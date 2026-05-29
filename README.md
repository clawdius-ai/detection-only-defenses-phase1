# Detection-Only Defenses for LLMs — Phase 1

Adaptive jailbreak attacks (PAIR, TAP) evaluated against detector-only defenses on AdvBench.

## Overview

This repository implements and evaluates adaptive jailbreak attack baselines and detector-only defense baselines on the AdvBench dataset.

Adaptive attacks implemented:

- **PAIR** — Prompt Automatic Iterative Refinement (Chao et al., 2023, arXiv:2310.08419)
- **TAP** — Tree of Attacks with Pruning (Mehrotra et al., 2024, arXiv:2312.02119)

Detector-only defense baselines evaluated:

- **Keyword Filter** — conservative AdvBench-derived blocklist (lower-bound baseline)
- **PromptGuard** — Meta `Prompt-Guard-86M` input classifier
- **Llama-Guard-3-8B** — safety classifier via OpenRouter

## Pipeline

```
AdvBench prompt → [Attacker LLM] → candidate adversarial prompt
                                  → [Detector] → allow / block
                                  → [Target LLM] → response
                                  → [Judge LLM] → score 1–10
                                  → next round (until success or budget B)
```

## Experimental Settings

| Component | Choice |
|-----------|--------|
| Dataset   | AdvBench `harmful_behaviors.csv` (first 100 prompts; default subset N=20) |
| Attacker  | Mixtral-8x22B-Instruct (`mistralai/mixtral-8x22b-instruct` via OpenRouter) |
| Target    | GPT-4o (`gpt-4o-2024-08-06` via OpenAI) |
| Judge     | GPT-4o (`gpt-4o-2024-08-06` via OpenAI) with 1–10 harm scoring rubric |
| Budgets   | B ∈ {5, 10} target queries per behavior |

## Repository Layout

```
src/
  attacks/       PAIR + TAP implementations
  defenses/      Detector-only defenses (PromptGuard, Llama-Guard, keyword)
  targets/       Target LLM wrapper
  judge/         Judge LLM (PAIR scoring rubric)
  utils/         Tracing, logging, API clients
  data/          AdvBench
configs/         YAML experiment configs
results/traces/  JSONL session traces (round-level)
backend/         FastAPI trace server
frontend/        React dashboard with PAIR/TAP graph visualization
n8n/             n8n workflow JSON
report/          Phase 1 markdown report
scripts/         Entry points
```

## Quick Start

```bash
cp .env.example .env
# Populate OPENAI_API_KEY and OPENROUTER_API_KEY
pip install -r requirements.txt
python scripts/run_experiment.py --config configs/pair_b5_nodefense.yaml
python scripts/run_experiment.py --config configs/tap_b5_nodefense.yaml
python scripts/aggregate_results.py
```

Full experimental grid:

```bash
bash scripts/run_all.sh
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
- Zou, A. et al. *Universal and Transferable Adversarial Attacks on Aligned Language Models.* arXiv:2307.15043 (AdvBench)
- Inan, H. et al. *Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations.* arXiv:2312.06674

## License

MIT (research / academic use).
