# Phase 1 Dashboard

```bash
npm install
npm run dev    # vite at :5173, proxies /api to backend at :8000
```

Visualizes:

- **Summary chart**: ASR per defense, grouped by attack and budget.
- **Sessions list**: filter by attack and defense.
- **Attack Trace Graph**: ReactFlow graph of the session's round tree. For PAIR
  the tree degenerates to a linear chain; for TAP the tree shows branching,
  pruning, and the leaf that reached jailbreak (if any). Node color encodes
  judge score and detector decision.
