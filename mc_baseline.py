"""
Classical Monte Carlo baseline for portfolio risk (VaR / CVaR).

This is the reference number that every quantum claim in the series is
measured against. The metric is deliberately NOT sample count -- it is
wall-clock time to reach a target accuracy epsilon.

Design notes
------------
1. Exact reference values.
   Returns are multivariate normal, so portfolio loss L = -w'r is univariate
   normal and E[L], VaR_q and CVaR_q all have closed forms. We therefore
   measure TRUE error against ground truth, not the dispersion of the
   estimator around itself. No scipy needed: statistics.NormalDist supplies
   the inverse CDF.

2. No analytic shortcut in the sampler.
   Because L is a linear functional of r, one could draw a single scalar per
   path instead of a full d-dimensional vector. We do not do that in the
   headline baseline: a real risk engine draws the joint distribution, and
   the comparison target (quantum amplitude estimation) must prepare that
   joint distribution too. The shortcut is measured separately as `reduced`
   so the reader can see what a modelling insight is worth.

3. BLAS thread control.
   NumPy will silently use every core. A "single core" measurement that
   forgets to pin thread counts is the single most common way these
   benchmarks go wrong. Threads are pinned per tier and recorded in the
   output.

Usage
-----
    python mc_baseline.py --quick        # fast smoke run
    python mc_baseline.py                # default grid
    python mc_baseline.py --max-n 1e8    # include the large end
"""

from __future__ import annotations

# Thread pinning must happen before numpy is imported.
import os
import sys

_PIN = os.environ.get("MC_PIN_THREADS")
if _PIN:
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[_v] = _PIN

import argparse
import json
import math
import platform
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------

N_ASSETS = 100          # matches the problem size used in the quantum papers
CONFIDENCE = 0.99       # VaR / CVaR confidence level
HORIZON_DAYS = 1
TRADING_DAYS = 252
CHUNK = 500_000         # paths per generation chunk, bounds peak memory


@dataclass(frozen=True)
class Model:
    """One-period portfolio loss model with a market-factor covariance."""
    mu: np.ndarray        # (d,) expected returns over the horizon
    chol: np.ndarray      # (d, d) lower Cholesky factor of Sigma
    w: np.ndarray         # (d,) portfolio weights, sum to 1
    nu: float | None = None   # Student-t degrees of freedom; None = normal

    @property
    def d(self) -> int:
        return self.mu.shape[0]

    # Loss L = -w'r is normal (or Student-t with the same nu) with location
    # loss_mean and scale loss_sd. For t, chol factors the SCALE matrix, so
    # the covariance is nu/(nu-2) times chol chol'.
    @property
    def loss_mean(self) -> float:
        return float(-self.w @ self.mu)

    @property
    def loss_sd(self) -> float:
        v = self.chol.T @ self.w
        return float(np.sqrt(v @ v))


UNIVERSE = os.environ.get("MC_UNIVERSE", "sp100")   # sp100 | synthetic
DIST = os.environ.get("MC_DIST", "normal")          # normal | t
SP100_FILE = Path(__file__).parent / "data" / "sp100_model.npz"


def build_model(universe: str | None = None, dist: str | None = None) -> Model:
    """The benchmark model. Selected by MC_UNIVERSE / MC_DIST so that every
    script in the repo (and every worker process) sees the same one.

    sp100      the 100 largest S&P 500 companies, covariance and mean from
               five years of daily returns, market-cap weights. Built once by
               fetch_sp100.py; only derived quantities are stored.
    synthetic  the one-factor model of the first version of article 2.
    dist=t     multivariate Student-t with nu fitted to the portfolio's
               historical returns; the covariance is preserved.
    """
    universe = universe or UNIVERSE
    dist = dist or DIST
    if universe == "synthetic":
        if dist != "normal":
            raise ValueError("synthetic model is normal only")
        return build_synthetic_model()
    if universe != "sp100":
        raise ValueError(f"unknown universe {universe!r}")
    if not SP100_FILE.exists():
        raise FileNotFoundError(
            f"{SP100_FILE} missing -- run fetch_sp100.py once (needs network)")
    z = np.load(SP100_FILE)
    cov, nu = z["cov"], None
    if dist == "t":
        nu = float(z["nu"])
        cov = cov * (nu - 2.0) / nu              # scale matrix, same covariance
    elif dist != "normal":
        raise ValueError(f"unknown dist {dist!r}")
    mu = z["mu"] * HORIZON_DAYS
    return Model(mu=mu, chol=np.linalg.cholesky(cov * HORIZON_DAYS),
                 w=z["w"], nu=nu)


def build_synthetic_model(d: int = N_ASSETS, seed: int = 20260922) -> Model:
    """Equity-like covariance: one market factor plus idiosyncratic noise.

    Deterministic given the seed, so the benchmark is hermetic -- no network,
    no data files. Swap in an empirical covariance here to use real returns;
    the timing characteristics are unchanged.
    """
    rng = np.random.default_rng(seed)

    ann_vol = rng.uniform(0.15, 0.45, size=d)          # annualised vols
    beta = rng.uniform(0.6, 1.4, size=d)               # market betas
    market_vol = 0.18
    # Systematic part cannot exceed total variance; rest is idiosyncratic.
    sys_var = (beta * market_vol) ** 2
    idio_var = np.maximum(ann_vol ** 2 - sys_var, (0.05 ** 2))

    sigma_ann = np.outer(beta, beta) * market_vol ** 2 + np.diag(idio_var)
    scale = HORIZON_DAYS / TRADING_DAYS
    sigma = sigma_ann * scale

    mu = rng.uniform(0.02, 0.12, size=d) * scale       # drift over horizon

    chol = np.linalg.cholesky(sigma)

    w = rng.uniform(0.5, 1.5, size=d)
    w /= w.sum()

    return Model(mu=mu, chol=chol, w=w)


def exact_reference(m: Model, q: float = CONFIDENCE) -> dict[str, float]:
    """Closed-form ground truth for the three estimators."""
    mean, sd = m.loss_mean, m.loss_sd
    if m.nu is None:
        nd = statistics.NormalDist()
        z = nd.inv_cdf(q)
        phi = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
        return {"mean": mean, "var": mean + sd * z,
                "cvar": mean + sd * phi / (1.0 - q)}
    # Student-t: CVaR_q = m + s * f(t_q) / (1-q) * (nu + t_q^2) / (nu - 1)
    from scipy.stats import t as student_t
    nu = m.nu
    tq = float(student_t.ppf(q, nu))
    ft = float(student_t.pdf(tq, nu))
    return {"mean": mean, "var": mean + sd * tq,
            "cvar": mean + sd * ft / (1.0 - q) * (nu + tq * tq) / (nu - 1.0)}


# --------------------------------------------------------------------------
# Samplers
# --------------------------------------------------------------------------

def sample_losses_full(m: Model, n: int, seed: int) -> np.ndarray:
    """Draw the full d-dimensional joint distribution, then project.

    This is the honest baseline: it is what a risk engine actually does and
    what QAE's state preparation would have to encode.
    """
    rng = np.random.default_rng(seed)
    out = np.empty(n, dtype=np.float64)
    wmu = float(m.w @ m.mu)
    # Project weights through the Cholesky factor once; the per-path work is
    # still a full d-dimensional draw followed by a d-length dot product.
    done = 0
    while done < n:
        k = min(CHUNK, n - done)
        z = rng.standard_normal((k, m.d))
        r = z @ m.chol.T                      # correlated shocks, (k, d)
        if m.nu is None:
            out[done:done + k] = -(r @ m.w) - wmu
        else:
            # multivariate t: every asset's shock shares one sqrt(nu/W) mix
            # per path. Applied after the projection -- the same arithmetic
            # as scaling each row of r, d times cheaper.
            g = np.sqrt(m.nu / rng.chisquare(m.nu, k))
            out[done:done + k] = -(r @ m.w) * g - wmu
        done += k
    return out


def sample_losses_reduced(m: Model, n: int, seed: int) -> np.ndarray:
    """Exploit the analytic collapse: L is univariate normal.

    Not the headline baseline. Reported to show what a modelling insight is
    worth relative to any hardware change.
    """
    rng = np.random.default_rng(seed)
    if m.nu is None:
        return m.loss_mean + m.loss_sd * rng.standard_normal(n)
    return m.loss_mean + m.loss_sd * rng.standard_t(m.nu, n)


SAMPLERS = {"full": sample_losses_full, "reduced": sample_losses_reduced}


def estimate(losses: np.ndarray, q: float = CONFIDENCE) -> dict[str, float]:
    """Mean loss, VaR_q and CVaR_q from a loss sample."""
    mean = float(losses.mean())
    var = float(np.quantile(losses, q))
    tail = losses[losses >= var]
    cvar = float(tail.mean()) if tail.size else var
    return {"mean": mean, "var": var, "cvar": cvar}


# --------------------------------------------------------------------------
# Timing harness
# --------------------------------------------------------------------------

def _one_replication(args):
    """Run a single replication. Top-level so it is picklable."""
    sampler_name, n, seed, mu, chol, w, nu = args
    m = Model(mu=mu, chol=chol, w=w, nu=nu)
    t0 = time.perf_counter()
    losses = SAMPLERS[sampler_name](m, n, seed)
    est = estimate(losses)
    return time.perf_counter() - t0, est


def run_cell(m: Model, sampler_name: str, n: int, reps: int,
             workers: int, base_seed: int) -> dict:
    """Measure one (sampler, n) cell: wall-clock and true error.

    `workers` > 1 splits each replication's paths across processes, which is
    how a risk desk would actually run it.
    """
    truth = exact_reference(m)
    m_sd = m.loss_sd
    times, ests = [], []

    for r in range(reps):
        seed = base_seed + 1000 * r
        if workers == 1:
            dt, est = _one_replication(
                (sampler_name, n, seed, m.mu, m.chol, m.w, m.nu))
        else:
            per = [n // workers] * workers
            for i in range(n - sum(per)):
                per[i] += 1
            jobs = [(sampler_name, per[i], seed + i, m.mu, m.chol, m.w, m.nu)
                    for i in range(workers)]
            t0 = time.perf_counter()
            with ProcessPoolExecutor(max_workers=workers) as ex:
                parts = list(ex.map(_one_replication, jobs))
            dt = time.perf_counter() - t0
            # NOTE: shard estimates are NOT combined into an error
            # figure. The mean of shard quantiles is not the quantile of the
            # union, so averaging would bias VaR/CVaR. Multi-worker cells are
            # used for THROUGHPUT only; the error law is taken from the
            # single-process runs, where the estimator is exact. Error is a
            # function of N alone, so the two compose correctly.
            est = {k: float("nan") for k in ("mean", "var", "cvar")}
        times.append(dt)
        ests.append(est)

    result = {
        "sampler": sampler_name,
        "n": n,
        "reps": reps,
        "workers": workers,
        "time_median_s": statistics.median(times),
        "time_min_s": min(times),
        "time_max_s": max(times),
        "paths_per_s": n / statistics.median(times),
    }
    # True RMSE against the closed-form reference, per estimator.
    # Skipped for multi-worker cells (see note above): throughput only.
    if workers > 1:
        for key in ("mean", "var", "cvar"):
            result[f"rmse_{key}"] = float("nan")
            result[f"relerr_{key}"] = float("nan")
        return result
    for key in ("mean", "var", "cvar"):
        errs = np.array([e[key] - truth[key] for e in ests])
        rmse = float(np.sqrt(np.mean(errs ** 2)))
        result[f"rmse_{key}"] = rmse
        # The mean loss sits near zero, so dividing by it is unstable. Scale
        # that one by the loss SD; VaR/CVaR are far from zero and scale by
        # their own magnitude.
        denom = m_sd if key == "mean" else abs(truth[key])
        result[f"relerr_{key}"] = rmse / denom
    return result


def fit_sqrt_law(cells: list[dict], key: str) -> dict:
    """Fit log(relerr) = a + b*log(n). The 1/sqrt(N) law predicts b = -0.5."""
    pts = [(c["n"], c[f"relerr_{key}"]) for c in cells if c[f"relerr_{key}"] > 0]
    if len(pts) < 2:
        return {"slope": float("nan"), "intercept": float("nan")}
    x = np.log(np.array([p[0] for p in pts], dtype=float))
    y = np.log(np.array([p[1] for p in pts], dtype=float))
    b, a = np.polyfit(x, y, 1)
    return {"slope": float(b), "intercept": float(a)}


def cvar_error_constant(m: Model, q: float = CONFIDENCE) -> float:
    """Exact C in relerr(CVaR) = C / sqrt(N) for plain Monte Carlo.

    The empirical CVaR estimator is asymptotically normal with
        N * Var -> Var[(L - VaR_q)^+] / (1 - q)^2
    (Rockafellar-Uryasev form; Hong & Liu, Management Science 55(2), 2009;
    review: Hong, Hu & Liu, ACM TOMACS 24(4), 2014).
    L is univariate normal or t here, so the tail moments are one-dimensional
    integrals. This replaces calibrating C at one measured point: with 20
    replications a measured RMSE carries ~16% noise, which enters N squared.
    The first version of this benchmark did exactly that and put N 28% low.
    """
    from scipy import integrate, stats
    dist = stats.norm() if m.nu is None else stats.t(m.nu)
    zq = float(dist.ppf(q))
    m1 = integrate.quad(lambda x: (x - zq) * dist.pdf(x), zq, math.inf)[0]
    m2 = integrate.quad(lambda x: (x - zq) ** 2 * dist.pdf(x), zq, math.inf)[0]
    sd_std = math.sqrt(m2 - m1 * m1) / (1.0 - q)
    return m.loss_sd * sd_std / exact_reference(m, q)["cvar"]


def time_to_epsilon(cells: list[dict], key: str, eps: float,
                    throughput: float, C_exact: float | None = None) -> dict:
    """Wall-clock seconds to reach relative accuracy `eps`.

    The fitted slope is used to VALIDATE the 1/sqrt(N) law, not to
    extrapolate with. Extrapolation uses the theoretical exponent -0.5 with
    the constant calibrated at the largest measured N, which is both more
    honest and more accurate than riding a noisy fit out over decades.

    err(N) = C / sqrt(N),  C = err(N_max) * sqrt(N_max)
       =>   N(eps) = (C / eps)**2
    """
    usable = [c for c in cells if c[f"relerr_{key}"] > 0]
    if not usable:
        return {"seconds": float("nan"), "n_required": float("nan"),
                "extrapolated": True}
    anchor = max(usable, key=lambda c: c["n"])
    C_anchor = anchor[f"relerr_{key}"] * math.sqrt(anchor["n"])
    C = C_exact if C_exact is not None else C_anchor
    n_req = (C / eps) ** 2
    return {
        "seconds": n_req / throughput,
        "n_required": n_req,
        "C_used": C,
        "C_source": "exact" if C_exact is not None else "anchor",
        "C_anchor": C_anchor,
        "anchor_n": anchor["n"],
        "extrapolated": n_req > anchor["n"],
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def env_info() -> dict:
    import numpy
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": sys.version.split()[0],
        "numpy": numpy.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "blas_threads_pinned": os.environ.get("MC_PIN_THREADS", "unset"),
        "universe": UNIVERSE,
        "dist": DIST,
        "n_assets": N_ASSETS,
        "confidence": CONFIDENCE,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--quick", action="store_true", help="short smoke run")
    p.add_argument("--max-n", type=float, default=1e7)
    p.add_argument("--reps", type=int, default=10)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--sampler", choices=["full", "reduced", "both"],
                   default="both")
    p.add_argument("--out", default="results.json")
    args = p.parse_args()

    grid = [10**3, 10**4, 10**5, 10**6]
    if args.quick:
        reps = 5
    else:
        reps = args.reps
        n = 10**7
        while n <= args.max_n + 1:
            grid.append(int(n))
            n *= 10

    model = build_model()
    truth = exact_reference(model)

    print(f"Portfolio: {model.d} assets, {CONFIDENCE:.0%} confidence, "
          f"{HORIZON_DAYS}d horizon")
    print(f"Exact reference   mean={truth['mean']:+.8f}  "
          f"VaR={truth['var']:+.8f}  CVaR={truth['cvar']:+.8f}")
    print(f"Workers={args.workers}  reps={reps}  "
          f"BLAS pin={os.environ.get('MC_PIN_THREADS', 'unset')}\n")

    samplers = ["full", "reduced"] if args.sampler == "both" else [args.sampler]

    # Warm-up: first NumPy call pays allocator and page-fault costs.
    sample_losses_full(model, 50_000, seed=1)

    results: dict[str, list[dict]] = {}
    for s in samplers:
        print(f"--- sampler: {s} ---")
        print(f"{'N':>12} {'time_med(s)':>12} {'paths/s':>14} "
              f"{'relerr_mean':>12} {'relerr_VaR':>12} {'relerr_CVaR':>12}")
        cells = []
        for n in grid:
            c = run_cell(model, s, n, reps, args.workers, base_seed=7)
            cells.append(c)
            print(f"{n:>12,} {c['time_median_s']:>12.4f} "
                  f"{c['paths_per_s']:>14,.0f} "
                  f"{c['relerr_mean']:>12.2e} {c['relerr_var']:>12.2e} "
                  f"{c['relerr_cvar']:>12.2e}")
        results[s] = cells
        print()

    C_exact = cvar_error_constant(model)
    summary = {"env": env_info(), "truth": truth, "results": results,
               "cvar_error_constant_exact": C_exact, "fits": {}}
    for s, cells in results.items():
        summary["fits"][s] = {}
        for key in ("mean", "var", "cvar"):
            fit = fit_sqrt_law(cells, key)
            tput = max(c["paths_per_s"] for c in cells)
            entry = {"slope_fitted": fit["slope"], "throughput_paths_s": tput}
            for eps in (1e-2, 1e-3, 1e-4, 1e-6):
                entry[f"eps_{eps:g}"] = time_to_epsilon(
                    cells, key, eps, tput,
                    C_exact if key == "cvar" else None)
            summary["fits"][s][key] = entry

    with open(args.out, "w") as fh:
        json.dump(summary, fh, indent=2)

    print("=" * 74)
    print("ERROR LAW  (1/sqrt(N) predicts slope = -0.500)")
    for s in results:
        for key in ("mean", "var", "cvar"):
            print(f"  {s:>8} / {key:<5} slope = "
                  f"{summary['fits'][s][key]['slope_fitted']:+.4f}")
    print()
    Cm = [round(c["relerr_cvar"] * math.sqrt(c["n"]), 3)
          for c in results.get("full", [])]
    print(f"CVaR ERROR CONSTANT  exact C = {C_exact:.4f}   measured C*sqrt(N) "
          f"per grid point: {Cm}\n")
    print("WALL-CLOCK TIME TO TARGET ACCURACY  (sampler=full, CVaR@99%, exact C)")
    if "full" in summary["fits"]:
        for eps in (1e-2, 1e-3, 1e-4, 1e-6):
            e = summary["fits"]["full"]["cvar"][f"eps_{eps:g}"]
            tag = "extrapolated" if e["extrapolated"] else "measured range"
            print(f"  eps = {eps:<8g}  N = {e['n_required']:>18,.0f}   "
                  f"t = {e['seconds']:>12.3f} s   ({tag})")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
