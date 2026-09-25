#!/usr/bin/env bash
# Complete measurement for articles 1 and 2, in one go.
#
#   ./run_benchmarks.sh            # all cores of this machine
#   ./run_benchmarks.sh 28         # explicit worker count
#   SKIP_VR=1 ./run_benchmarks.sh  # reuse existing results_vr_sp100_*.json
#
# Before starting: close everything else (browsers, Teams, games, Spotlight
# indexing). Every step records the load average in benchmark.log; a load
# above ~1.5 at the start means the numbers will not be publishable.
#
# Needs: .venv with numpy scipy matplotlib pandas (no network), data/
# sp100_model.npz (from fetch_sp100.py, already in the repo). Julia is
# optional; for the Accelerate comparison it installs AppleAccelerate.jl
# once into ./jlenv (network needed on that first run only).

set -euo pipefail
cd "$(dirname "$0")"

WORKERS="${1:-$(sysctl -n hw.ncpu)}"
PY=.venv/bin/python
LOG=benchmark.log
export MC_UNIVERSE=sp100

stamp() { echo "== $* | $(date '+%F %T') | $(uptime | sed 's/.*load/load/')" | tee -a "$LOG"; }

: > "$LOG"
stamp "machine $(sysctl -n machdep.cpu.brand_string), $(sysctl -n hw.ncpu) cores, workers=$WORKERS"

for DIST in normal t; do
  export MC_DIST=$DIST
  SUF=$([ "$DIST" = normal ] && echo "" || echo "_$DIST")

  stamp "$DIST: baseline error curve, 1 core"
  MC_PIN_THREADS=1 $PY mc_baseline.py --reps 20 --max-n 1e7 \
      --out "results_1core$SUF.json" >> "$LOG" 2>&1

  stamp "$DIST: multi-core throughput"
  $PY throughput_probe.py "throughput$SUF.json" >> "$LOG" 2>&1

  if [ -n "${SKIP_VR:-}" ] && [ -f "results_vr_sp100_$DIST.json" ]; then
    stamp "$DIST: variance reduction skipped, reusing results_vr_sp100_$DIST.json"
  else
    stamp "$DIST: variance reduction (curves + timing)"
    MC_PIN_THREADS=1 $PY -W ignore mc_variance_reduction.py --workers "$WORKERS" \
        --out "results_vr_sp100_$DIST.json" >> "$LOG" 2>&1
    $PY -W ignore retime_variance_reduction.py "$WORKERS" 20 \
        "results_vr_sp100_$DIST.json" >> "$LOG" 2>&1
  fi
done

export MC_DIST=normal
if command -v julia >/dev/null; then
  N=$($PY -c "import json;print(json.load(open('results_vr_sp100_normal.json'))['methods']['full']['n_run'])")
  $PY export_model.py >> "$LOG" 2>&1
  if [ ! -f jlenv/Manifest.toml ]; then
    stamp "julia: installing AppleAccelerate.jl into ./jlenv (one-off)"
    julia --project=jlenv -e 'using Pkg; Pkg.add("AppleAccelerate")' >> "$LOG" 2>&1
  fi
  for T in 1 "$WORKERS"; do
    stamp "julia OpenBLAS, $T threads, N=$N"
    JL_OUT="julia_openblas_$T.json" julia -t "$T" mc_baseline.jl "$N" 20 256 >> "$LOG" 2>&1
    stamp "julia Accelerate, $T threads, N=$N"
    JL_OUT="julia_accelerate_$T.json" JL_BLAS=accelerate \
      julia --project=jlenv -t "$T" mc_baseline.jl "$N" 20 256 >> "$LOG" 2>&1
  done
else
  stamp "julia not found -- skipped"
fi

stamp "plots"
for DIST in normal t; do
  MC_DIST=$DIST $PY plot_baseline.py >> "$LOG" 2>&1
  MC_DIST=$DIST $PY plot_variance_reduction.py >> "$LOG" 2>&1
done
stamp "done"
