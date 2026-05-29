# n8n Orchestration View

`phase1_workflow.json` implements a single-round orchestration of the
pipeline used by the Python runner, intended as a visual / documentation
artifact:

```
AdvBench (HTTP) → Take 20 → Attacker (Mixtral-8x22B-Instruct via OpenRouter)
                          → Detector (Llama-Guard-3 via OpenRouter)
                          → if allowed → Target (GPT-4o) → Judge (GPT-4o)
                          → JSONL trace
```

Import via *Workflows → Import from File*. Environment variables expected:

- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`

The Python runner remains the source of truth for multi-round adaptive
attacks and the full experimental grid; this workflow demonstrates how the
same pipeline maps to an n8n orchestration graph.
