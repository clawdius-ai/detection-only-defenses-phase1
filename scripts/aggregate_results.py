"""Aggregate all JSONL traces under results/traces and emit a summary table.

Produces:
  - results/summary.csv      : per-cell rollup using REAL-API rows only.
  - results/summary_all.csv  : per-cell rollup including demo rows (with demo_sessions col).
  - results/per_prompt.csv   : per-prompt best score, success indicator (real-only).

Demo rows (extra.demo == True) are excluded from summary.csv so the headline
numbers reflect actual experiments and not the synthetic placeholder set
shipped for dashboard bootstrap. Use --include-demo to fold them back in.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from collections import defaultdict


def _is_demo(row: dict) -> bool:
    extra = row.get("extra") or {}
    return extra.get("demo") is True


def _write_summary(rows, out_path):
    sessions = defaultdict(lambda: {"max_score": 1, "success": False,
                                     "rounds": 0, "blocked_rounds": 0,
                                     "demo": False, "goal": ""})
    for r in rows:
        key = (r["attack"], r["defense"], r["budget"], r["advbench_index"],
               r["session_id"])
        s = sessions[key]
        s["max_score"] = max(s["max_score"], r["judge_score"])
        s["success"] = s["success"] or r["success"]
        s["rounds"] += 1
        if r["detector_decision"] == "block":
            s["blocked_rounds"] += 1
        s["goal"] = r["goal"]
        if _is_demo(r):
            s["demo"] = True

    cells = defaultdict(lambda: {"n": 0, "success": 0, "rounds": 0,
                                  "blocked_rounds": 0, "scores": [],
                                  "demo_sessions": 0})
    for (attack, defense, budget, _idx, _sid), s in sessions.items():
        c = cells[(attack, defense, budget)]
        c["n"] += 1
        c["success"] += int(s["success"])
        c["rounds"] += s["rounds"]
        c["blocked_rounds"] += s["blocked_rounds"]
        c["scores"].append(s["max_score"])
        if s["demo"]:
            c["demo_sessions"] += 1

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["attack", "defense", "budget", "N", "ASR",
                    "avg_queries", "block_rate", "mean_max_score",
                    "demo_sessions"])
        for (attack, defense, budget), c in sorted(cells.items()):
            asr = c["success"] / max(1, c["n"])
            avg_q = c["rounds"] / max(1, c["n"])
            block_rate = c["blocked_rounds"] / max(1, c["rounds"])
            mean_max = sum(c["scores"]) / max(1, len(c["scores"]))
            w.writerow([attack, defense, budget, c["n"],
                        f"{asr:.4f}", f"{avg_q:.2f}",
                        f"{block_rate:.4f}", f"{mean_max:.2f}",
                        c["demo_sessions"]])
    return sessions


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-demo", action="store_true",
                    help="Include demo rows in results/summary.csv (default: real-only).")
    args = ap.parse_args()

    rows = []
    for path in sorted(glob.glob("results/traces/*.jsonl")):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    if not rows:
        print("No traces found.")
        return 0

    real_rows = [r for r in rows if not _is_demo(r)]
    demo_rows = [r for r in rows if _is_demo(r)]
    print(f"loaded {len(rows)} rows ({len(real_rows)} real, {len(demo_rows)} demo)")

    headline_rows = rows if args.include_demo else real_rows
    _write_summary(headline_rows, "results/summary.csv")
    print("wrote results/summary.csv"
          + (" (real-only)" if not args.include_demo else " (real+demo)"))

    # Always also write an all-inclusive view for reference.
    _write_summary(rows, "results/summary_all.csv")
    print("wrote results/summary_all.csv (real+demo)")

    # Build sessions dict for per_prompt from real rows only.
    sessions = defaultdict(lambda: {"max_score": 1, "success": False,
                                     "rounds": 0, "blocked_rounds": 0,
                                     "goal": ""})
    for r in real_rows:
        key = (r["attack"], r["defense"], r["budget"], r["advbench_index"],
               r["session_id"])
        s = sessions[key]
        s["max_score"] = max(s["max_score"], r["judge_score"])
        s["success"] = s["success"] or r["success"]
        s["rounds"] += 1
        if r["detector_decision"] == "block":
            s["blocked_rounds"] += 1
        s["goal"] = r["goal"]

    # Per-prompt (real rows only)
    per_path = "results/per_prompt.csv"
    with open(per_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["attack", "defense", "budget", "advbench_index",
                    "session_id", "max_score", "success", "rounds",
                    "blocked_rounds", "goal"])
        for (attack, defense, budget, idx, sid), s in sorted(sessions.items()):
            w.writerow([attack, defense, budget, idx, sid,
                        s["max_score"], int(s["success"]),
                        s["rounds"], s["blocked_rounds"], s["goal"]])
    print(f"wrote {per_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
