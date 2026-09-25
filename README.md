# Quantum Portfolio Risk on AWS Braket — Code and Data

**English** · [Deutsch](README.de.md)

Code and measured data behind a Medium series that compares classical Monte
Carlo and quantum amplitude estimation for portfolio risk on AWS Braket. The
series measures one thing throughout: **wall-clock time to a target accuracy
ε** — not sample counts, not oracle calls.

The articles and their figures are published on Medium. This repository holds
everything needed to reproduce the numbers; the `plot_*.py` scripts regenerate
every figure from the data here.

## The series

| # | Title | What it measures |
|---|---|---|
| 1 | The Clock Nobody Started | Why sample counts say nothing about speed; seven questions for any benchmark |
| 2 | 268 Milliseconds | The classical baseline: CVaR of the S&P 500 top-100 by plain Monte Carlo |
| 2b | 4.7 Milliseconds | Beating the baseline: Julia, quasi-Monte Carlo, importance sampling, fat tails |
| 3 | A Factor of 188 | Braket setup, device availability, control-plane latency, spending limits |
| 4 | The Quantum Computer Is the Fastest Part | Where the time of a quantum loop goes |
| 5 | 412,800 Oracle Calls | Quantum amplitude estimation from standard gates: speedup, constant, cost |
| 6 | 106 CNOTs | The smallest QAE circuit on IQM, Rigetti and IonQ hardware |

## Key results

Portfolio: the 100 largest S&P 500 companies (SPDR holdings of 22 September
2026, index weights), covariance from five years of daily returns. CVaR at
99%, one-day horizon, ε = 10⁻³. Classical measurements on an Apple M3 Max,
14 cores, Python 3.14.7, NumPy 2.5.3 on Accelerate, Julia 1.12.6.

**Classical (articles 2 and 2b)**

| | Normal returns | Student-t (ν = 4.2) |
|---|---:|---:|
| Plain Monte Carlo, 14 cores, end to end | **268 ms** | 1,853 ms |
| Best method, 14 cores | **4.7 ms** (importance sampling) | **109 ms** (quasi-MC, PCA order) |

| Method | N | 1 core, normal | 14 cores, normal | 14 cores, t |
|---|---:|---:|---:|---:|
| NumPy, plain MC | 3,102,840 | 1,818 ms | 268 ms | 1,853 ms |
| Julia, OpenBLAS (default) | 3,102,840 | 2,485 ms | 1,357 ms | – |
| Julia, Accelerate | 3,102,840 | 1,347 ms | 173 ms | – |
| Quasi-MC, Cholesky | 131,072 | 162 ms | 30 ms | 205 ms |
| Quasi-MC, PCA | 65,536 | 82 ms | 17 ms | 109 ms |
| Importance sampling | 16,419 | 11 ms | 4.7 ms | 1,659 ms |
| IS + quasi-MC (PCA) | 4,096 | 7.5 ms | 6.0 ms | 289 ms |

N is for the normal case; under the t distribution plain MC needs 21.6 million
paths.

**Cloud latency (articles 3 and 4)**

- Local Braket simulator, 20 qubits, 1,000 shots: 17 ms.
- One iteration of a variational loop on IQM Garnet: 3.3 s, of which the
  computation is under 2.4 ms (0.07%). SDK polling alone costs about 750 ms
  per iteration; one parameter removes it.

**Quantum amplitude estimation (article 5, noiseless simulator)**

- The quadratic speedup is real: error falls with slope −1.00, against −0.50
  for sampling.
- For a 1% tail probability to ε = 10⁻³: **412,800 oracle calls**, not 1,000.
  The deepest circuit has 597,594 two-qubit gates.

**Real hardware (article 6)** — 3 qubits, tail probability 6.6%, P(flag = 1)
after k Grover steps:

| | k = 0 | k = 1 | k = 2 |
|---|---:|---:|---:|
| ideal | 6.6% | 49.2% | 92.6% |
| IonQ Forte Enterprise 1 | 9.5% | 48.0% | **74.0%** |
| IQM Garnet | 12.3% | 40.1% | 53.9% |
| IQM Emerald | 11.6% | 44.2% | 46.0% |
| Rigetti Cepheus-1 | 19.3% | 50.2% | 49.9% |

Full noise converges to 50%. Total cost $62.03; the IonQ tasks spent 12.4 to
12.8 hours in the queue.

## Method

All decisions are commented in the code.

1. **Exact reference.** Under normal and t returns the portfolio loss is
   univariate normal or t, so VaR and CVaR have closed forms. The error
   measured is the true error (RMSE over 20 replications).
2. **No shortcut in the sampler.** Every path is a full 100-dimensional draw
   with the correlation matmul, because QAE's state preparation has to load
   the same joint distribution. The shortcut is measured separately as
   `reduced`.
3. **BLAS threads pinned** (`MC_PIN_THREADS=1`) and logged.
4. **Exact error constant.** N(ε) for plain Monte Carlo comes from the
   asymptotic variance of the CVaR estimator
   (`mc_baseline.cvar_error_constant`: C = 1.76 normal, 4.65 t), not from a
   fit. For quasi-MC and importance sampling: fit, then a calibration run of
   100 replications near the fitted N, corrected along the local slope.
5. **Direct timing** at the final N, 20 rounds, the Python methods
   interleaved; Julia separately, 20 repetitions each.
6. **Predictions before hardware runs.** `hw_qae.py preview` simulates the
   circuits with the error rates the providers report, before anything is
   submitted.

**Limits.** The portfolio is linear; for a book with options the gains from
importance sampling and quasi-MC shrink further. Selecting today's largest
companies is a survivorship bias (harmless for a compute-time benchmark).
One machine, one day; the load average per step is in `benchmark.log`.

## Reproduce

```bash
python3 -m venv .venv && ./.venv/bin/pip install numpy scipy matplotlib amazon-braket-sdk

# once, with network: build the model (stores derived quantities only)
./.venv/bin/pip install yfinance pandas openpyxl
./.venv/bin/python fetch_sp100.py

# articles 2 and 2b: full measurement, both distributions, figures
./run_benchmarks.sh

# article 3: local simulator and control-plane latency (free, read-only calls)
./.venv/bin/python probe_local.py
AWS_PROFILE=<your-profile> ./.venv/bin/python probe_api_latency.py

# article 5: QAE on the local simulator (free)
./.venv/bin/python qae_tail.py validate
./.venv/bin/python qae_tail.py scaling 400
./.venv/bin/python qae_tail.py resources
./.venv/bin/python qae_tail.py budget

# article 6: hardware (free steps first; submitting costs money)
./.venv/bin/python hw_qae.py check
./.venv/bin/python hw_qae.py preview
./.venv/bin/python hw_qae.py cost
```

`hw_qae.py submit` refuses to run without `--submit` and a `--max-usd`
ceiling above the planned cost, and it skips offline devices. Set a spending
limit per device in the Braket console first.

## Files

| File | Content |
|---|---|
| `fetch_sp100.py` | Loads holdings and prices, estimates covariance and ν |
| `data/sp100_model.npz`, `.json` | Derived model (tickers, weights, μ, Σ, ν) |
| `data/braket_devices_2026-09-24.json` | Device error rates and timing as reported through Braket |
| `mc_baseline.py` | Model, estimator, exact reference and error constant |
| `mc_variance_reduction.py`, `retime_variance_reduction.py` | Quasi-MC, importance sampling, calibration, interleaved timing |
| `throughput_probe.py` | Multi-core scaling with a persistent pool |
| `mc_baseline.jl`, `export_model.py` | Julia port on the identical model |
| `run_benchmarks.sh` | Complete measurement chain with log |
| `probe_local.py`, `probe_api_latency.py` | Article 3: local simulator, control-plane latency |
| `loop_core.py`, `hybrid_entry.py`, `article4_*.json` | Article 4: latency loop, Hybrid Job entry point, raw data |
| `qae_tail.py` | Article 5: QAE from standard gates, scaling, resources, budget |
| `hw_qae.py`, `hw_tasks.json`, `hw_spend.json` | Article 6: hardware runs, results, spending-limit counters |
| `plot_*.py` | Regenerate all figures (DE/EN, light/dark) |
| `medium_export.py` | Turns an article into Medium-ready HTML with tables as images |
| `results_*.json`, `throughput*.json`, `julia_*.json`, `benchmark.log` | Raw results |
| `archiv/` | First version (synthetic model) and discarded runs, with notes |
| `quellen-dossier.md`, `ergebnisse-speedup.md` | Source dossier and result notes (German) |

## License

Code (`*.py`, `*.jl`, `*.sh`): [MIT](LICENSE).
Documentation and result data: [CC BY 4.0](LICENSE-CONTENT.md).
Not included: raw prices and ETF holdings (`data/raw/`), which
`fetch_sp100.py` downloads again; the AWS account ID is replaced by
`<account-id>` in all task ARNs.
