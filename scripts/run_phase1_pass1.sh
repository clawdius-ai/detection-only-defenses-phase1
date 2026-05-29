#!/usr/bin/env bash
# Sequential real-API runs requested by Amine (Phase 1, pass 1 additional runs)
set -uo pipefail
cd /root/projects/detection-only-defenses-phase1
source .venv/bin/activate

mkdir -p logs

ts=$(date +%Y%m%d_%H%M%S)
LOG="logs/phase1_pass1_${ts}.log"
echo "[$(date -u +%FT%TZ)] starting phase1 pass1 runs -> $LOG"

run_one() {
  local name="$1"
  local n="$2"
  echo "[$(date -u +%FT%TZ)] BEGIN $name (N=$n)" | tee -a "$LOG"
  python scripts/run_experiment.py --config "configs/${name}.yaml" --limit "$n" >> "$LOG" 2>&1
  local rc=$?
  echo "[$(date -u +%FT%TZ)] END   $name rc=$rc" | tee -a "$LOG"
  return $rc
}

run_one pair_b5_nodefense  20
run_one tap_b5_nodefense   20
run_one pair_b10_nodefense 10

echo "[$(date -u +%FT%TZ)] aggregating" | tee -a "$LOG"
python scripts/aggregate_results.py >> "$LOG" 2>&1
echo "[$(date -u +%FT%TZ)] done" | tee -a "$LOG"
