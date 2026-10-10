# kenya-project-research

One-command researcher that finds Kenyan-viable project ideas, scores them
against a 7-dimension rubric, enforces a viability gate, deduplicates
proposals over 30 days, and writes the shared project backlog.

Public repo: https://github.com/gashotoxic/kenya-project-research
Part of the Kenya Projects Pipeline (research stage): spec
`~/.hermes/SHARED/kenya-projects-pipeline-spec.md`, section 4.

## The one command

```bash
./run-research.sh            # validate -> score -> gate -> dedup -> backlog
./run-research.sh --fetch    # + live source reachability check
./run-research.sh --notify   # + Telegram digest (env creds, message_id returned)
./run-research.sh --check    # validate + score the inbox, write nothing
```

It writes `~/.hermes/SHARED/kenya-project-backlog.md` and exits non-zero on
an invalid inbox (the flaw is printed; nothing is half-written).

## Architecture (5-minute read)

```
ideas/inbox.jsonl          research input (agent-authored, one JSON per line)
        |
        v
+-------------------------------------------------------------+
| researcher/                                                  |
|   schema.py     strict idea validation (7 dims, >=2 sources) |
|   scoring.py    rubric totals + gate (25/35, pain 4, build 3)|
|   sources.py    URL validation + parallel reachability probe |
|   dedup.py      30-day proposal window (append-only history) |
|   backlog.py    backlog + digest rendering                  |
|   notify.py     Telegram sendMessage -> message_id proof     |
|   pipeline.py   orchestration (one run)                      |
|   cli.py        `run` / `check` entry points                 |
+-------------------------------------------------------------+
        |                                    |
        v                                    v
~/.hermes/SHARED/kenya-project-backlog.md   ~/.hermes/SHARED/kenya-project-research-state/
  (top 5 proposals, dedup window,            (proposed.jsonl + runs.jsonl — dedup
   held, rejected one-liners, run log)        memory; survives repo rebuilds)
```

**Division of labour.** Judgment (finding ideas, scoring 0-5 against the
rubric anchors) is done by the weekly research agent (SCOUT) and recorded in
the inbox with sources. Everything deterministic — arithmetic, gate, dedup,
formatting, delivery — is done by this code, so every run is reproducible
and testable.

**Run semantics.** Each run proposes at most 5 new ideas (rank: total desc,
pain desc, newest first). An idea proposed once is not re-proposed within 30
days; it stays visible in the backlog's dedup window with full detail. Ideas
above the gate but outside the top 5 are "held" and stay eligible. Below-gate
ideas appear as rejected one-liners with their scores.

## Rubric — "Kenyan viable"

Each dimension 0-5. **Gate: total >= 25/35 AND pain >= 4 AND buildability >= 3.**

| # | Dimension | What a 5 looks like |
|---|-----------|---------------------|
| 1 | pain | People do this manually every week and hate it |
| 2 | market | SMEs / chamas / freelancers / landlords — wide, not one company |
| 3 | payments | M-Pesa or Paystack integration is natural |
| 4 | data | Public data or simulatable; browser fallback acceptable |
| 5 | buildability | One agent, <= 2 weeks to a live demo on our stack |
| 6 | differentiation | No common Kenyan SaaS already nails it |
| 7 | showcase | Demo is visually obvious; portfolio/resume weight |

## Idea inbox schema (`ideas/inbox.jsonl`)

One JSON object per line. Validation is strict — unknown or missing keys,
scores outside 0-5, or fewer than 2 distinct http(s) source URLs fail the run.

```json
{
  "key": "kebab-case-unique-id",
  "title": "Human Title",
  "one_liner": "<= 240 chars",
  "pain_description": "2-4 sentences describing the workflow pain",
  "scores": {"pain": 5, "market": 5, "payments": 4, "data": 5,
             "buildability": 4, "differentiation": 4, "showcase": 5},
  "score_rationale": {"pain": "why this score", "differentiation": "..."},
  "sources": ["https://real.source/one", "https://real.source/two"],
  "agent_scope": "The one painful workflow the agent fixes",
  "date_found": "YYYY-MM-DD"
}
```

## Weekly cron (SCOUT profile)

- Schedule: **weekly Monday 08:30 EAT** (`30 8 * * 1`, machine local = EAT)
- Profile: `scout` (research lane) — job `SCOUT Kenya Project Scout`
- Prompt: versioned in [`docs/CRON-PROMPT.md`](docs/CRON-PROMPT.md)
- Delivery: Telegram — the pipeline posts the digest and records the
  `message_id` in `state/runs.jsonl` and run output; the Hermes job delivers
  the agent's short ack (carrying that message_id) to the same chat

## Environment variables (names only — values never in code)

| Var | Used for | Required |
|-----|----------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram digest delivery (`--notify`) | only for `--notify` |
| `TELEGRAM_CHAT_ID` (or `TELEGRAM_HOME_CHANNEL`) | digest chat target | only for `--notify` |
| `KPR_INBOX` | inbox path override | no |
| `KPR_BACKLOG_PATH` | backlog path override | no |
| `KPR_STATE_DIR` | dedup state path override | no |
| `KPR_ENV_FILE` / `KPR_SKIP_ENV_FILE` | env-file loading control | no |

On the Hermes fleet machine the CLI auto-loads `~/.hermes/profiles/scout/.env`
then `~/.hermes/.env` for missing vars only (real environment always wins);
elsewhere, export the vars. Set `KPR_SKIP_ENV_FILE=1` to disable.

Secret handling: the notify module redacts the token from every error before
it leaves the module. `grep` proof that no credential lives in this repo:

```bash
grep -rniE '([0-9]{8,10}:AA[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9]{20,}|cpk_[a-f0-9]{8,})' .   # -> no matches
```

## Tests

```bash
python3 -m unittest discover -s tests    # 25 tests, stdlib only, no network
```

Covered: schema strictness, gate matrix (total/pain/buildability), ranking,
30-day dedup window (suppress + release + future dates), top-5 capping, held
promotion, rejected one-liners with scores, backlog sections, end-to-end run,
re-run dedup proof, token redaction.

## Tier 1 mapping (this repo)

| Tier 1 check | How |
|--------------|-----|
| README (5-min architecture) | this file |
| Public GitHub | https://github.com/gashotoxic/kenya-project-research |
| Prompts versioned like code | `docs/CRON-PROMPT.md` (the cron job uses this text verbatim) |
| Tool outputs schema-validated | strict `schema.py` validation; invalid input fails the run |
| Retries with backoff | `notify.py` retries 3x with 1/2/4s backoff |
| Secrets/PII stripped before model | secrets env-sourced + redacted; digests carry counts and titles only |
| Logged calls | `state/runs.jsonl` + `state/proposed.jsonl` (append-only) |
| Human approval on money/email/delete | nothing in this repo sends money, email, or deletes data |
