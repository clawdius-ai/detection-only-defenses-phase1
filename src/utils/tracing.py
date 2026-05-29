"""Round-level JSONL tracing for reproducibility."""
from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


_LOCK = threading.Lock()


@dataclass
class RoundRecord:
    session_id: str
    attack: str
    defense: str
    budget: int
    advbench_index: int
    goal: str
    round: int
    parent_round: Optional[int]
    candidate_prompt: str
    detector_decision: str
    detector_score: Optional[float]
    target_response: str
    judge_score: int
    success: bool
    extra: Dict[str, Any] = field(default_factory=dict)


class JsonlTraceWriter:
    """Append-only JSONL writer, thread-safe."""

    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path

    def write(self, record: RoundRecord) -> None:
        line = json.dumps(asdict(record), ensure_ascii=False)
        with _LOCK:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]
