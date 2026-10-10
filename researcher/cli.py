"""Command-line entry point.

  python3 -m researcher.cli run    full pipeline (the one command)
  python3 -m researcher.cli check  validate + score the inbox, write nothing

Defaults resolve from env so the cron/agent never passes paths:
  KPR_INBOX         ideas/inbox.jsonl inside this repo
  KPR_BACKLOG_PATH  ~/.hermes/SHARED/kenya-project-backlog.md
  KPR_STATE_DIR     ~/.hermes/SHARED/kenya-project-research-state
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import envload, pipeline, sources
from .scoring import evaluate, gate_summary
from .schema import IdeaError, load_inbox

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED = Path.home() / ".hermes" / "SHARED"


def _default_inbox() -> str:
    return os.environ.get("KPR_INBOX", str(REPO_ROOT / "ideas" / "inbox.jsonl"))


def _default_backlog() -> str:
    return os.environ.get("KPR_BACKLOG_PATH", str(SHARED / "kenya-project-backlog.md"))


def _default_state() -> str:
    return os.environ.get(
        "KPR_STATE_DIR", str(SHARED / "kenya-project-research-state")
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="researcher", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p):
        p.add_argument("--inbox", default=_default_inbox())
        p.add_argument("--top", type=int, default=pipeline.DEFAULT_TOP_N)

    run_p = sub.add_parser("run", help="full pipeline run")
    add_common(run_p)
    run_p.add_argument("--backlog", default=_default_backlog())
    run_p.add_argument("--state", default=_default_state())
    run_p.add_argument("--window-days", type=int, default=30)
    run_p.add_argument("--fetch", action="store_true", help="probe source URLs live")
    run_p.add_argument("--notify", action="store_true", help="send Telegram digest (env creds)")
    run_p.add_argument("--chat-id", default=None)

    check_p = sub.add_parser("check", help="validate + score inbox only")
    add_common(check_p)
    return parser


def cmd_check(args) -> int:
    ideas = load_inbox(args.inbox)
    print(f"inbox OK: {len(ideas)} ideas validated (gate: {gate_summary()})")
    for idea in ideas:
        ok, reasons = evaluate(idea)
        verdict = "PASS" if ok else f"REJECT ({'; '.join(reasons)})"
        print(f"  {idea.key}: total {idea.total} -> {verdict}")
    return 0


def cmd_run(args) -> int:
    result = pipeline.run(
        inbox_path=args.inbox,
        backlog_path=args.backlog,
        state_dir=args.state,
        top_n=args.top,
        window_days=args.window_days,
        fetch=args.fetch,
        do_notify=args.notify,
        chat_id=args.chat_id,
    )
    counts = result["counts"]
    print(f"run {result['run_id']} ({result['date']}) — gate: {gate_summary()}")
    print(
        f"  {counts['scored']} scored · {counts['proposed']} proposed · "
        f"{counts['held']} held · {counts['rejected']} rejected · "
        f"{counts['deduped']} deduped"
    )
    for rank, idea in enumerate(result["proposed"], start=1):
        print(f"  {rank}. {idea.title} — {idea.total}/35")
    if result["sources_checked"] is not None:
        ok = sum(1 for s in result["sources_checked"] if s["status"].startswith("ok:"))
        print(f"  sources reachable: {ok}/{len(result['sources_checked'])}")
    print(f"  backlog written: {result['backlog_path']}")
    delivery = result.get("delivery")
    if delivery is not None:
        if delivery["ok"]:
            print(f"  telegram delivered: message_id={delivery['message_id']} chat={delivery['chat_id']}")
        else:
            print(f"  telegram FAILED: {delivery['error']}")
            return 3
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    envload.load_env()
    try:
        if args.command == "check":
            return cmd_check(args)
        return cmd_run(args)
    except IdeaError as exc:
        print(f"INBOX INVALID: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"MISSING FILE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
