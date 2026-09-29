"""Re-time every method at its required N from results_variance_reduction.json
without redoing the error curves. Use when the timing pass of the main run
was disturbed by background load: the error curves do not depend on load,
the timings do. Rounds are interleaved across methods, so any remaining
drift hits all methods alike."""

import os

os.environ.setdefault("MC_PIN_THREADS", "1")
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = os.environ["MC_PIN_THREADS"]

import json
import math
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import mc_variance_reduction as v
from mc_baseline import build_model, exact_reference


def retime_curves(rounds: int = 7):
    """Re-time every grid point of every error curve on one core, rounds
    interleaved across methods and N. Errors are kept: they depend on the
    seeds, not on machine load."""
    path = sys.argv[3] if len(sys.argv) > 3 else "results_variance_reduction.json"
    res = json.load(open(path))
    m = build_model()
    f = v.make_factors(m)
    import time
    samples = {}
    for r in range(rounds):
        for me, d in res["methods"].items():
            for c in d["curve"]:
                t0 = time.perf_counter()
                L, W = v.sample(me, m, c["n"], seed=7 + 1000 * r, factors=f)
                v.estimate_cvar(L, W)
                samples.setdefault((me, c["n"]), []).append(
                    time.perf_counter() - t0)
    for me, d in res["methods"].items():
        for c in d["curve"]:
            c["time_median_s"] = statistics.median(samples[(me, c["n"])])
    res["curve_timing_rounds"] = rounds
    res["curve_loadavg_after"] = os.getloadavg()
    json.dump(res, open(path, "w"), indent=2)
    print("curve times updated, load", os.getloadavg())


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--curves":
        return retime_curves(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    path = sys.argv[3] if len(sys.argv) > 3 else "results_variance_reduction.json"
    res = json.load(open(path))
    m = build_model()
    truth = exact_reference(m)["cvar"]
    pool = ProcessPoolExecutor(max_workers=workers)
    list(pool.map(v._worker, [("full", 1024, 1, 0, m.mu, m.chol, m.w, m.nu)] * workers))

    methods = list(res["methods"])
    data = {(me, wk): ([], []) for me in methods for wk in (1, workers)}
    for r in range(rounds):
        for me in methods:
            n = res["methods"][me]["n_run"]
            for wk in (1, workers):
                dt, est = v.timed_run(me, m, n, 99 + 1000 * r, wk, pool)
                data[(me, wk)][0].append(dt)
                data[(me, wk)][1].append(est - truth)
    pool.shutdown()

    for me in methods:
        timing = {}
        for wk in (1, workers):
            ts, errs = data[(me, wk)]
            timing[str(wk)] = {
                "time_median_s": statistics.median(ts),
                "time_min_s": min(ts),
                "relerr_check": math.sqrt(float(np.mean(np.square(errs))))
                / abs(truth),
            }
        res["methods"][me]["timing"] = timing
        print(f"{me:>11}  N={res['methods'][me]['n_run']:>9,}  " + "  ".join(
            f"{k}c {t['time_median_s']*1e3:8.1f} ms (err {t['relerr_check']:.1e})"
            for k, t in timing.items()))
    res["timing_rounds"] = rounds
    res["loadavg_after"] = os.getloadavg()
    json.dump(res, open(path, "w"), indent=2)


if __name__ == "__main__":
    main()
