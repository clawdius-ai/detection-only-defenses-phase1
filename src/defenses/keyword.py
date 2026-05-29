"""Keyword baseline detector.

A conservative blocklist of harmful-intent keywords drawn from AdvBench
behaviors. This is intentionally simple and serves as a lower-bound
baseline against which learned detectors are compared.
"""
from __future__ import annotations

import re

from .base import DetectorDecision


DEFAULT_KEYWORDS = [
    r"bomb", r"explosive", r"weapon", r"chemical weapon",
    r"bioweapon", r"nerve agent", r"ricin", r"sarin", r"anthrax",
    r"malware", r"ransomware", r"phishing", r"keylogger", r"botnet",
    r"exploit", r"sql injection", r"buffer overflow", r"rootkit",
    r"hack into", r"unauthorized access", r"steal credit card",
    r"child sexual", r"csam", r"how to kill", r"assassinate",
    r"counterfeit", r"money laundering",
]


class KeywordDetector:
    name = "keyword"

    def __init__(self, keywords=None):
        keywords = keywords or DEFAULT_KEYWORDS
        self.pattern = re.compile("|".join(keywords), re.IGNORECASE)

    def evaluate(self, prompt: str) -> DetectorDecision:
        match = self.pattern.search(prompt or "")
        blocked = match is not None
        return DetectorDecision(
            blocked=blocked,
            score=1.0 if blocked else 0.0,
            label="harmful" if blocked else "benign",
        )
