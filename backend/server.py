"""FastAPI trace server.

Serves aggregated experiment summaries and full session traces to the
React dashboard.

Endpoints
---------
GET /api/summary          -> per-cell rollups (attack x defense x budget)
GET /api/sessions         -> list of session metadata
GET /api/sessions/{id}    -> all rounds for a given session id
GET /api/traces           -> raw JSONL rows (paginated)
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

TRACE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         "results", "traces")

app = FastAPI(title="Detection-Only Defenses Phase 1 — Trace API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_all() -> List[Dict]:
    rows: List[Dict] = []
    for path in sorted(glob.glob(os.path.join(TRACE_DIR, "*.jsonl"))):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _is_demo(row: Dict) -> bool:
    return row.get("extra", {}).get("demo") is True


def _filter_mode(rows: List[Dict], mode: str = "all") -> List[Dict]:
    if mode == "demo":
        return [r for r in rows if _is_demo(r)]
    if mode == "real":
        return [r for r in rows if not _is_demo(r)]
    return rows


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/summary")
def summary(mode: str = "all") -> Dict[str, List[Dict]]:
    rows = _filter_mode(_load_all(), mode)
    cells: Dict = defaultdict(lambda: {"n_sessions": set(), "successes": set(),
                                         "rounds": 0, "blocked": 0,
                                         "scores": []})
    for r in rows:
        key = (r["attack"], r["defense"], r["budget"])
        c = cells[key]
        c["n_sessions"].add(r["session_id"])
        c["rounds"] += 1
        if r["detector_decision"] == "block":
            c["blocked"] += 1
        c["scores"].append(r["judge_score"])
        if r["success"]:
            c["successes"].add(r["session_id"])
    out = []
    for (attack, defense, budget), c in sorted(cells.items()):
        n = len(c["n_sessions"])
        out.append({
            "attack": attack,
            "defense": defense,
            "budget": budget,
            "N": n,
            "demo_sessions": len({
                r["session_id"] for r in rows
                if (r["attack"], r["defense"], r["budget"]) == (attack, defense, budget)
                and _is_demo(r)
            }),
            "ASR": round(len(c["successes"]) / max(1, n), 4),
            "block_rate": round(c["blocked"] / max(1, c["rounds"]), 4),
            "mean_judge": round(sum(c["scores"]) / max(1, len(c["scores"])), 2),
            "total_rounds": c["rounds"],
        })
    return {"summary": out}


@app.get("/api/sessions")
def sessions(attack: Optional[str] = None, defense: Optional[str] = None,
             budget: Optional[int] = None, mode: str = "all") -> Dict[str, List[Dict]]:
    rows = _filter_mode(_load_all(), mode)
    sess: Dict[str, Dict] = {}
    for r in rows:
        if attack and r["attack"] != attack:
            continue
        if defense and r["defense"] != defense:
            continue
        if budget is not None and r["budget"] != budget:
            continue
        sid = r["session_id"]
        s = sess.setdefault(sid, {
            "session_id": sid, "attack": r["attack"],
            "defense": r["defense"], "budget": r["budget"],
            "advbench_index": r["advbench_index"], "goal": r["goal"],
            "max_score": 1, "success": False, "rounds": 0,
            "demo": False,
        })
        s["max_score"] = max(s["max_score"], r["judge_score"])
        s["success"] = s["success"] or r["success"]
        s["rounds"] += 1
        s["demo"] = s["demo"] or _is_demo(r)
    return {"sessions": list(sess.values())}


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str) -> Dict:
    rows = [r for r in _load_all() if r["session_id"] == session_id]
    if not rows:
        raise HTTPException(404, "session not found")
    rows.sort(key=lambda r: r["round"])
    return {"session_id": session_id, "rounds": rows}


@app.get("/api/traces")
def traces(limit: int = 200, offset: int = 0, mode: str = "all") -> Dict[str, List[Dict]]:
    rows = _filter_mode(_load_all(), mode)
    return {"total": len(rows), "rows": rows[offset:offset + limit]}
