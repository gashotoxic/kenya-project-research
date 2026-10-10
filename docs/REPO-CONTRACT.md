# Repository contract — kenya-project-research

Binding contract for all work in this tree (DOX-style). The root `AGENTS.md`
is the canonical home for this content but its creation is pending interactive
approval (protected agent-instruction file); until then this file is the
contract, and `AGENTS.md` should mirror it once approved.

## Purpose

One-command researcher for the Kenya Projects Pipeline (Phase 2): score
Kenyan-viable project ideas against the 7-dimension rubric, enforce the
viability gate, deduplicate proposals over 30 days, and write the shared
backlog. Research judgment lives with the weekly SCOUT agent; all
deterministic mechanics live in this repo.

## Ownership

- Builder/maintainer: **GIMA** (Code & Projects Lead)
- Weekly research run: **SCOUT** profile (cron `SCOUT Kenya Project Scout`)
- Spec owner/verdict: **MUGO**
- Spec: `~/.hermes/SHARED/kenya-projects-pipeline-spec.md` (section 4)
- Answer key: `~/.hermes/SHARED/kenya-projects-pipeline-answer-key.md` (Phase 2)

## Layout

| Path | Role |
|------|------|
| `run-research.sh` | THE one command (`run` or `--check`) |
| `researcher/` | pipeline package (schema, scoring, sources, dedup, backlog, notify, pipeline, cli) |
| `ideas/inbox.jsonl` | research input: one JSON idea per line, strictly validated |
| `tests/test_researcher.py` | stdlib unittest suite (no network) |
| `docs/CRON-PROMPT.md` | the weekly cron prompt, versioned like code |
| `README.md` | Tier 1 architecture README + rubric + schema |

Runtime state lives OUTSIDE the repo:
`~/.hermes/SHARED/kenya-project-backlog.md` (output) and
`~/.hermes/SHARED/kenya-project-research-state/` (proposed.jsonl +
runs.jsonl). Never hand-edit the backlog; never commit state.

## Contracts (do not change without updating spec + answer key)

- Rubric: 7 dimensions (pain, market, payments, data, buildability,
  differentiation, showcase), each 0-5.
- Gate: total >= 25/35 AND pain >= 4 AND buildability >= 3.
- Dedup: an idea key is proposed at most once per 30 days
  (`dedup.WINDOW_DAYS`).
- Top 5 new proposals per run; overflow above gate = "held"; below gate =
  rejected one-liners with scores.
- Every inbox idea needs >= 2 distinct http(s) source URLs; validation
  failure exits 2 and writes nothing.
- Secrets: env-sourced only (`TELEGRAM_BOT_TOKEN` etc.), redacted in errors.
  A credential in this repo is a defect.

## Commands

```bash
./run-research.sh [--fetch] [--notify]   # full pipeline
./run-research.sh --check                # validate + score only
python3 -m unittest discover -s tests    # test suite
```

## Change rules

- Read this file before editing; update it after any change to purpose,
  layout, contracts, or commands (DOX protocol).
- Keep the inbox schema, gate numbers, and backlog sections in sync across
  `README.md`, `researcher/`, and this file.
- `docs/CRON-PROMPT.md` and the registered cron job must stay verbatim
  identical; the README documents the registration command.
