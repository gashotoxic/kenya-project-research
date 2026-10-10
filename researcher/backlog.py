"""Backlog rendering: ~/.hermes/SHARED/kenya-project-backlog.md

Shape (spec section 4.2): top-5 proposals with full detail (7 scores,
total, >= 2 sources, agent scope, date found), rejected below-gate ideas as
one-liners with scores, plus the dedup/held transparency sections and a
cumulative run log.
"""
from __future__ import annotations

from .scoring import MAX_TOTAL, gate_summary

HEADER = "# Kenya Project Backlog"


def _score_line(idea) -> str:
    parts = " · ".join(f"{dim} {idea.scores[dim]}" for dim in idea.scores)
    return f"{parts} → **total {idea.total}/{MAX_TOTAL}**"


def _proposal_block(idea, rank=None, note: str = None) -> str:
    heading = (
        f"### {rank}. {idea.title} — {idea.total}/{MAX_TOTAL}"
        if rank is not None
        else f"### {idea.title} — {idea.total}/{MAX_TOTAL}"
    )
    lines = [heading]
    if note:
        lines.append(f"- **{note}**")
    lines += [
        f"- **One-liner:** {idea.one_liner}",
        f"- **Pain:** {idea.pain_description}",
        f"- **Scores:** {_score_line(idea)}",
        "- **Sources:**",
    ]
    lines.extend(f"  - {url}" for url in idea.sources)
    lines.append(f"- **Agent scope:** {idea.agent_scope}")
    lines.append(f"- **Date found:** {idea.date_found}")
    return "\n".join(lines)


def _earlier_block(record: dict, idea) -> str:
    """Full detail for an earlier proposal; falls back to log fields."""
    if idea is not None:
        return _proposal_block(
            idea,
            note=f"Proposed {record['proposed_on']} in run {record['run_id']}",
        )
    return (
        f"### {record['title']} — {record.get('total', '?')}/{MAX_TOTAL}\n"
        f"- **Proposed:** {record['proposed_on']} in run {record['run_id']} "
        "(detail lost — idea left the inbox before history stored full records)"
    )


def render_backlog(
    run_id: str,
    run_date: str,
    proposed,
    earlier,
    held,
    rejected,
    run_log,
    sources_checked=None,
) -> str:
    """proposed/earlier/held are Idea lists (earlier: (record, idea|None)
    tuples); rejected is (idea, reasons) tuples."""
    out = [
        HEADER,
        "",
        f"_Run {run_id} · generated {run_date} · gate: {gate_summary()}_",
        "_Schedule: weekly Monday 08:30 EAT (SCOUT profile) · full history: "
        "`~/.hermes/SHARED/kenya-project-research-state/`_",
        "",
        "## Proposals — top 5 (this run)",
        "",
    ]
    if proposed:
        for rank, idea in enumerate(proposed, start=1):
            out.append(_proposal_block(idea, rank=rank))
            out.append("")
    else:
        out.append("_No new proposals this run._")
        out.append("")

    out.append("## Already proposed (30-day dedup window)")
    out.append("")
    if earlier:
        for record, idea in earlier:
            out.append(_earlier_block(record, idea))
            out.append("")
    else:
        out.append("_None._")
        out.append("")

    out.append("## Held — passed gate, outside top 5")
    out.append("")
    if held:
        for idea in held:
            out.append(f"- {idea.title} (key `{idea.key}`, total {idea.total}/{MAX_TOTAL}) — {idea.one_liner}")
    else:
        out.append("_None._")
    out.append("")

    out.append("## Rejected — below gate")
    out.append("")
    if rejected:
        for idea, reasons in rejected:
            out.append(
                f"- {idea.title} — total {idea.total}/{MAX_TOTAL} "
                f"(pain {idea.scores['pain']}, buildability {idea.scores['buildability']}) — "
                f"{idea.one_liner} — failed: {'; '.join(reasons)}"
            )
    else:
        out.append("_None._")
    out.append("")

    if sources_checked is not None:
        ok = sum(1 for item in sources_checked if item["status"].startswith("ok:"))
        out.append(f"_Source reachability check: {ok}/{len(sources_checked)} answered._")
        out.append("")

    out.append("## Run log")
    out.append("")
    for record in run_log:
        out.append(
            f"- {record['run_id']} ({record['date']}): {record['scored']} scored · "
            f"{record['proposed']} proposed · {record['held']} held · "
            f"{record['rejected']} rejected · {record['deduped']} deduped"
        )
    out.append("")
    return "\n".join(out)


def render_digest(run_id: str, run_date: str, proposed, counts: dict) -> str:
    """Compact digest body used for Telegram delivery."""
    lines = [
        f"Kenya project scout — run {run_id} ({run_date})",
        f"{counts['scored']} ideas scored · {counts['proposed']} proposed · "
        f"{counts['held']} held · {counts['rejected']} rejected · "
        f"{counts['deduped']} deduped",
        "",
    ]
    for rank, idea in enumerate(proposed, start=1):
        lines.append(f"{rank}. {idea.title} — {idea.total}/{MAX_TOTAL}")
    lines.append("")
    lines.append("Backlog: ~/.hermes/SHARED/kenya-project-backlog.md")
    return "\n".join(lines)
