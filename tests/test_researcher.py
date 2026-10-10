"""Test suite for the researcher pipeline (stdlib unittest, no network).

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from researcher import dedup, pipeline, scoring  # noqa: E402
from researcher.backlog import render_backlog  # noqa: E402
from researcher.notify import _redact, resolve_chat_id  # noqa: E402
from researcher.schema import IdeaError, load_inbox, parse_idea  # noqa: E402

TODAY = date(2026, 10, 10)


def make_idea(**overrides):
    base = {
        "key": "sample-idea",
        "title": "Sample Idea",
        "one_liner": "Does a thing.",
        "pain_description": "People do this weekly and hate it.",
        "scores": {
            "pain": 5, "market": 4, "payments": 4, "data": 4,
            "buildability": 4, "differentiation": 3, "showcase": 4,
        },
        "sources": ["https://example.com/a", "https://example.org/b"],
        "agent_scope": "One agent, one workflow.",
        "date_found": "2026-10-10",
    }
    base.update(overrides)
    return base


class SchemaTests(unittest.TestCase):
    def test_valid_idea_parses(self):
        idea = parse_idea(make_idea())
        self.assertEqual(idea.total, 28)

    def test_bad_key_rejected(self):
        with self.assertRaises(IdeaError):
            parse_idea(make_idea(key="Bad Key!"))

    def test_missing_dimension_rejected(self):
        scores = make_idea()["scores"]
        del scores["pain"]
        with self.assertRaises(IdeaError):
            parse_idea(make_idea(scores=scores))

    def test_out_of_range_score_rejected(self):
        with self.assertRaises(IdeaError):
            parse_idea(make_idea(scores=make_idea()["scores"] | {"pain": 6}))

    def test_bool_score_rejected(self):
        with self.assertRaises(IdeaError):
            parse_idea(make_idea(scores=make_idea()["scores"] | {"pain": True}))

    def test_single_source_rejected(self):
        with self.assertRaises(IdeaError):
            parse_idea(make_idea(sources=["https://example.com/a"]))

    def test_non_http_source_rejected(self):
        with self.assertRaises(IdeaError):
            parse_idea(make_idea(sources=["ftp://example.com/a", "https://example.org/b"]))

    def test_duplicate_source_urls_rejected(self):
        with self.assertRaises(IdeaError):
            parse_idea(make_idea(sources=["https://example.com/a", "https://example.com/a/"]))

    def test_bad_date_rejected(self):
        with self.assertRaises(IdeaError):
            parse_idea(make_idea(date_found="10-10-2026"))

    def test_load_inbox_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp) / "inbox.jsonl"
            line = json.dumps(make_idea())
            inbox.write_text(line + "\n" + line + "\n")
            with self.assertRaises(IdeaError):
                load_inbox(inbox)


class GateTests(unittest.TestCase):
    def _idea(self, **score_overrides):
        return parse_idea(make_idea(scores=make_idea()["scores"] | score_overrides))

    def test_gate_passes_at_threshold(self):
        idea = self._idea(pain=4, buildability=3)
        self.assertTrue(all(v >= 0 for v in idea.scores.values()))
        ok, reasons = scoring.evaluate(idea)
        self.assertTrue(ok, reasons)

    def test_gate_fails_low_total(self):
        ok, reasons = scoring.evaluate(
            self._idea(pain=4, market=2, payments=2, data=2, buildability=3, differentiation=2, showcase=2)
        )
        self.assertFalse(ok)
        self.assertIn("total 17 < 25", reasons)

    def test_gate_fails_low_pain(self):
        ok, reasons = scoring.evaluate(self._idea(pain=3))
        self.assertFalse(ok)
        self.assertTrue(any(r.startswith("pain") for r in reasons))

    def test_gate_fails_low_buildability(self):
        ok, reasons = scoring.evaluate(self._idea(buildability=2))
        self.assertFalse(ok)
        self.assertTrue(any(r.startswith("buildability") for r in reasons))

    def test_ranking_total_then_pain(self):
        low_pain = parse_idea(make_idea(key="a-idea", scores=make_idea()["scores"] | {"pain": 4, "showcase": 4}))   # total 27
        high_pain = parse_idea(make_idea(key="b-idea", scores=make_idea()["scores"] | {"pain": 5, "showcase": 3}))  # total 27
        ideas = sorted([low_pain, high_pain], key=scoring.rank_key)
        self.assertEqual([i.key for i in ideas], ["b-idea", "a-idea"])


class DedupTests(unittest.TestCase):
    def test_window_suppresses_then_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = dedup.History(tmp)
            idea = parse_idea(make_idea())
            history.record_proposal(idea, "R-20261010-01", TODAY)

            inside = history.proposed_within(TODAY.replace(day=20), window_days=30)
            self.assertIn("sample-idea", inside)

            outside = history.proposed_within(date(2026, 11, 25), window_days=30)
            self.assertNotIn("sample-idea", outside)

    def test_future_dates_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = dedup.History(tmp)
            idea = parse_idea(make_idea())
            history.record_proposal(idea, "R-20270101-01", date(2027, 1, 1))
            self.assertEqual(history.proposed_within(TODAY), {})


class BacklogRenderTests(unittest.TestCase):
    def _render(self):
        ideas = [parse_idea(make_idea(key=f"idea-{n}", title=f"Idea {n}")) for n in range(3)]
        rejected = [(parse_idea(make_idea(key="low-idea", title="Low", scores=make_idea()["scores"] | {"pain": 2, "buildability": 2, "market": 2, "payments": 2, "data": 2, "differentiation": 2, "showcase": 2})), ["total 14 < 25"])]
        return render_backlog(
            run_id="R-20261010-01",
            run_date="2026-10-10",
            proposed=ideas[:2],
            earlier=[],
            held=ideas[2:],
            rejected=rejected,
            run_log=[{"run_id": "R-20261010-01", "date": "2026-10-10", "scored": 4, "proposed": 2, "held": 1, "rejected": 1, "deduped": 0}],
        )

    def test_required_sections_present(self):
        text = self._render()
        for section in (
            "## Proposals — top 5 (this run)",
            "## Already proposed (30-day dedup window)",
            "## Held — passed gate, outside top 5",
            "## Rejected — below gate",
            "## Run log",
        ):
            self.assertIn(section, text)

    def test_proposal_carries_scores_total_sources(self):
        text = self._render()
        self.assertIn("total 28/35", text)
        self.assertIn("https://example.com/a", text)
        self.assertIn("**Agent scope:**", text)
        self.assertIn("**Date found:** 2026-10-10", text)

    def test_rejected_one_liner_carries_score(self):
        text = self._render()
        self.assertIn("Low — total 14/35", text)


class PipelineTests(unittest.TestCase):
    def _write_inbox(self, tmp, ideas):
        inbox = Path(tmp) / "inbox.jsonl"
        inbox.write_text("\n".join(json.dumps(i) for i in ideas) + "\n")
        return inbox

    def _make_many(self, count, key_prefix="idea"):
        out = []
        for n in range(count):
            scores = make_idea()["scores"] | {"pain": 5, "showcase": 5}
            out.append(make_idea(key=f"{key_prefix}-{n:02d}", title=f"Idea {n:02d}", scores=scores))
        return out

    def test_end_to_end_top5_cap_and_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = self._write_inbox(tmp, self._make_many(7))
            result = pipeline.run(
                inbox_path=inbox,
                backlog_path=Path(tmp) / "backlog.md",
                state_dir=Path(tmp) / "state",
                run_date=TODAY,
            )
            self.assertEqual(result["counts"]["proposed"], 5)
            self.assertEqual(result["counts"]["held"], 2)
            text = Path(result["backlog_path"]).read_text()
            self.assertIn("### 5. Idea 04", text)

    def test_rerun_within_30_days_proposes_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = self._write_inbox(tmp, self._make_many(3))
            first = pipeline.run(inbox_path=inbox, backlog_path=Path(tmp) / "b.md", state_dir=Path(tmp) / "state", run_date=TODAY)
            self.assertEqual(first["counts"]["proposed"], 3)
            second = pipeline.run(inbox_path=inbox, backlog_path=Path(tmp) / "b.md", state_dir=Path(tmp) / "state", run_date=TODAY.replace(day=25))
            self.assertEqual(second["counts"]["proposed"], 0)
            self.assertEqual(second["counts"]["deduped"], 3)
            text = Path(second["backlog_path"]).read_text()
            self.assertIn("## Already proposed (30-day dedup window)", text)
            self.assertIn("Proposed 2026-10-10 in run R-20261010-01", text)
            self.assertIn("- **Sources:**", text)

    def test_below_gate_lands_in_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = make_idea(key="bad-idea", title="Bad", scores=make_idea()["scores"] | {"pain": 2, "buildability": 2})
            inbox = self._write_inbox(tmp, [bad])
            result = pipeline.run(inbox_path=inbox, backlog_path=Path(tmp) / "b.md", state_dir=Path(tmp) / "state", run_date=TODAY)
            self.assertEqual(result["counts"]["rejected"], 1)
            self.assertIn("Bad — total 23/35", Path(result["backlog_path"]).read_text())


class NotifyUnitTests(unittest.TestCase):
    def test_redaction(self):
        self.assertEqual(_redact("token=abc123", ["abc123"]), "token=<redacted>")

    def test_chat_id_resolution_forms(self):
        import os
        old = os.environ.get("TELEGRAM_CHAT_ID")
        try:
            os.environ["TELEGRAM_CHAT_ID"] = "telegram:-100555"
            self.assertEqual(resolve_chat_id(), "-100555")
            self.assertEqual(resolve_chat_id("231479478"), "231479478")
        finally:
            if old is None:
                del os.environ["TELEGRAM_CHAT_ID"]
            else:
                os.environ["TELEGRAM_CHAT_ID"] = old


if __name__ == "__main__":
    unittest.main()
