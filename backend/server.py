"""FastAPI trace server.

Serves aggregated experiment summaries and full session traces to the
React dashboard.

Endpoints
---------
GET /api/health           -> liveness probe + cache stats
GET /api/summary          -> per-cell rollups (attack x defense x budget)
GET /api/sessions         -> list of session metadata (filterable + sortable)
GET /api/sessions/{id}    -> all rounds for a given session id
GET /api/runs             -> list of trace files with metadata
GET /api/traces           -> raw JSONL rows (paginated)
GET /api/per_prompt       -> per-advbench-prompt success rollup across cells

Implementation notes
--------------------
The trace JSONL files are immutable per-run; we cache the parsed rows in
memory and invalidate based on the maximum mtime in the trace directory.
This keeps the dashboard snappy even as more traces accumulate.
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Query
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


# ---------------------------------------------------------------------------
# Caching layer
# ---------------------------------------------------------------------------

_CACHE: Dict[str, object] = {
    "signature": None,   # (file_count, max_mtime, total_bytes)
    "rows": [],
    "files": [],
}


def _scan_files() -> Tuple[List[str], Tuple[int, float, int]]:
    paths = sorted(glob.glob(os.path.join(TRACE_DIR, "*.jsonl")))
    if not paths:
        return [], (0, 0.0, 0)
    max_mt = 0.0
    total_bytes = 0
    for p in paths:
        try:
            st = os.stat(p)
            max_mt = max(max_mt, st.st_mtime)
            total_bytes += st.st_size
        except OSError:
            pass
    return paths, (len(paths), max_mt, total_bytes)


def _load_all() -> List[Dict]:
    paths, sig = _scan_files()
    if _CACHE.get("signature") == sig and _CACHE.get("rows"):
        return _CACHE["rows"]  # type: ignore[return-value]
    rows: List[Dict] = []
    files_meta: List[Dict] = []
    for path in paths:
        n_rows = 0
        sessions_in_file = set()
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rows.append(row)
                n_rows += 1
                sessions_in_file.add(row.get("session_id"))
        try:
            st = os.stat(path)
            files_meta.append({
                "file": os.path.basename(path),
                "rows": n_rows,
                "sessions": len(sessions_in_file),
                "size_bytes": st.st_size,
                "mtime": st.st_mtime,
            })
        except OSError:
            pass
    _CACHE["signature"] = sig
    _CACHE["rows"] = rows
    _CACHE["files"] = files_meta
    return rows


def _is_demo(row: Dict) -> bool:
    extra = row.get("extra") or {}
    return extra.get("demo") is True


def _filter_mode(rows: List[Dict], mode: str = "all") -> List[Dict]:
    if mode == "demo":
        return [r for r in rows if _is_demo(r)]
    if mode == "real":
        return [r for r in rows if not _is_demo(r)]
    return rows


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> Dict[str, object]:
    rows = _load_all()
    files = _CACHE.get("files") or []
    return {
        "status": "ok",
        "trace_dir": TRACE_DIR,
        "n_rows": len(rows),
        "n_files": len(files),  # type: ignore[arg-type]
        "demo_rows": sum(1 for r in rows if _is_demo(r)),
        "real_rows": sum(1 for r in rows if not _is_demo(r)),
    }


@app.get("/api/runs")
def runs() -> Dict[str, List[Dict]]:
    """List the underlying JSONL trace files for diagnostics."""
    _load_all()  # ensure cache populated
    return {"files": list(_CACHE.get("files") or [])}  # type: ignore[arg-type]


@app.get("/api/summary")
def summary(mode: str = "all") -> Dict[str, List[Dict]]:
    rows = _filter_mode(_load_all(), mode)

    # Per-session rollup (so cell aggregates use per-session metrics, not raw row counts).
    sessions: Dict[Tuple, Dict] = {}
    for r in rows:
        key = (r["attack"], r["defense"], r["budget"], r["session_id"])
        s = sessions.setdefault(key, {
            "max_judge": int(r.get("judge_score", 1)),
            "success": False,
            "rounds": 0,
            "blocked": 0,
            "demo": False,
        })
        s["max_judge"] = max(s["max_judge"], int(r.get("judge_score", 1)))
        s["success"] = s["success"] or bool(r.get("success"))
        s["rounds"] += 1
        if r.get("detector_decision") == "block":
            s["blocked"] += 1
        if _is_demo(r):
            s["demo"] = True

    cells: Dict[Tuple, Dict] = defaultdict(lambda: {
        "sessions": 0, "successes": 0, "rounds": 0,
        "blocked": 0, "max_judges": [], "demo_sessions": 0,
    })
    for (attack, defense, budget, _sid), s in sessions.items():
        c = cells[(attack, defense, budget)]
        c["sessions"] += 1
        c["successes"] += int(s["success"])
        c["rounds"] += s["rounds"]
        c["blocked"] += s["blocked"]
        c["max_judges"].append(s["max_judge"])
        if s["demo"]:
            c["demo_sessions"] += 1

    out = []
    for (attack, defense, budget), c in sorted(cells.items()):
        n = c["sessions"]
        out.append({
            "attack": attack,
            "defense": defense,
            "budget": budget,
            "N": n,
            "demo_sessions": c["demo_sessions"],
            "ASR": round(c["successes"] / max(1, n), 4),
            "block_rate": round(c["blocked"] / max(1, c["rounds"]), 4),
            "mean_judge": round(sum(c["max_judges"]) / max(1, len(c["max_judges"])), 2),
            "total_rounds": c["rounds"],
        })
    return {"summary": out}


@app.get("/api/sessions")
def sessions_endpoint(
    attack: Optional[str] = None,
    defense: Optional[str] = None,
    budget: Optional[int] = None,
    mode: str = "all",
    q: Optional[str] = Query(default=None, description="substring filter on goal"),
    sort: str = Query(default="default", description="default|score|rounds|success"),
) -> Dict[str, List[Dict]]:
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
            "session_id": sid,
            "attack": r["attack"],
            "defense": r["defense"],
            "budget": r["budget"],
            "advbench_index": r["advbench_index"],
            "goal": r["goal"],
            "max_score": int(r.get("judge_score", 1)),
            "success": False,
            "rounds": 0,
            "blocked_rounds": 0,
            "demo": False,
        })
        js = int(r.get("judge_score", 1))
        s["max_score"] = max(s["max_score"], js)
        s["success"] = s["success"] or bool(r.get("success"))
        s["rounds"] += 1
        if r.get("detector_decision") == "block":
            s["blocked_rounds"] += 1
        if _is_demo(r):
            s["demo"] = True

    items = list(sess.values())

    # Optional goal substring filter
    if q and isinstance(q, str):
        ql = q.lower()
        items = [s for s in items if ql in s.get("goal", "").lower()]

    # Sort
    if sort == "score":
        items.sort(key=lambda s: (-s["max_score"], s["advbench_index"]))
    elif sort == "rounds":
        items.sort(key=lambda s: (-s["rounds"], s["advbench_index"]))
    elif sort == "success":
        items.sort(key=lambda s: (not s["success"], -s["max_score"], s["advbench_index"]))
    else:
        items.sort(key=lambda s: (s["attack"], s["defense"], s["budget"], s["advbench_index"]))

    return {"sessions": items}


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str) -> Dict:
    rows = [r for r in _load_all() if r["session_id"] == session_id]
    if not rows:
        raise HTTPException(404, "session not found")
    rows.sort(key=lambda r: r["round"])
    return {"session_id": session_id, "rounds": rows}


@app.get("/api/per_prompt")
def per_prompt(mode: str = "all") -> Dict[str, List[Dict]]:
    """Per-advbench-prompt rollup: how often did each prompt get jailbroken?"""
    rows = _filter_mode(_load_all(), mode)
    sessions: Dict[Tuple, Dict] = {}
    for r in rows:
        key = (r["attack"], r["defense"], r["budget"],
               r["advbench_index"], r["session_id"])
        s = sessions.setdefault(key, {
            "goal": r.get("goal", ""),
            "max_judge": int(r.get("judge_score", 1)),
            "success": False,
        })
        s["max_judge"] = max(s["max_judge"], int(r.get("judge_score", 1)))
        s["success"] = s["success"] or bool(r.get("success"))

    # Aggregate by advbench_index across all cells
    by_prompt: Dict[int, Dict] = {}
    for (_attack, _defense, _budget, idx, _sid), s in sessions.items():
        p = by_prompt.setdefault(idx, {
            "advbench_index": idx,
            "goal": s["goal"],
            "attempts": 0,
            "successes": 0,
            "max_judge": 0,
        })
        p["attempts"] += 1
        p["successes"] += int(s["success"])
        p["max_judge"] = max(p["max_judge"], s["max_judge"])

    out = sorted(by_prompt.values(),
                 key=lambda p: (-p["successes"], -p["max_judge"], p["advbench_index"]))
    return {"per_prompt": out}


@app.get("/api/traces")
def traces(limit: int = 200, offset: int = 0, mode: str = "all") -> Dict[str, object]:
    rows = _filter_mode(_load_all(), mode)
    return {"total": len(rows), "rows": rows[offset:offset + limit]}
