# Trace API

```bash
pip install -r ../requirements.txt
uvicorn server:app --reload --port 8000
```

Endpoints:

- `GET /api/summary` — per-cell rollup
- `GET /api/sessions?attack=pair&defense=none&budget=5`
- `GET /api/sessions/{session_id}` — round-level rows
- `GET /api/traces?limit=200&offset=0`
