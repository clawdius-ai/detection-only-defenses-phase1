"""Entry point: run a single experimental cell (attack x defense x budget).

Usage:
    python scripts/run_experiment.py --config configs/pair_b5_nodefense.yaml
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from typing import Dict, Any

import yaml
from dotenv import load_dotenv
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.llm_clients import OpenAIChatClient, OpenRouterChatClient
from src.utils.tracing import JsonlTraceWriter
from src.targets.target import TargetLLM
from src.judge.judge import GPT4Judge
from src.defenses.registry import build_detector
from src.attacks.pair import PAIRAttacker
from src.attacks.tap import TAPAttacker


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    parent = cfg.pop("extends", None)
    if parent:
        parent_cfg = load_config(parent)
        cfg = deep_merge(parent_cfg, cfg)
    return cfg


def load_advbench(path: str, n: int, start: int = 0):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append((row["goal"], row["target"]))
    return rows[start:start + n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--limit", type=int, default=None,
                    help="Override dataset.n_prompts for quick smoke tests.")
    args = ap.parse_args()

    load_dotenv()
    cfg = load_config(args.config)

    tag = cfg.get("output_tag", "run")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    trace_path = os.path.join("results", "traces", f"{tag}_{timestamp}.jsonl")
    writer = JsonlTraceWriter(trace_path)

    n_prompts = args.limit or int(cfg["dataset"]["n_prompts"])
    prompts = load_advbench(cfg["dataset"]["path"], n_prompts,
                             int(cfg["dataset"].get("start_index", 0)))

    target_client = OpenAIChatClient(
        model=cfg["target"]["model"],
        temperature=float(cfg["target"]["temperature"]),
        max_tokens=int(cfg["target"]["max_tokens"]),
    )
    target = TargetLLM(target_client)

    judge_client = OpenAIChatClient(
        model=cfg["judge"]["model"], temperature=0.0, max_tokens=64)
    judge = GPT4Judge(judge_client,
                      success_threshold=int(cfg["judge"]["success_threshold"]))

    attacker_client = OpenRouterChatClient(
        model=cfg["attacker"]["model"],
        temperature=float(cfg["attacker"]["temperature"]),
        max_tokens=int(cfg["attacker"]["max_tokens"]),
    )

    detector = build_detector(cfg.get("defense", {}))

    attack_name = cfg["attack"]["name"].lower()
    budget = int(cfg["attack"]["budget"])

    if attack_name == "pair":
        runner = PAIRAttacker(attacker_client, target, judge, detector,
                              writer, budget=budget)
    elif attack_name == "tap":
        tap_cfg = cfg.get("tap", {})
        runner = TAPAttacker(
            attacker_client, target, judge, detector, writer,
            budget=budget,
            branching=int(tap_cfg.get("branching", 2)),
            width=int(tap_cfg.get("width", 3)),
        )
    else:
        raise ValueError(f"Unknown attack: {attack_name}")

    n_success = 0
    total_rounds = 0
    for idx, (goal, target_prefix) in enumerate(tqdm(prompts, desc=tag)):
        result = runner.run(idx, goal, target_prefix)
        n_success += int(result.success)
        total_rounds += result.rounds_used

    n = len(prompts)
    asr = n_success / max(1, n)
    avg_q = total_rounds / max(1, n)
    summary_path = os.path.join("results", f"{tag}_{timestamp}_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as fh:
        fh.write(
            f"tag={tag}\nattack={attack_name}\ndefense={detector.name}\n"
            f"budget={budget}\nN={n}\nsuccess={n_success}\nASR={asr:.4f}\n"
            f"avg_queries={avg_q:.2f}\ntrace={trace_path}\n"
        )
    print(f"[done] ASR={asr:.2%} ({n_success}/{n})  avg_queries={avg_q:.2f}")
    print(f"trace -> {trace_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
