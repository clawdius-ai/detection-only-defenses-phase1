"""Detector-only defense interface.

A detector receives an input prompt (and optionally session context) and
returns a routing decision: allow or block. It does NOT modify the prompt
or intervene in target generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class DetectorDecision:
    blocked: bool
    score: Optional[float]
    label: str


class Detector(Protocol):
    name: str

    def evaluate(self, prompt: str) -> DetectorDecision:
        ...


class NoDetector:
    """No-defense baseline: always allow."""
    name = "none"

    def evaluate(self, prompt: str) -> DetectorDecision:  # noqa: D401
        return DetectorDecision(blocked=False, score=None, label="allow")
