"""Asymptotic throughput probe: persistent worker pool, large N.

A real risk engine keeps its workers warm. Measuring process spawn on every
replication understates multicore throughput, so the pool is created once
and reused. Reports the scaling curve across worker counts.
"""
import os, time, statistics
for v in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS",
          "VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[v] = "1"
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from mc_baseline import build_model, sample_losses_full

MODEL = build_model()
MU = MODEL.mu

def shard(args):
    n, seed = args
    # same sampler as the error measurement, so normal and t both work
    return sample_losses_full(MODEL, n, seed).mean()   # a scalar, not 800MB

def measure(pool, workers, n, reps=3):
    per = [n // workers] * workers
    ts = []
    for r in range(reps):
        jobs = [(per[i], 991 + 7*i + 100*r) for i in range(workers)]
        t0 = time.perf_counter()
        list(pool.map(shard, jobs))
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)

def cpu_brand():
    import subprocess
    try:
        return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                              capture_output=True, text=True).stdout.strip()
    except OSError:
        import platform
        return platform.processor()


if __name__ == "__main__":
    import json, sys
    from mc_baseline import UNIVERSE, DIST
    out = sys.argv[1] if len(sys.argv) > 1 else "throughput.json"
    N = 20_000_000
    ncpu = os.cpu_count()
    grid = sorted({w for w in (1, 2, 4, 8, 14, 20, 28) if w <= ncpu} | {ncpu})
    print(f"N = {N:,} paths, {MU.shape[0]} assets, persistent pool, "
          f"BLAS pinned to 1, {UNIVERSE}/{DIST}\n")
    print(f"{'workers':>8} {'time_med(s)':>12} {'paths/s':>16} {'speedup':>9} {'eff':>7}")
    base, rows = None, []
    for w in grid:
        with ProcessPoolExecutor(max_workers=w) as pool:
            list(pool.map(shard, [(1000, 1)] * w))      # warm the pool
            t = measure(pool, w, N)
        tp = N / t
        if base is None:
            base = tp
        rows.append({"workers": w, "time_median_s": t, "paths_per_s": tp})
        print(f"{w:>8} {t:>12.3f} {tp:>16,.0f} {tp/base:>8.1f}x {tp/base/w:>6.0%}")
    json.dump({"cpu": cpu_brand(), "cpu_count": ncpu, "universe": UNIVERSE,
               "dist": DIST, "n": N, "rows": rows}, open(out, "w"), indent=2)
    print(f"\nwrote {out}")
