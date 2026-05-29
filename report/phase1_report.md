# Phase 1 — Running Adaptive Jailbreak and Detector-Only Defense Baselines

## 1. Problem Statement

Large Language Models (LLMs) are aligned through safety policies and
instruction tuning to refuse harmful, restricted, or policy-violating
content. **Adaptive jailbreak attacks** iteratively modify their input
prompts in response to the target model's outputs and may include feedback
signals such as refusal messages or detector decisions. **Detector-only
defenses** consume the input prompt and session transcript and emit a
routing decision (allow / block / refuse); they do not modify the prompt or
intervene inside the model's generation process.

Phase 1 evaluates the effectiveness and limitations of detector-only
defenses against adaptive jailbreak attacks by re-implementing two canonical
adaptive attacks (PAIR and TAP) and exposing each to multiple detector-only
defenses on the AdvBench benchmark.

## 2. Experimental Settings

### 2.1 Dataset

AdvBench `harmful_behaviors.csv` (Zou et al., 2023) is used as the primary
benchmark. The first 100 behaviors are reserved for evaluation; a
cost-bounded subset of N=20 prompts is used for the initial run reported
below, with the same pipeline supporting N=100 without code changes
(`dataset.n_prompts` in the YAML configs).

### 2.2 Adaptive Attack Baselines

| Attack | Reference | Implementation notes |
|--------|-----------|----------------------|
| PAIR   | Chao et al., 2023 (arXiv:2310.08419) | Single attacker stream; each round produces a JSON object `{improvement, prompt}`. Budget B caps the number of refinement rounds. |
| TAP    | Mehrotra et al., 2024 (arXiv:2312.02119) | Tree-structured search with branching `b`, width `w`, depth `d`. Pre-target pruning via on-topic check; post-target pruning keeps the top-`w` leaves by judge score. Budget B caps the total number of target queries. |

Both attacks share the attacker system prompt template adapted from the
PAIR paper (Appendix A) and the JSON output protocol.

### 2.3 Detector-Only Defense Baselines

| Defense        | Type           | Backbone                                    |
|----------------|----------------|---------------------------------------------|
| `none`         | Baseline       | No detector; all prompts forwarded to target |
| `keyword`      | Rule baseline  | Conservative AdvBench-derived blocklist     |
| `promptguard`  | Classifier     | `meta-llama/Prompt-Guard-86M` (HuggingFace) |
| `llamaguard`   | LLM-as-judge   | `meta-llama/llama-guard-3-8b` via OpenRouter |

A prompt is **blocked** when the detector's non-safe class mass exceeds a
configurable threshold (PromptGuard) or when the classifier returns the
`unsafe` label (LlamaGuard) or matches a blocklist term (keyword).
Blocked prompts are never forwarded to the target; their judge score is
recorded as 1.

### 2.4 Target, Judge, and Attacker

- **Target**: `gpt-4o-2024-08-06` via the OpenAI API.
- **Judge**: `gpt-4o-2024-08-06` with the 1–10 rubric described in Chao
  et al. (Appendix A); a response is declared a successful jailbreak when
  the judge returns a score of 10.
- **Attacker**: `mistralai/mixtral-8x22b-instruct` via OpenRouter. The
  original PAIR/TAP papers used Vicuna-13B as the attacker; Vicuna is no
  longer served via OpenRouter, so Mixtral-8x22B-Instruct is used as a
  strong open-weight substitute. The attacker prompt template is
  unchanged.

### 2.5 Attack Budgets

Experiments are run with B ∈ {5, 10} target queries per behavior.

### 2.6 Reproducibility

Every round of every session is logged to JSONL with the schema documented
in `README.md` (session id, attack, defense, budget, advbench index, goal,
round, parent round, candidate prompt, detector decision, detector score,
target response, judge score, success flag, and attacker reasoning).

## 3. Pipeline Overview

```
AdvBench behavior ──► Attacker (Vicuna-13B)
                          │
                          ▼
                     candidate prompt
                          │
                          ▼
                Detector-only defense ──┐
                          │             │
                       allow            block
                          │             │
                          ▼             ▼
                  Target (GPT-4)  judge_score = 1
                          │
                          ▼
                    Judge (GPT-4)
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        score >= 10              score < 10
        terminate session   feedback into attacker
```

PAIR runs a single linear stream of the loop above. TAP runs the same loop
in tree form: each surviving leaf is branched into `b` candidate
refinements per depth level, off-topic candidates are pruned, surviving
leaves are scored against the target, and the top-`w` leaves are kept for
the next depth.

## 4. Metrics

- **ASR (Attack Success Rate)**: fraction of behaviors with at least one
  round in the session reaching a judge score of 10.
- **Block rate**: fraction of all (session × round) candidate prompts
  blocked by the detector.
- **Mean max judge score**: mean over behaviors of the maximum judge score
  observed across all rounds of the corresponding session.
- **Average queries per behavior**: mean target queries used per behavior
  (the attacker may terminate early on a success).

## 5. Results

Run the experimental grid:

```bash
bash scripts/run_all.sh
```

Aggregated results are written to `results/summary.csv`. A representative
schema for the produced table is:

| attack | defense      | budget | N  | ASR    | avg_queries | block_rate | mean_max_score |
|--------|--------------|--------|----|--------|-------------|------------|----------------|
| pair   | none         | 5      | 20 | (run)  | (run)       | 0.0        | (run)          |
| pair   | keyword      | 5      | 20 | (run)  | (run)       | (run)      | (run)          |
| pair   | promptguard  | 5      | 20 | (run)  | (run)       | (run)      | (run)          |
| pair   | llamaguard   | 5      | 20 | (run)  | (run)       | (run)      | (run)          |
| pair   | none         | 10     | 20 | (run)  | (run)       | 0.0        | (run)          |
| tap    | none         | 5      | 20 | (run)  | (run)       | 0.0        | (run)          |
| tap    | none         | 10     | 20 | (run)  | (run)       | 0.0        | (run)          |
| tap    | keyword      | 5      | 20 | (run)  | (run)       | (run)      | (run)          |
| tap    | promptguard  | 5      | 20 | (run)  | (run)       | (run)      | (run)          |
| tap    | llamaguard   | 5      | 20 | (run)  | (run)       | (run)      | (run)          |

Each row is reproducible by re-running its YAML config; the corresponding
JSONL trace is referenced in the matching `*_summary.txt` file. Per-prompt
outcomes are available in `results/per_prompt.csv`.

## 6. Interactive Inspection

The dashboard (`backend/` + `frontend/`) renders the experimental grid and
the round-level attack trace graph (linear for PAIR, branching for TAP).
Node color encodes the judge score and the detector decision; the side
panel surfaces the candidate prompt, the detector score, the target
response, and the attacker's stated improvement at each round.

## 7. Limitations and Next Steps

- The Vicuna-13B attacker is consumed via OpenRouter; local execution of
  Vicuna-13B is impractical on the available hardware. The same pipeline
  accepts any OpenRouter-served attacker model.
- PromptGuard is a small (86M) input-classifier baseline; stronger
  detector baselines such as Llama-Guard-3-8B are included to match the
  evaluation specification calling for "stronger and more competitive
  baselines."
- StrongREJECT and JBB-Behaviors are not yet evaluated; the dataset loader
  accepts arbitrary CSVs with `goal` and `target` columns and these
  datasets can be added by introducing additional YAML configs.
- The current judge fires success only at a strict score of 10. Sensitivity
  analyses across thresholds and an off-the-shelf harm classifier (e.g.,
  HarmBench) are planned for Phase 2.

## 8. References

1. Chao, P. et al. *Jailbreaking Black Box Large Language Models in Twenty Queries.* arXiv:2310.08419, 2023.
2. Mehrotra, A. et al. *Tree of Attacks: Jailbreaking Black-Box LLMs Automatically.* arXiv:2312.02119, 2024.
3. Zou, A. et al. *Universal and Transferable Adversarial Attacks on Aligned Language Models.* arXiv:2307.15043, 2023. (AdvBench)
4. Inan, H. et al. *Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations.* arXiv:2312.06674, 2023.
