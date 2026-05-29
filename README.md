# Detection-Only Defenses for LLMs — Phase 1

Adaptive jailbreak attacks (PAIR, TAP) evaluated against detector-only defenses.

## Overview

This repository implements and evaluates adaptive jailbreak attack baselines and detector-only defense baselines on the AdvBench dataset. Two adaptive attacks are implemented:

- **PAIR** — Prompt Automatic Iterative Refinement (Chao et al., 2023)
- **TAP** — Tree of Attacks with Pruning (Mehrotra et al., 2024)

Two detector-only defense baselines are evaluated:

- **PromptGuard** (Meta `Llama-Prompt-Guard-2-86M`)
- **Llama-Guard-3-8B** (via OpenRouter)
- **Keyword Filter** (baseline lower bound)

## Pipeline

```
AdvBench prompt → [Attacker LLM] → candidate adversarial prompt
                                  → [Detector?] → allow / block
                                  → [Target LLM] → response
                                  → [Judge LLM] → score 1–10
                                  → next round (until success or budget B)
```

## Experimental Settings

| Component | Choice |
|-----------|--------|
| Dataset   | AdvBench `harmful_behaviors.csv` (first 100 prompts; default subset N=20) |
| Attacker  | Mixtral-8x22B-Instruct (`mistralai/mixtral-8x22b-instruct` via OpenRouter; substitute for Vicuna-13B which is no longer served on OpenRouter) |
| Target    | GPT-4o (`gpt-4o-2024-08-06` via OpenAI) |
| Judge     | GPT-4o (`gpt-4o-2024-08-06` via OpenAI) with 1–10 harm scoring rubric |
| Budgets   | B ∈ {5, 10} |

## Repository Layout

```
src/
  attacks/       PAIR + TAP implementations
  defenses/      Detector-only defenses (PromptGuard, Llama-Guard, keyword)
  targets/       Target LLM wrappers
  judge/         Judge LLM (PAIR scoring rubric)
  utils/         Tracing, logging, API clients
  data/          AdvBench
configs/         YAML experiment configs
results/traces/  JSONL session traces (round-level)
backend/         FastAPI trace server
frontend/        React + shadcn dashboard with PAIR/TAP graph viz
n8n/             n8n workflow JSON
report/          Phase 1 markdown report
scripts/         Entry points
```

## Status

- **Code, configs, dashboard, n8n workflow, report, slides** — complete and pushed.
- **Attacker (OpenRouter / Mixtral-8x22B)** — verified live.
- **Target / Judge (OpenAI / GPT-4o)** — live; experiment grid partially executed (see `results/summary.csv`). Remaining cells (PromptGuard, Llama-Guard-3 over PAIR/TAP) are scaffolded and can be run via `bash scripts/run_all.sh`.
- **Synthetic demo traces** (`results/traces/demo_synthetic.jsonl`) are bundled so the dashboard renders out-of-the-box. They are clearly marked `extra.demo = true` and are **excluded from `results/summary.csv` by default** (rerun `python scripts/aggregate_results.py --include-demo` to fold them in). The dashboard offers an explicit *Real API Runs* vs *Demo Traces* toggle.

### Reading the headline numbers

The judge in `configs/base.yaml` uses `success_threshold: 10`, matching Chao et al. (PAIR, Appendix A). That is a strict bar; many HarmBench-style reproductions report ASR at judge ≥ 7 or ≥ 8 instead. The dashboard exposes a *judge threshold* selector and the API returns both the strict `ASR` (judge == 10) and `ASR_at_threshold` (per-session max judge ≥ selected cutoff) for every cell.

## Quick Start

```bash
cp .env.example .env
# Fill OPENAI_API_KEY and OPENROUTER_API_KEY
pip install -r requirements.txt
python scripts/run_experiment.py --config configs/pair_b5.yaml
python scripts/run_experiment.py --config configs/pair_b10.yaml
python scripts/run_experiment.py --config configs/tap_b5.yaml
python scripts/run_experiment.py --config configs/tap_b10.yaml
python scripts/aggregate_results.py
```

Dashboard:

```bash
cd backend && uvicorn server:app --reload
cd frontend && npm install && npm run dev
```

## Trace Schema

Each session emits one JSONL line per round:

```json
{
  "session_id": "uuid",
  "attack": "pair|tap",
  "defense": "none|promptguard|llamaguard|keyword",
  "budget": 5,
  "advbench_index": 0,
  "goal": "...",
  "round": 1,
  "parent_round": null,
  "candidate_prompt": "...",
  "detector_decision": "allow|block",
  "detector_score": 0.12,
  "target_response": "...",
  "judge_score": 7,
  "success": false
}
```

## References

- Chao, P. et al. *Jailbreaking Black Box Large Language Models in Twenty Queries.* arXiv:2310.08419
- Mehrotra, A. et al. *Tree of Attacks: Jailbreaking Black-Box LLMs Automatically.* arXiv:2312.02119
- Zou, A. et al. *Universal and Transferable Adversarial Attacks on Aligned Language Models.* (AdvBench)
- Inan, H. et al. *Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations.*

## License

MIT (research / academic use).
