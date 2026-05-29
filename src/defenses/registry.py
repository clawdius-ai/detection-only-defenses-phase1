"""Detector factory."""
from __future__ import annotations

from typing import Dict, Any

from .base import Detector, NoDetector
from .keyword import KeywordDetector


def build_detector(spec: Dict[str, Any]) -> Detector:
    name = (spec or {}).get("name", "none").lower()
    if name == "none":
        return NoDetector()
    if name == "keyword":
        return KeywordDetector()
    if name == "promptguard":
        from .promptguard import PromptGuardDetector
        return PromptGuardDetector(
            model_name=spec.get("model", "meta-llama/Prompt-Guard-86M"),
            threshold=float(spec.get("threshold", 0.5)),
        )
    if name == "llamaguard":
        from .llamaguard import LlamaGuardDetector
        return LlamaGuardDetector(
            model=spec.get("model", "meta-llama/llama-guard-3-8b"),
        )
    raise ValueError(f"Unknown detector: {name}")
