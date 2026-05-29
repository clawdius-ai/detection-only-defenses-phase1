#!/usr/bin/env bash
# Run the full Phase 1 experimental grid.
set -euo pipefail
cd "$(dirname "$0")/.."

CONFIGS=(
  configs/pair_b5_nodefense.yaml
  configs/pair_b10_nodefense.yaml
  configs/tap_b5_nodefense.yaml
  configs/tap_b10_nodefense.yaml
  configs/pair_b5_keyword.yaml
  configs/pair_b5_promptguard.yaml
  configs/pair_b5_llamaguard.yaml
  configs/tap_b5_keyword.yaml
  configs/tap_b5_promptguard.yaml
  configs/tap_b5_llamaguard.yaml
)

for cfg in "${CONFIGS[@]}"; do
  echo "=== $cfg ==="
  python scripts/run_experiment.py --config "$cfg"
done

python scripts/aggregate_results.py
