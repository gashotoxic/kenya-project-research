"""30-day proposal dedup and run history.

State lives OUTSIDE the repo (default: ~/.hermes/SHARED/kenya-project-research-state/)
so it survives repo rebuilds and clones. Only ideas that were actually
PROPOSED enter the log; held/rejected ideas stay re-eligible.

Format: append-only JSONL.
  proposed.jsonl  {"key","title","total","proposed_on","run_id"}
  runs.jsonl      {"run_id","date","scored","proposed","held","rejected","deduped"}
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

WINDOW_DAYS = 30


class History:
    def __init__(self, state_dir):
        self.state_dir = Path(state_dir)
        self.proposed_path = self.state_dir / "proposed.jsonl"
        self.runs_path = self.state_dir / "runs.jsonl"

    def _read_jsonl(self, path: Path) -> list:
        if not path.exists():
            return []
        records = []
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if text:
                    records.append(json.loads(text))
        return records

    def _append_jsonl(self, path: Path, record: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def proposals(self) -> list:
        return self._read_jsonl(self.proposed_path)

    def runs(self) -> list:
        return self._read_jsonl(self.runs_path)

    def proposed_within(self, on: date, window_days: int = WINDOW_DAYS) -> dict:
        """key -> latest proposal record if proposed within the window."""
        cutoff = on - timedelta(days=window_days)
        latest: dict = {}
        for record in self.proposals():
            try:
                proposed_on = date.fromisoformat(record["proposed_on"])
            except (KeyError, ValueError):
                continue
            if proposed_on < cutoff or proposed_on > on:
                continue
            key = record.get("key")
            if key and (key not in latest or record["proposed_on"] > latest[key]["proposed_on"]):
                latest[key] = record
        return latest

    def record_proposal(self, idea, run_id: str, on: date) -> dict:
        record = {
            "key": idea.key,
            "title": idea.title,
            "total": idea.total,
            "proposed_on": on.isoformat(),
            "run_id": run_id,
            "idea": idea.as_dict(),
        }
        self._append_jsonl(self.proposed_path, record)
        return record

    def record_run(self, record: dict) -> None:
        self._append_jsonl(self.runs_path, record)
