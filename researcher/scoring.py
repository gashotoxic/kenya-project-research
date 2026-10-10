"""The 7-dimension "Kenyan viable" rubric and the viability gate.

Rubric (each dimension 0-5, spec section 4.1):
  1. pain            Pain severity in Kenya
  2. market          Market reach (SMEs / chamas / freelancers / landlords)
  3. payments        Payment-rails fit (M-Pesa / Paystack natural)
  4. data            Data/API availability (public, simulatable, browser fallback)
  5. buildability    One agent, <= 2 weeks to a live demo on our stack
  6. differentiation No common Kenyan SaaS already nails it
  7. showcase        Demo is visually obvious; portfolio weight

GATE: total >= 25/35 AND pain >= 4 AND buildability >= 3.
"""
from __future__ import annotations

from datetime import date

from .schema import Idea

GATE_TOTAL = 25
GATE_PAIN = 4
GATE_BUILDABILITY = 3
MAX_TOTAL = 35


def evaluate(idea: Idea):
    """Return (passed_gate, reasons_failed)."""
    reasons = []
    if idea.total < GATE_TOTAL:
        reasons.append(f"total {idea.total} < {GATE_TOTAL}")
    if idea.scores["pain"] < GATE_PAIN:
        reasons.append(f"pain {idea.scores['pain']} < {GATE_PAIN}")
    if idea.scores["buildability"] < GATE_BUILDABILITY:
        reasons.append(f"buildability {idea.scores['buildability']} < {GATE_BUILDABILITY}")
    return (not reasons), reasons


def rank_key(idea: Idea):
    """Order: total desc, pain desc, newest date_found, then stable by key."""
    return (
        -idea.total,
        -idea.scores["pain"],
        -date.fromisoformat(idea.date_found).toordinal(),
        idea.key,
    )


def gate_summary() -> str:
    return (
        f"total >= {GATE_TOTAL}/{MAX_TOTAL} AND pain >= {GATE_PAIN} "
        f"AND buildability >= {GATE_BUILDABILITY}"
    )
