"""Idea schema and strict validation.

Every candidate idea enters the pipeline as one JSON object per line in
``ideas/inbox.jsonl``. Validation is strict on purpose: a malformed entry
fails the whole run (exit 2) so the weekly research agent fixes its output
instead of shipping garbage into the backlog.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlparse

DIMENSIONS = (
    "pain",
    "market",
    "payments",
    "data",
    "buildability",
    "differentiation",
    "showcase",
)

KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_ONE_LINER = 240


class IdeaError(ValueError):
    """An inbox entry is invalid. The run must fail loudly, never skip."""


@dataclass
class Idea:
    key: str
    title: str
    one_liner: str
    pain_description: str
    scores: dict
    sources: list
    agent_scope: str
    date_found: str
    score_rationale: dict = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.scores[d] for d in DIMENSIONS)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "title": self.title,
            "one_liner": self.one_liner,
            "pain_description": self.pain_description,
            "scores": dict(self.scores),
            "sources": list(self.sources),
            "agent_scope": self.agent_scope,
            "date_found": self.date_found,
            "score_rationale": dict(self.score_rationale),
        }


def valid_url(url: str) -> bool:
    """True for absolute http(s) URLs with a plausible host."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return (
        parsed.scheme in ("http", "https")
        and bool(parsed.netloc)
        and "." in parsed.netloc.split("@")[-1].split(":")[0]
    )


def normalize_url(url: str) -> str:
    """Canonical form used for source-uniqueness checks."""
    return url.strip().rstrip("/").lower()


def _check_sources(value, errors: list) -> list:
    if not isinstance(value, list):
        errors.append("sources must be a list of URL strings")
        return []
    urls = []
    for item in value:
        if not isinstance(item, str) or not valid_url(item):
            errors.append(f"invalid source URL: {item!r}")
        else:
            urls.append(item)
    distinct = {normalize_url(u) for u in urls}
    if len(distinct) < 2:
        errors.append(f"need >= 2 distinct source URLs, got {len(distinct)}")
    return urls


def _check_scores(value, errors: list) -> dict:
    if not isinstance(value, dict):
        errors.append("scores must be an object with the 7 dimension keys")
        return {}
    scores = {}
    for dim in DIMENSIONS:
        if dim not in value:
            errors.append(f"scores missing dimension: {dim}")
            continue
        raw = value[dim]
        if isinstance(raw, bool) or not isinstance(raw, int):
            errors.append(f"scores.{dim} must be an integer 0-5, got {raw!r}")
            continue
        if not 0 <= raw <= 5:
            errors.append(f"scores.{dim} out of range 0-5: {raw}")
            continue
        scores[dim] = raw
    for extra in sorted(set(value) - set(DIMENSIONS)):
        errors.append(f"scores has unknown dimension: {extra!r}")
    return scores


def parse_idea(obj, where: str = "inbox") -> Idea:
    """Validate one decoded JSON object; raise IdeaError listing every flaw."""
    if not isinstance(obj, dict):
        raise IdeaError(f"{where}: entry must be a JSON object")
    errors: list = []

    key = obj.get("key")
    if not isinstance(key, str) or not KEY_RE.match(key):
        errors.append(f"key must match {KEY_RE.pattern}, got {key!r}")

    for field_name in ("title", "one_liner", "pain_description", "agent_scope"):
        value = obj.get(field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name} must be a non-empty string")

    one_liner = obj.get("one_liner")
    if isinstance(one_liner, str) and len(one_liner) > MAX_ONE_LINER:
        errors.append(f"one_liner longer than {MAX_ONE_LINER} chars")

    date_found = obj.get("date_found")
    if not isinstance(date_found, str) or not DATE_RE.match(date_found):
        errors.append(f"date_found must be YYYY-MM-DD, got {date_found!r}")
    else:
        try:
            date.fromisoformat(date_found)
        except ValueError:
            errors.append(f"date_found is not a real date: {date_found!r}")

    scores = _check_scores(obj.get("scores"), errors)
    sources = _check_sources(obj.get("sources"), errors)

    rationale = obj.get("score_rationale", {})
    if rationale and not isinstance(rationale, dict):
        errors.append("score_rationale must be an object when present")
        rationale = {}

    if errors:
        raise IdeaError(f"{where} (key={key!r}): " + "; ".join(errors))

    return Idea(
        key=key,
        title=obj["title"].strip(),
        one_liner=obj["one_liner"].strip(),
        pain_description=obj["pain_description"].strip(),
        scores=scores,
        sources=sources,
        agent_scope=obj["agent_scope"].strip(),
        date_found=date_found,
        score_rationale=rationale,
    )


def load_inbox(path) -> list:
    """Load ideas/inbox.jsonl. Blank lines and '#' comments are allowed."""
    ideas = []
    seen_keys = {}
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            where = f"{path}:{lineno}"
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as exc:
                raise IdeaError(f"{where}: invalid JSON ({exc})")
            idea = parse_idea(obj, where)
            if idea.key in seen_keys:
                raise IdeaError(
                    f"{where}: duplicate key {idea.key!r} "
                    f"(first seen on line {seen_keys[idea.key]})"
                )
            seen_keys[idea.key] = lineno
            ideas.append(idea)
    return ideas
