"""Aggregate all JSONL traces under results/traces and emit a summary table.

Produces:
  - results/summary.csv   : per-run rollup (attack, defense, budget, ASR, ...)
  - results/per_prompt.csv: per-prompt best score, success indicator
"""
from __future__ import annotations

import csv
import glob
import json
import os
from collections import defaultdict


def main() -> int:
    rows = []
    for path in sorted(glob.glob("results/traces/*.jsonl")):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    if not rows:
        print("No traces found.")
        return 0

    # Per-session rollup
    sessions = defaultdict(lambda: {"max_score": 1, "success": False,
                                     "rounds": 0, "blocked_rounds": 0})
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

    # Per-cell rollup
    cells = defaultdict(lambda: {"n": 0, "success": 0, "rounds": 0,
                                  "blocked_rounds": 0, "scores": []})
    for (attack, defense, budget, idx, _sid), s in sessions.items():
        c = cells[(attack, defense, budget)]
        c["n"] += 1
        c["success"] += int(s["success"])
        c["rounds"] += s["rounds"]
        c["blocked_rounds"] += s["blocked_rounds"]
        c["scores"].append(s["max_score"])

    os.makedirs("results", exist_ok=True)
    summary_path = "results/summary.csv"
    with open(summary_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["attack", "defense", "budget", "N", "ASR",
                    "avg_queries", "block_rate", "mean_max_score"])
        for (attack, defense, budget), c in sorted(cells.items()):
            asr = c["success"] / max(1, c["n"])
            avg_q = c["rounds"] / max(1, c["n"])
            block_rate = c["blocked_rounds"] / max(1, c["rounds"])
            mean_max = sum(c["scores"]) / max(1, len(c["scores"]))
            w.writerow([attack, defense, budget, c["n"],
                        f"{asr:.4f}", f"{avg_q:.2f}",
                        f"{block_rate:.4f}", f"{mean_max:.2f}"])
    print(f"wrote {summary_path}")

    # Per-prompt
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
