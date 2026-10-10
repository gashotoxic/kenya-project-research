"""End-to-end orchestration for one researcher run.

Pipeline stages (the one command runs all of them):
  1. load + strictly validate ideas/inbox.jsonl
  2. optional live source reachability check (--fetch)
  3. score against the rubric gate (total >= 25/35, pain >= 4, buildability >= 3)
  4. 30-day dedup against the proposal history
  5. rank, take top 5, record proposals
  6. write ~/.hermes/SHARED/kenya-project-backlog.md
  7. optional Telegram digest with message_id capture (--notify)
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from . import backlog, dedup, notify, sources
from .scoring import evaluate, rank_key
from .schema import IdeaError, load_inbox, parse_idea

DEFAULT_TOP_N = 5


def run(
    inbox_path,
    backlog_path,
    state_dir,
    top_n: int = DEFAULT_TOP_N,
    window_days: int = dedup.WINDOW_DAYS,
    fetch: bool = False,
    do_notify: bool = False,
    chat_id=None,
    run_date: date = None,
) -> dict:
    run_date = run_date or date.today()
    ideas = load_inbox(inbox_path)

    sources_checked = sources.check_live([u for idea in ideas for u in idea.sources]) if fetch else None

    passed, rejected = [], []
    for idea in ideas:
        ok, reasons = evaluate(idea)
        if ok:
            passed.append(idea)
        else:
            rejected.append((idea, reasons))

    history = dedup.History(state_dir)
    recent = history.proposed_within(run_date, window_days)
    deduped = [(idea, recent[idea.key]) for idea in passed if idea.key in recent]
    eligible = [idea for idea in passed if idea.key not in recent]

    inbox_by_key = {idea.key: idea for idea in ideas}
    earlier = []
    for record in sorted(recent.values(), key=lambda r: r["proposed_on"], reverse=True):
        idea = inbox_by_key.get(record.get("key"))
        if idea is None and isinstance(record.get("idea"), dict):
            try:
                idea = parse_idea(record["idea"], where=f"history:{record.get('key')}")
            except IdeaError:
                idea = None
        earlier.append((record, idea))

    eligible.sort(key=rank_key)
    proposed = eligible[:top_n]
    held = eligible[top_n:]

    runs = history.runs()
    today_runs = [r for r in runs if r.get("date") == run_date.isoformat()]
    run_id = f"R-{run_date.strftime('%Y%m%d')}-{len(today_runs) + 1:02d}"

    for idea in proposed:
        history.record_proposal(idea, run_id, run_date)

    delivery = None
    counts = {
        "scored": len(ideas),
        "proposed": len(proposed),
        "held": len(held),
        "rejected": len(rejected),
        "deduped": len(deduped),
    }
    if do_notify:
        delivery = notify.send_digest(
            backlog.render_digest(run_id, run_date.isoformat(), proposed, counts),
            chat_id=chat_id,
        )

    run_record = {
        "run_id": run_id,
        "date": run_date.isoformat(),
        **counts,
        "message_id": (delivery or {}).get("message_id"),
        "notify_ok": (delivery or {}).get("ok"),
    }
    history.record_run(run_record)
    run_log = history.runs()

    text = backlog.render_backlog(
        run_id=run_id,
        run_date=run_date.isoformat(),
        proposed=proposed,
        earlier=earlier,
        held=held,
        rejected=rejected,
        run_log=run_log,
        sources_checked=sources_checked,
    )
    backlog_file = Path(backlog_path)
    backlog_file.parent.mkdir(parents=True, exist_ok=True)
    backlog_file.write_text(text, encoding="utf-8")

    delivery = None
    if do_notify:
        delivery = notify.send_digest(
            backlog.render_digest(run_id, run_date.isoformat(), proposed, counts),
            chat_id=chat_id,
        )

    return {
        "run_id": run_id,
        "date": run_date.isoformat(),
        "counts": counts,
        "proposed": proposed,
        "held": held,
        "rejected": rejected,
        "deduped": deduped,
        "backlog_path": str(backlog_file),
        "sources_checked": sources_checked,
        "delivery": delivery,
    }
