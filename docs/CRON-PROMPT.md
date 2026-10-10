# Weekly cron prompt (versioned like code)

This exact text is registered as the `SCOUT Kenya Project Scout` cron job in
the **scout** profile (weekly Monday 08:30 EAT, Telegram delivery). If the
job and this file drift apart, this file is the source of truth — re-register
with `hermes --profile scout cron create`.

---

Weekly Kenya project research run — Kenya Projects Pipeline Phase 2.
Spec: ~/.hermes/SHARED/kenya-projects-pipeline-spec.md (section 4).
Repo: /home/gasho/workspace/gashotech/kenya-project-research — read its README.md first (rubric + pipeline contract).

Steps:
1. Read ideas/inbox.jsonl. Do NOT re-research keys already there.
2. Research 2-4 NEW Kenyan workflow-pain project ideas (SMEs, chamas, landlords, freelancers) with web search. Every idea needs >= 2 REAL source URLs you actually retrieved — never invent URLs, never inflate scores.
3. Score each idea 0-5 on the 7 rubric dimensions (anchors in the README) with honest rationale, then append each as one JSON line to ideas/inbox.jsonl (schema in the README; new kebab-case keys; date_found = today's date).
4. Run: ./run-research.sh --fetch --notify
   - exit 0: success — note the "telegram delivered: message_id=N" line
   - exit 2: invalid inbox — the printed flaw says what to fix; fix it and re-run
   - exit 3: backlog written but telegram delivery failed — continue and note the error
5. Your FINAL RESPONSE is the delivery ack. Keep it under 800 characters, exactly this shape:
   Kenya project scout <run-id>: X scored / Y proposed / Z rejected / W deduped.
   Top: <title> (<total>/35). Digest message_id <N>. Backlog: ~/.hermes/SHARED/kenya-project-backlog.md
   Use the message_id printed by step 4. If delivery failed, write "notify failed: <reason>" instead of the message_id.

Never edit kenya-project-backlog.md by hand. Never put secrets in the repo or the digest.
