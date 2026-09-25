"""
Better classical opponents: quasi-Monte Carlo and importance sampling.

Question 3 of the series asks for the best classical opponent, not the most
convenient one. `mc_baseline.py` measures plain Monte Carlo. This script
measures two textbook upgrades that keep the rule of article 2 intact: every
path is still a full 100-dimensional joint draw followed by the same
correlation matmul. No analytic collapse to one scalar per path.

Methods
-------
full        plain MC, identical to mc_baseline.sample_losses_full
qmc_chol    scrambled Sobol points, inverse-normal transform, Cholesky factor
qmc_pca     same, but the factor is the eigendecomposition ordered by
            variance -- the standard QMC trick (Glasserman, ch. 5), so the
            leading Sobol coordinates carry the most variance
is          importance sampling: z ~ N(theta, I), theta along the loss
            gradient, likelihood-ratio weights
is_qmc_pca  both combined

Metric
------
Unchanged from article 2: relative RMSE of CVaR@99% against the closed-form
truth, over independent replications (fresh seed / fresh scramble each).
Then: the N needed for eps = 1e-3 is read off the measured error curve, and
a run at that N is timed directly -- no extrapolation.

Caveat that belongs in any write-up
-----------------------------------
The test portfolio is linear and Gaussian. That is the friendliest possible
case for both techniques: the IS shift direction is exact, and the loss has
low effective dimension for QMC. For a book with options the gain shrinks.
The numbers here are an upper bound on what the techniques deliver.

Usage
-----
    python mc_variance_reduction.py --quick
    python mc_variance_reduction.py                 # full grid, ~10 min
    python mc_variance_reduction.py --workers 14    # + multi-core timing
"""

from __future__ import annotations

import os

_PIN = os.environ.get("MC_PIN_THREADS")
if _PIN:
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[_v] = _PIN

import argparse
import json
import math
import statistics
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.special import ndtri
from scipy.stats import chi2, qmc

from mc_baseline import (CONFIDENCE, Model, build_model, cvar_error_constant,
                         env_info, exact_reference)

CHUNK = 1 << 16          # paths per block; power of two keeps Sobol balanced
Q = CONFIDENCE


# --------------------------------------------------------------------------
# Factor matrices and IS shift
# --------------------------------------------------------------------------

def pca_factor(m: Model) -> np.ndarray:
    """A with A A' = Sigma, columns ordered by decreasing variance."""
    sigma = m.chol @ m.chol.T
    vals, vecs = np.linalg.eigh(sigma)
    order = np.argsort(vals)[::-1]
    return vecs[:, order] * np.sqrt(vals[order])


def is_shift(A: np.ndarray, w: np.ndarray, q: float = Q) -> np.ndarray:
    """Mean shift for z along the loss gradient.

    Loss is L = -w'(mu + A z), so the gradient w.r.t. z is -A'w. Shifting to
    the CVaR level, about phi(z_q)/(1-q) standard deviations out, centres the
    sampling distribution on the tail. For a non-linear book this direction
    would come from a delta(-gamma) approximation instead of being exact.
    """
    g = -(A.T @ w)
    zq = statistics.NormalDist().inv_cdf(q)
    c = math.exp(-0.5 * zq * zq) / math.sqrt(2 * math.pi) / (1 - q)
    return c * g / np.linalg.norm(g)


# --------------------------------------------------------------------------
# Samplers: return (losses, weights) for points [start, start + n)
# --------------------------------------------------------------------------

def _normals_mc(rng, k, d):
    return rng.standard_normal((k, d))


def _normals_sobol(eng, k, d):
    u = eng.random(k)
    # Scrambled Sobol never hits 0 or 1 exactly, but guard anyway.
    np.clip(u, 1e-16, 1 - 1e-16, out=u)
    return u


def _t_mix_mc(rng, k, nu):
    """sqrt(nu / W), W ~ chi2(nu): the per-path scale of a multivariate t."""
    return np.sqrt(nu / rng.chisquare(nu, k))


def sample(method: str, m: Model, n: int, seed: int,
           start: int = 0, factors: dict | None = None):
    """Draw n loss paths. `start` offsets into the Sobol sequence so that
    workers sharing a seed together produce exactly one n-point set."""
    f = factors or make_factors(m)
    qmc_based = method.startswith("qmc") or method == "is_qmc_pca"
    A = f["chol"] if method in ("full", "qmc_chol", "is") else f["pca"]
    theta = f["theta_chol"] if method == "is" else f["theta_pca"]
    use_is = method.startswith("is")

    d = m.d
    wmu = float(m.w @ m.mu)
    losses = np.empty(n)
    weights = np.empty(n) if use_is else None

    nu = m.nu
    if qmc_based:
        # For t, the mixing variable W gets Sobol coordinate 0: it drives the
        # tail more than any single factor, and QMC favours leading dims.
        eng = qmc.Sobol(d + (nu is not None), scramble=True, seed=seed)
        if start:
            eng.fast_forward(start)
    else:
        rng = np.random.default_rng(seed)

    done = 0
    while done < n:
        k = min(CHUNK, n - done)
        g = None
        if qmc_based:
            u = _normals_sobol(eng, k, d)
            if nu is not None:
                g = np.sqrt(nu / chi2.ppf(u[:, 0], nu))
                u = u[:, 1:]
            z = ndtri(u)
        else:
            z = _normals_mc(rng, k, d)
            if nu is not None:
                g = _t_mix_mc(rng, k, nu)
        if use_is:
            # Shift z only; W keeps its distribution, so the likelihood
            # ratio is unchanged. For t this is deliberately not optimal:
            # part of the tail comes from small W, which the shift ignores.
            z += theta
            # likelihood ratio N(0,I)/N(theta,I) = exp(-theta'z + |theta|^2/2)
            weights[done:done + k] = np.exp(-(z @ theta) + 0.5 * theta @ theta)
        r = z @ A.T                               # full correlation matmul
        proj = r @ m.w
        losses[done:done + k] = -(proj if g is None else proj * g) - wmu
        done += k
    return losses, weights


def make_factors(m: Model) -> dict:
    pca = pca_factor(m)
    return {"chol": m.chol, "pca": pca,
            "theta_chol": is_shift(m.chol, m.w),
            "theta_pca": is_shift(pca, m.w)}


METHODS = ["full", "qmc_chol", "qmc_pca", "is", "is_qmc_pca"]


# --------------------------------------------------------------------------
# Estimator (weighted Rockafellar-Uryasev form)
# --------------------------------------------------------------------------

def estimate_cvar(losses: np.ndarray, weights: np.ndarray | None,
                  q: float = Q) -> float:
    """CVaR_q. Unweighted: identical to mc_baseline.estimate.

    Weighted: VaR is the smallest x with (1/n) sum w_i 1{L_i > x} <= 1-q,
    CVaR = VaR + sum w_i (L_i - VaR)+ / (n (1-q)).
    """
    if weights is None:
        var = float(np.quantile(losses, q))
        return float(losses[losses >= var].mean())
    n = losses.size
    order = np.argsort(losses)[::-1]          # descending
    Ls, ws = losses[order], weights[order]
    tail_mass = np.cumsum(ws) / n
    i = int(np.searchsorted(tail_mass, 1 - q))
    var = float(Ls[min(i, n - 1)])
    excess = np.maximum(Ls - var, 0.0)
    return var + float((ws * excess).sum()) / (n * (1 - q))


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------

def _worker(args):
    method, n, seed, start, mu, chol, w, nu = args
    m = Model(mu=mu, chol=chol, w=w, nu=nu)
    return sample(method, m, n, seed, start=start)


def timed_run(method: str, m: Model, n: int, seed: int, workers: int,
              pool: ProcessPoolExecutor | None) -> tuple[float, float]:
    """Wall-clock for one complete estimate at n paths: draw + estimate.

    Multi-worker: one shared seed, contiguous Sobol blocks per worker, results
    gathered and estimated once in the parent. Unlike mc_baseline this does
    combine shards, so the multi-core number is a real estimate, not just
    throughput. Plain MC shards use seed + i, as in the baseline.
    """
    t0 = time.perf_counter()
    if workers == 1:
        L, W = sample(method, m, n, seed)
    else:
        per = [n // workers] * workers
        for i in range(n - sum(per)):
            per[i] += 1
        starts = np.cumsum([0] + per[:-1]).tolist()
        qmc_based = "qmc" in method
        jobs = [(method, per[i], seed if qmc_based else seed + i,
                 starts[i] if qmc_based else 0, m.mu, m.chol, m.w, m.nu)
                for i in range(workers)]
        parts = list(pool.map(_worker, jobs))
        L = np.concatenate([p[0] for p in parts])
        W = None if parts[0][1] is None else np.concatenate(
            [p[1] for p in parts])
    est = estimate_cvar(L, W)
    return time.perf_counter() - t0, est


def error_curve(method, m, grid, reps, truth, factors):
    rows = []
    for n in grid:
        errs, times = [], []
        for r in range(reps):
            t0 = time.perf_counter()
            L, W = sample(method, m, n, seed=7 + 1000 * r, factors=factors)
            est = estimate_cvar(L, W)
            times.append(time.perf_counter() - t0)
            errs.append(est - truth)
        rel = math.sqrt(float(np.mean(np.square(errs)))) / abs(truth)
        rows.append({"n": n, "relerr_cvar": rel,
                     "time_median_s": statistics.median(times)})
        print(f"  {method:>11}  N={n:>10,}  relerr={rel:.3e}  "
              f"t={statistics.median(times):.4f}s", flush=True)
    return rows


def n_for_eps(rows, eps):
    """N at which the measured curve reaches eps.

    A least-squares power law log(err) = a + b log(N) is fitted to the five
    grid points around the crossing and solved for eps. Interpolating between
    just the two bracketing points was tried first and rejected: with 20
    replications each point carries ~15% noise, and for plain MC that put N
    18% too low (1.73M vs. 2.04M; the 1/sqrt(N) law gives 2.05M).
    Returns (N, extrapolated)."""
    lx = [math.log(r["n"]) for r in rows]
    ly = [math.log(r["relerr_cvar"]) for r in rows]
    if ly[0] <= math.log(eps):               # already there at the smallest N
        return rows[0]["n"], False, -0.5
    i = min(range(len(rows)), key=lambda j: abs(ly[j] - math.log(eps)))
    lo, hi = max(0, i - 2), min(len(rows), i + 3)
    b, a = np.polyfit(lx[lo:hi], ly[lo:hi], 1)
    n_req = math.exp((math.log(eps) - a) / b)
    return n_req, n_req > rows[-1]["n"], float(b)


def calibrate(method, m, n, reps, truth, factors):
    """Relative RMSE at one N from `reps` fresh replications. With 100
    replications the RMSE itself is good to ~7%, against ~16% at 20."""
    errs = []
    for r in range(reps):
        L, W = sample(method, m, n, seed=500_000 + 1000 * r, factors=factors)
        errs.append(estimate_cvar(L, W) - truth)
    return math.sqrt(float(np.mean(np.square(errs)))) / abs(truth)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--reps", type=int, default=20)
    p.add_argument("--max-log2", type=int, default=22)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--eps", type=float, default=1e-3)
    p.add_argument("--timing-reps", type=int, default=7)
    p.add_argument("--calib-reps", type=int, default=100)
    p.add_argument("--methods", default=",".join(METHODS))
    p.add_argument("--out", default="results_variance_reduction.json")
    a = p.parse_args()

    reps = 5 if a.quick else a.reps
    top = 18 if a.quick else a.max_log2
    grid = [1 << k for k in range(4, top + 1)]
    methods = a.methods.split(",")

    m = build_model()
    truth = exact_reference(m)["cvar"]
    C_exact = cvar_error_constant(m)
    factors = make_factors(m)
    sample("qmc_pca", m, 4096, seed=1, factors=factors)   # warm-up

    print(f"CVaR@{Q:.0%} truth = {truth:.8f}   reps={reps}   "
          f"pin={os.environ.get('MC_PIN_THREADS', 'unset')}\n")

    out = {"env": env_info(), "truth_cvar": truth, "eps": a.eps,
           "chunk": CHUNK, "methods": {}}
    pool = (ProcessPoolExecutor(max_workers=a.workers)
            if a.workers > 1 else None)
    if pool:  # spawn the workers before any clock starts
        list(pool.map(_worker, [("full", 1024, 1, 0, m.mu, m.chol, m.w, m.nu)]
                      * a.workers))

    for method in methods:
        rows = error_curve(method, m, grid, reps, truth, factors)
        lx = np.log([r["n"] for r in rows])
        ly = np.log([r["relerr_cvar"] for r in rows])
        slope = float(np.polyfit(lx, ly, 1)[0])
        pow2 = "qmc" in method           # Sobol wants a power of two
        calib = None
        if method == "full":
            # Plain MC has an exact error constant -- no fit, no noise.
            n_fit, extrap, b = n_for_eps(rows, a.eps)
            n_req, src = (C_exact / a.eps) ** 2, "exact"
        else:
            # No closed form: fit, then one calibration run with many
            # replications at the fitted N, then correct along the slope.
            n_fit, extrap, b = n_for_eps(rows, a.eps)
            n_c = int(math.ceil(n_fit))
            if pow2:
                n_c = 1 << math.ceil(math.log2(n_c))
            e_c = calibrate(method, m, n_c, a.calib_reps, truth, factors)
            # A noisy local slope would make the correction explode; keep it
            # inside the physically sensible range between 1/sqrt(N) and 1/N.
            b = min(max(b, -1.0), -0.4)
            n_req = n_c * (a.eps / e_c) ** (1.0 / b)
            src = "fit+calibration"
            calib = {"n": n_c, "reps": a.calib_reps, "relerr": e_c,
                     "local_slope": b}
            print(f"  calibration: N={n_c:,} x{a.calib_reps}: relerr "
                  f"{e_c:.3e} -> N(eps)={n_req:,.0f}", flush=True)
        n_run = int(math.ceil(n_req))
        if pow2:
            n_run = 1 << math.ceil(math.log2(n_run))

        timing = {}
        for wk in sorted({1, a.workers}):
            ts, errs = [], []
            for r in range(a.timing_reps):
                dt, est = timed_run(method, m, n_run, 99 + 1000 * r, wk, pool)
                ts.append(dt)
                errs.append(est - truth)
            timing[str(wk)] = {
                "time_median_s": statistics.median(ts),
                "time_min_s": min(ts),
                "relerr_check": math.sqrt(float(np.mean(np.square(errs))))
                / abs(truth),
            }
        out["methods"][method] = {"curve": rows, "slope": slope,
                                  "n_required": n_req,
                                  "n_required_source": src,
                                  "n_fit": n_fit, "calibration": calib,
                                  "n_required_extrapolated": extrap,
                                  "n_run": n_run, "timing": timing}
        tstr = "  ".join(f"{k} core(s): {v['time_median_s']*1e3:8.1f} ms "
                         f"(check err {v['relerr_check']:.2e})"
                         for k, v in timing.items())
        print(f"  -> slope {slope:+.3f}  N(eps)={n_req:,.0f}"
              f"{' (extrap.)' if extrap else ''}  run N={n_run:,}  {tstr}\n",
              flush=True)

    if pool:
        pool.shutdown()
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
