"""Shared helpers for parsing attacker JSON output."""
from __future__ import annotations

import json
import re
from typing import Dict, Optional


_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def parse_attacker_json(raw: str) -> Optional[Dict[str, str]]:
    """Attempt to parse the JSON object returned by the attacker LLM.

    The attacker is instructed to return ``{"improvement": "...", "prompt": "..."}``
    but may add commentary or use code fences. The first balanced JSON object is
    extracted and parsed. Returns None on failure.
    """
    if not raw:
        return None
    candidates = []
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence_match:
        candidates.append(fence_match.group(1).strip())
    candidates.append(raw.strip())
    block = _JSON_BLOCK_RE.search(raw)
    if block:
        candidates.append(block.group(0))
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict) and "prompt" in obj:
                obj.setdefault("improvement", "")
                return {"improvement": str(obj["improvement"]),
                        "prompt": str(obj["prompt"])}
        except json.JSONDecodeError:
            continue
    return None
