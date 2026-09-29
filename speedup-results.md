# Speedup Measurement: Julia, Quasi-Monte Carlo, Importance Sampling

**English** · [Deutsch](speedup-results.de.md)

As of 24 September 2026, final measurement. Question: can the classical
baseline be beaten — with a faster language or with a better method? And
which of it survives real data and fat tails?

## Protocol

- S&P 500 top-100 (SPY holdings of 22 Sep 2026, index weights), covariance
  from 1,254 trading days 09/2021–09/2026; normal and Student-t (ν = 4.18)
- CVaR@99%, ε = 10⁻³ (relative RMSE against the closed-form solution)
- Every path a full 100-dimensional draw plus the correlation matmul
- N(ε): plain MC exact from the asymptotic variance; the other methods a
  local power-law fit (20 replications, N = 2⁴ … 2²²) plus a calibration run
  with 100 replications
- Direct timing at the final N, 20 rounds, interleaved
- Apple M3 Max, 14 cores, quiet machine (background programs closed); load
  average per step in `results/benchmark.log`

## Result

| Method | 1 core, normal | 14 cores, normal | 14 cores, t |
|---|---:|---:|---:|
| NumPy, plain MC | 1,818 ms | 268 ms | 1,853 ms |
| Julia, OpenBLAS | 2,485 ms | 1,357 ms (0.2×) | – |
| Julia, Accelerate | 1,347 ms | 173 ms (1.5×) | – |
| Quasi-MC, Cholesky | 162 ms | 30 ms (9×) | 205 ms (9×) |
| Quasi-MC, PCA | 82 ms | 17 ms (16×) | 109 ms (17×) |
| Importance sampling | 11 ms | 4.7 ms (57×) | 1,659 ms (1.1×) |
| IS + quasi-MC | 7.5 ms | 6.0 ms (45×) | 289 ms (6×) |

## Findings

1. **Language: a factor of 1.5, and only with the same BLAS.** Julia with
   OpenBLAS is five times slower than NumPy with Accelerate.
2. **Method: a factor of 9 to 57** with identical work per path.
3. **Importance sampling is not robust.** 57× under the normal distribution,
   1.1× under t: shifting the factors does not capture the mixing variable
   that drives the tail when tails are fat.
4. **Quasi-MC is robust:** 9× and 16–17× under both distributions. Local
   slopes −0.54 to −0.83 — in part classically "quadratic".

## Comparison with the synthetic one-factor model (first version)

The synthetic model was the most favourable case: there IS + quasi-MC
reached a factor of 63, quasi-MC with PCA 18×, with Cholesky only 3.3×. With
real data Cholesky rises to 9×, PCA stays at 16×, and only the t distribution
raises the question of robustness.

## Correction to the first version

N(ε) for plain MC was first determined from a measured error constant (RMSE
at the largest N). With 20 replications the RMSE scatters by ~16%, and N by
~30% as a result. Outcome: N 28% too low; the old headline of 78 ms (M3 Ultra,
synthetic) should have read about 109 ms. Now: exact constant, measurement
only as a check.

## Reproduction

`./shell/run_benchmarks.sh` (see [README](README.md)).
