# Source Dossier — Quantum Portfolio Optimization on AWS

**English** · [Deutsch](source-dossier.de.md)

As of: 2026-09-22

Evidence collection for the article series. Each source with its status, key
figures, quotable passages and the article it belongs to.

**Legend: evidence status**
- **[P]** Peer-reviewed / published
- **[PP]** Preprint (arXiv), not peer-reviewed
- **[V]** Vendor / marketing content — not evidence, only an exhibit
- **[S]** Secondary source (journalism)

---

## The thesis of the series

> The speedup is real, but an order of magnitude too weak to beat the
> constants — and the crossover lies in an accuracy range with no financial
> meaning.

The pattern of evidence across all sources:

**When the numbers are worked out rigorously, the result is catastrophic.
When they are not worked out, there is a result.**

---

## 1. Dalzell et al. — The assessment framework  [PP]

*Quantum algorithms: A survey of applications and end-to-end complexities*
AWS Center for Quantum Computing · arXiv:2310.03011

**Role in the series:** Methodological foundation. Defines what an end-to-end
assessment of a quantum algorithm has to deliver (among others "criterion 4
of the end-to-end practical algorithm", which the QIPM paper tests against).

**Why it matters:** Article 1 does not need a home-made scheme. The claim is
not "I think it should be measured differently" but "AWS has defined how to
measure, and most papers don't."

→ **Article 1**

---

## 2. AWS + Goldman Sachs — QIPM, the continuous case  [P]

*End-to-end resource analysis for quantum interior point methods and
portfolio optimization*
PRX Quantum 4, 040325 (2023) · arXiv:2211.12489 (v2, May 2024)

Complete resource analysis at circuit level, **including constant factors** —
from problem input to output. Exactly the calculation that is otherwise
missing.

**Key figures for n = 100 assets**

| Quantity | Value |
|---|---|
| Logical qubits | 8,000,000 |
| T-count | 7 × 10^29 |
| T-depth | 2 × 10^24 |

**Quote (load-bearing):**
> "Even if layers of T-gates are optimistically implemented at the GHz speeds
> of classical processors (in reality they are likely to be 2–4 orders of
> magnitude slower than that) these estimates suggest that the runtime of the
> quantum algorithm would still be millions of years, even for an instance size
> that is already classically tractable on a laptop."

**Quote (conclusion):**
> "the QIPM, in its current form, does not satisfy criterion 4 of the
> end-to-end practical algorithm"

**Own calculation (label it as such in the article):**
2 × 10^24 layers at 10^9 layers/s = 2 × 10^15 s ≈ **63 million years**.
With the realistic 2–4 orders of magnitude slower: 6 to 600 billion years.
Age of the universe for comparison: ~13.8 billion years.

8 million *logical* qubits mean several billion physical qubits at realistic
surface-code overhead. Current devices: a few hundred.

**Rhetorical value:** AWS's own team, on AWS's own blog. Ideal for an AWS
series — not an accusation, a quote.

→ **Articles 6, 8**

---

## 3. Chakrabarti et al. — Derivative pricing, the Monte Carlo case  [P]

*A Threshold for Quantum Advantage in Derivative Pricing*
Quantum 5, 463 (2021) · arXiv:2012.03819
Goldman Sachs + IBM + QuICS/UMD

Benchmark instruments: autocallables and TARFs. Introduces the
re-parameterization method to get around known blockers.

**Key figures**

| Quantity | Value |
|---|---|
| Logical qubits | 8,000 |
| T-depth | 54,000,000 |
| Required logical clock rate | **50 MHz** |

> **Correction 24 Sep 2026 (fact check against the original):** The paper
> states **10 MHz** ("the quantum processor would need to execute T-gates at a
> rate of 10MHz"), not 50 MHz, and even "current estimates target logical clock
> rates around 10kHz" — the ~40 kHz below are my own derivation, not from the
> paper. Also: the GHz quote of the QIPM work comes from the AWS blog of
> 13 Nov 2023, not from the PRX Quantum paper; "63 million years" is my own
> calculation. IBM/Vanguard v1: 19 Aug 2025.

The 50 MHz are the rate needed to match the classical MC pricing time of
~1 second.

**Own assessment (label it as such in the article):**
Superconducting surface-code cycle ~1 µs; one logical operation takes ~d
cycles at d ≈ 25 → ~25 µs per logical operation → logical clock rate
**~40 kHz**. 50 MHz is thus roughly **three orders of magnitude** beyond what
surface-code architectures project.

**The decisive comparison with source 2:**
Derivative pricing needs 8,000 logical qubits, QIPM 8,000,000. QAE is the
better algorithm by a factor of 1,000 — the Monte Carlo side is the
**strongest case** quantum finance has to offer. And even there it fails on
wall-clock time. That is why the series starts with Monte Carlo.

→ **Articles 3, 6, 8**

---

## 4. Babbush et al. — Why quadratic is fundamentally not enough  [P]

*Focus beyond Quadratic Speedups for Error-Corrected Quantum Advantage*
PRX Quantum 2, 010103 (2021) · arXiv:2011.04149
Google Quantum AI (Babbush, McClean, Newman, Gidney, Boixo, Neven)

**Core claim:** Quadratic speedups do **not** enable quantum advantage on early
error-corrected devices unless error correction improves fundamentally. The
constant-factor overhead eats them up. Practical advantage rather needs
**quartic** speedups.

**Why load-bearing:** QAE delivers exactly a quadratic speedup. So the claim is
not "the hardware isn't there yet" but structural. And it comes from Google's
own quantum team — not a fringe position.

**Line to remember for the article:** Today's hardware is slow because it is
noisy. Future hardware stays slow because error correction is expensive.

→ **Articles 1, 8**

---

## 5. IBM + Vanguard — CVaR-VQA, the NISQ case  [PP]

*Portfolio construction using a sampling-based variational quantum scheme*
arXiv:2508.13557 (v1 Aug 2025, **v2 Nov 2025**)
Agliardi, Alevras, Kumar, Lo Nardo, Compostella, Kumar, Proissl (IBM Quantum),
Mehta (Vanguard, Centre for Analytics & Insights)

Note: The IBM blog of 29 Sep 2025 refers to v1. Always cite v2.

**Setup**

| | |
|---|---|
| Problem | Bond ETF construction, simplified to **109 binary variables** |
| Hardware | IBM Heron `ibm_marrakesh`, `ibm_fez`; 109 qubits |
| Shots | 8,192 per iteration |
| Optimizer | NFT, 327–434 parameters |
| Circuits | TwoLocal bilinear (T 17 / 1,525 gates / 216 2Q) · TwoLocal color (T 19 / 1,555 / 246) · BFCD (T 57 / 4,220 / 648) |
| Result | 0.49% / 0.55% / 0.91% gap after local search; simulator 0.39% |

### Finding A — CPLEX solves the same problem provably optimally in seconds

Section II, verbatim:
> "The simplified problem with 109 bonds, on the other hand, can be solved by
> classical solvers like CPLEX or Gurobi to optimality in a few seconds,
> yielding, in the case of CPLEX, 33 solutions with one being the proven optimal."

CPLEX: proven optimum in seconds. Quantum run: 0.49% above it.
**This sentence is in the paper and missing from the IBM blog.**

### Finding B — The "classical baseline" is not a classical solver

The point of comparison in Fig. 5/6 is the *"Initial"* distribution =
iteration 1, the **untrained** circuit. "Purely classical" therefore means:
local search from quasi-random starting points. No simulated annealing, no
tabu search, no runtime comparison against CPLEX.

Translated: *trained quantum seeding beats random seeding.*
A statement about starting points, not about classical optimization.

### Finding C — Not a single hardware runtime in the entire paper

The only timings: Table I, **MPS simulator times on an Apple M1 Pro laptop**
(5 s / 3 min / 16 min for 1k shots). No QPU runtime, no time-to-solution.

The speed argument is explicitly hypothetical:
> "For instance, if hardware requires 2x the number of iterations but is then
> 10x faster than simulators time-wise, then still quantum hardware will be
> 5x faster in the overall time taken to run the scheme."

Made-up numbers — and the point of comparison is the **simulator**, i.e. the
classical simulation of a quantum computer. Not the comparison that matters
for business.

### Finding D — The claim in the abstract is refuted by the paper's own hardware run

Abstract: *"hard-to-simulate quantum circuits may lead to better convergence
than simpler circuits."* This comes from the **31-qubit simulation**.

On 109-qubit hardware BFCD — the hard-to-simulate ansatz — performed **worst**
(0.91% vs. 0.49%). The paper says so and explains it: slower convergence,
local search fails on unconverged samples.

### Finding E — The load-bearing premise is unpublished

Motivation: professional solvers did not deliver good solutions for
1,000–10,000 instruments within 5–10 minutes. Footnote 1:
> "Empirical estimate based on internal work."

No benchmark, no solver version, no configuration, not reproducible.

### Finding F — The conclusions are honest

> "In order for quantum methods to provide an advantage over classical, though,
> it is essential to scale the problem size to a much larger regime, where
> classical solvers struggle."

> "we believe that little can be inferred about the runtime at large scale,
> from experiments of small to mid problem size, given the heuristic nature
> of the methods."

The authors do not overreach. **The gap lies between the paper and its
reception, not between the paper and the truth.** Tone accordingly: don't
criticize the researchers, correct the reading.

### Own order of magnitude (not from the paper)

NFT needs 3 circuit evaluations per parameter. At 327 parameters:
~981 circuits/epoch × 8,192 shots = **~8 million shots per epoch**.

In Braket prices (IBM bills differently; only to put the resource intensity
in context): Rigetti Cepheus ~$3,400 · IQM Garnet ~$11,600 · IonQ Forte
~$640,000 — **per epoch**, for a problem that CPLEX solves provably optimally
in seconds.

**Open:** Iteration counts appear only in Fig. 4–6, not in the text. Read them
off the PDF figures for exact values.

→ **Articles 5, 6, 7 — and the article with the widest reach in the series**

---

## 6. superpositions.studio — QAE vs Monte Carlo  [V]

`superpositions.studio/comparisons/qae-vs-monte-carlo`

**No author, no date, no references.** Marketing content of a commercial
quantum platform. **Useless as a source of facts** — excellent as an exhibit,
because it contains the fallacy the series is about, live.

### The crossover at eps ~ 10^-2 is an artefact

Their own wording: *"the two error curves are **normalized** to cross around
eps ~ 10^-2."*

1/eps^2 and 1/eps with constants = 1 cross at eps = 1. To make them cross at
10^-2, you choose a prefactor of 100. A **charting decision, not a
measurement.**

Dangerous, because 1% accuracy is a range actually used. My own wall-clock
derivation puts the crossover at eps < 10^-6 to 10^-8 — four to six orders of
magnitude off.

> **Correction 24 Sep 2026:** The range 10⁻⁶–10⁻⁸ assumed five to eight orders
> of magnitude in the per-sample time ratio. With my own measurements
> (classical 86 ns/sample on 14 cores, Garnet 11 ms/shot service time, IQM
> gates 20–40 ns) it is two to eight: crossover 10⁻⁵–10⁻⁶ for measured cloud
> values, 10⁻⁶–10⁻⁸ for trapped ions, in the best case (superconducting, bare
> hardware, ~1,000 gates) up to 10⁻³. See article 1, section "The claim that
> isn't one".

The page admits it itself: IQAE beats MC *"only asymptotically and only in
query count, not runtime."* The caveat is in the text, not in the chart.

### Their own numbers refute the headline

| | |
|---|---|
| Problem size | **2 assets** (AAPL, MSFT), 11 qubits |
| Single AE run | 202 ms |
| Full run, 8 cores | **20.6 s** |
| Hardware | **noiseless simulator** |

A 2-asset VaR by classical MC: milliseconds. Without noise, without a queue,
without a cloud round trip.

### The two ways of counting qubits

~700 qubits (their estimate for 100+ assets) vs. 8,000,000 logical qubits
(AWS/Goldman for n = 100). Not a contradiction — **algorithmic** qubits
without error correction against the full **error-corrected** requirement.
The factor in between is the problem the debate glosses over.

Worth a section of its own: *"Why every qubit count you read is one of two
completely different numbers."*

### Fairness

They state openly that nothing runs on real hardware, and for industrial
advantage they name error-corrected hardware in the 2030s with *"thousands of
logical qubits and roughly 10^7–10^9 logical gate operations"*. Factually
defensible.

Tone: not "they are lying" but **"the caveats are in the text, the chart says
something else, and nobody reads the caveats."**

→ **Article 1 (case study), 3**

---

## 7. Tech Monitor / Greg Noone  [S]

*Quantum Untangled: AWS and Goldman* · techmonitor.substack.com · 16 Nov 2023

Secondary coverage of source 2. Do not cite as evidence — use the primary
source. Useful as an example of how the result was received.

---

## AWS Braket — platform facts (live query 2026-09-22)

Re-check prices and devices before publishing each article. Important:
**the AWS documentation is outdated in several places.** The table below comes
from `aws braket search-devices`, not from the docs.

### Regions and actual device status

| Region | Device | Qubits | Status |
|---|---|---|---|
| **us-west-1** (N. California) | Rigetti **Cepheus-1-108Q** | 108 | online |
| | Rigetti Ankaa-3 | 84 | **retired** — docs still list it |
| | SV1, DM1 | — | online |
| **us-east-1** (N. Virginia) | IonQ Forte Enterprise 1 | 36 | online |
| | IonQ Forte-1 | 36 | **offline** |
| | QuEra Aquila (analog) | 256 | online |
| | SV1, DM1 | — | online |
| **eu-north-1** (Stockholm) | IQM Garnet | 20 | online |
| | IQM Emerald | 54 | online |
| | AQT IBEX-Q1 (**trapped ion**) | — | online |
| | *no simulators* | — | — |
| **eu-west-2** (London) | SV1, DM1 only | — | Oxford Lucy retired |

- **TN1 is retired everywhere.**
- Braket is **not available in eu-central-1** (Frankfurt). Stockholm is the
  only EU region with QPUs; London is a third country and has simulators only.
- The SDK can send tasks to QPUs in **any** region, regardless of the working
  region — it automatically opens a session to the device's region.
- **Correction to an earlier version:** Rigetti is in us-west-1, not
  us-west-2.

### Prices

| Device | Per task | Per shot | Reservation/h |
|---|---|---|---|
| Rigetti Cepheus-1 | $0.30 | **$0.000425** | $4,100 |
| IQM Garnet | $0.30 | $0.00145 | $3,000 |
| IQM Emerald | $0.30 | $0.00160 | $4,000 |
| QuEra Aquila | $0.30 | $0.01000 | $2,500 |
| AQT IBEX-Q1 | $0.30 | $0.02350 | $4,800 |
| IonQ Forte | $0.30 | $0.08000 | $7,000 |

SV1 simulator: $0.075/minute. **No D-Wave** on Braket.

20,000 shots, shot fees only without task fee: Cepheus **$8.50** ·
Garnet $29 · AQT $470 · IonQ $1,600. As a full run with 20 tasks of 1,000
shots each: $14.50 · $35 · $476 · $1,606.

### Cost brake: native spending limits

```
aws braket create-spending-limit \
    --device-arn <arn> --spending-limit <USD> \
    --time-period startAt=<epoch>,endAt=<epoch>
```

Per device, amount as `\d+(\.\d{1,2})?`, time period optional. Plus
`update-`, `delete-` and `search-spending-limits`.

**Pitfalls for article 3:**
1. The docs, verbatim: *"Simulators do not support spending limits."* Of all
   things, SV1, billed by the minute, cannot be capped.
2. A limit with an end date no longer protects once it has expired — but:
   **if you omit `--time-period`, AWS sets `endAt` to 2125-12-30**, i.e.
   effectively unlimited. Don't set a period unless you want a period budget.
3. The response of `search-spending-limits` returns `totalSpend` and
   `queuedSpend` — monitoring without Cost Explorer.

**Set on 2026-09-23 in the series' AWS account** (no end date, spend 0):
Cepheus-1-108Q/us-west-1 $100 · Garnet $100 · Emerald $50 · Ibex-Q1 $50
(all eu-north-1). Total exposure **$300**.

### Program Sets

Since 2025: up to 100 circuits per task, up to 24× faster. AWS itself admits
that individually submitted circuits can add **hours** to an experiment →
evidence for the latency thesis in article 4.

### Own measurement: local simulator (free)

Braket `LocalSimulator`, GHZ circuit, Apple M3 Ultra. No AWS, no cost. This
is the **floor of the latency stack** — everything the cloud adds is measured
against it.

| Qubits | Shots | Median | µs/shot |
|---|---|---|---|
| 5 | 1,000 | 4.3 ms | 4.3 |
| 10 | 1,000 | 6.5 ms | 6.5 |
| 15 | 1,000 | 12.9 ms | 12.9 |
| 20 | 1,000 | **23.7 ms** | 23.7 |

> **Updated 25 Sep 2026:** Article 3 uses the repeat run on the M3 Max
> (`results/results_local_sim.json`): 3.7 / 5.6 / 9.2 / **16.8 ms**. The
> values above are from the M3 Ultra (23 Sep).

### Own measurement: Braket control-plane latency (2026-09-23)

From a machine in Germany, `GetDevice` (free API call, no task submitted).
Handshake = fresh DNS + TCP + TLS, i.e. the physical floor. API = warm call on
an established connection.

| Region | Handshake | API median | API p90 | API max |
|---|---|---|---|---|
| eu-north-1 Stockholm | 71 ms | **140 ms** | 243 ms | 434 ms |
| us-east-1 N. Virginia | 226 ms | 271 ms | 358 ms | 384 ms |
| us-west-1 N. California | 419 ms | **920 ms** | 1,698 ms | 4,217 ms |
| us-west-2 Oregon | 422 ms | **269 ms** | 301 ms | 602 ms |

**The central finding:** us-west-1 and us-west-2 have practically identical
handshakes (419 vs. 422 ms) — the same distance. But the API response differs
by **a factor of 3.4**. That is not distance, that is the region itself.
us-west-1 is AWS's oldest West Coast region (2009).

And that is exactly where Cepheus-1-108Q sits — the device with 108 qubits and
the cheapest shot price. **You pay in latency what you save on shots.**

Extrapolated to a variational loop with 200 serial iterations, round trip
only, without queue and without gate time:

| Region | 200 iterations |
|---|---|
| Stockholm | 28 s |
| us-west-2 | 54 s |
| us-west-1 | **184 s** |

A real loop needs several calls per iteration (submit, poll, retrieve), so the
factor is even higher.

**Limitation:** One location. us-west-1 was measured three times on 23 Sep
(medians 785 / 1,001 / 920 ms) — generalizing to other locations is not
supported by evidence.

### Repeat 2026-09-29 (three runs back to back, stable network)

`results/results_api_latency_2026-09-29_run{1,2,3}.json`, same script
(`python/probe_api_latency.py`, 15 calls per device), 10:23–10:27. API median
per run:

| Region / device | Run 1 | Run 2 | Run 3 | Handshake | 23 Sep |
|---|---:|---:|---:|---:|---:|
| eu-north-1 IQM Garnet | 142 ms | 145 ms | 131 ms | 91–93 ms | 140 ms |
| eu-north-1 AQT Ibex-Q1 | 109 ms | 111 ms | 108 ms | 91–93 ms | – |
| us-east-1 IonQ Forte Enterprise 1 | 209 ms | 207 ms | 204 ms | 227–235 ms | 271 ms |
| us-west-1 Rigetti Cepheus-1 | **654 ms** | **659 ms** | **660 ms** | 341–348 ms | 920 ms |
| us-west-2 SV1 | 234 ms | 236 ms | 248 ms | 367–379 ms | 269 ms |

- Across the three runs the medians vary by at most 11% (Stockholm), in
  us-west-1 by 1%. Maximum us-west-1: 915 / 974 / 1,003 ms (23 Sep: 4,217 ms).
- Ratio us-west-1 / us-west-2: 2.79 / 2.79 / 2.67 (23 Sep: 3.4). The handshake
  to us-west-1 is even shorter here than to us-west-2 — which sharpens the
  finding "region, not distance".
- Across days the absolute values vary by about a third (us-west-1
  920 → 658 ms).
- Extrapolation 200 iterations × 3 round trips in us-west-1: 395 s instead of
  552 s.
- Worked into article 3 (DE/EN) as a paragraph on stability; the table of
  23 Sep remains the main measurement. Two earlier repeats on 25 Sep were
  discarded because the local network was unstable (handshake to us-west-1
  5,175 and 463 ms); they measured the local network, not Braket.

**Consequence:** Braket Hybrid Jobs run the classical loop inside AWS, next to
the device. That is exactly what they exist for. The comparison "loop from the
laptop" against "loop as a Hybrid Job" is the core measurement of article 4.

### Own measurement: laptop vs. Hybrid Job (2026-09-23) — core measurement of article 4

Identical serial loop, 25 iterations, 4-qubit circuit, 100 shots, SV1 in
us-west-1. Simulator instead of QPU, so the queue drops out as a confounder.
The only difference: where the classical driver runs.

| Variant | Median | min | p90 | max |
|---|---|---|---|---|
| local simulator (M3 Ultra) | **2.4 ms** | 2 | 3 | 13 |
| SV1 us-west-1, from the laptop | **3,074 ms** | 1,962 | 3,588 | 3,957 |
| SV1 us-west-1, Hybrid Job (colocated) | **1,677 ms** | 1,556 | 2,081 | 2,611 |

**The finding is not "Hybrid Jobs solve the problem".**

- Colocation saves **1,397 ms per iteration**, a factor of 1.83.
- What remains is **1,677 ms of overhead** — **713 times** the actual
  computation, even though the driver sits right next to the device.
- So the latency is **not primarily network.** About 45% was distance, 55% is
  the Braket task model itself: task creation, scheduling, S3 write, result
  retrieval.

Extrapolated to 200 iterations:

| | Time |
|---|---|
| Laptop | 615 s |
| Hybrid Job | 336 s |
| computation only | **0.5 s** |

**In the colocated run, 0.14% of the time is actual computation.** That
supports the thesis of the series: the variational loop is latency-bound, not
compute-bound.

**Lower bound, not upper bound:** Measured on a simulator without a queue. A
real QPU adds queue time on top.

Side finding: container start of the Hybrid Job **120 s**, once per job. So it
only pays off for longer loops.

**Cost of the entire measurement: ~$0.20** (51 SV1 tasks billed at least 3 s
each, plus 164 s ml.m5.large). The QPU spending limits remain at 0 — SV1 is a
simulator and not covered by them.

### Own measurement: real QPU, IQM Garnet (2026-09-23)

Identical loop, 25 iterations, 4-qubit circuit, 100 shots, eu-north-1.
Execution window open, **queue empty** — i.e. the best case without waiting.

| Variant | Client median | Service median |
|---|---|---|
| local simulator (M3 Ultra) | **2.4 ms** | — |
| SV1 California, from the laptop | 3,074 ms | — |
| SV1 California, Hybrid Job | 1,677 ms | — |
| **IQM Garnet Stockholm, real QPU** | **3,292 ms** | **1,389 ms** |

**The main finding: the quantum hardware is not the bottleneck.** A real QPU
in Stockholm is only 7% above a simulator in California (3,292 vs. 3,074 ms).
The service time Braket itself logs for Garnet (1,389 ms) is even *smaller*
than the client time of the colocated simulator. The device is fast; the
machinery around it is slow.

#### The poll artefact, isolated

By default the SDK polls **every second** (`DEFAULT_RESULTS_POLL_INTERVAL = 1`).
So every client measurement contains up to 1 s of pure polling granularity.
Cross-check with `poll_interval_seconds=0.1`, n = 8:

| Poll interval | Client median | Service median |
|---|---|---|
| 1 s (default) | 3,292 ms | 1,389 ms |
| 0.1 s | **2,290 ms** | 1,139 ms |

**1,002 ms difference — practically exactly the polling grid.** Not an
estimate.

#### Layer breakdown for Garnet (with fast polling)

| Layer | Time | avoidable? |
|---|---|---|
| Poll granularity (default) | ~1,000 ms | **yes**, one parameter |
| Network + S3 retrieval + SDK | ~1,151 ms | partly (colocation) |
| Braket service + device | ~1,139 ms | no |
| actual computation | < 2.4 ms | — |

At 200 iterations in the default configuration: **11 minutes of wall-clock
time, half a second of which is computation.**

**Recommendation that follows from the measurement:** lower
`poll_interval_seconds`. One parameter saves about 200 seconds over 200
iterations — for free.

**Cost:** Garnet 25 iterations $11.13 + 8 iterations poll test $3.56 +
simulator runs ~$0.20 = **~$14.89**. The spending limit counts correctly
(11.125 after the first run) — the brake is not just set but verified.

### Setup hurdles (all worked into article 3)

1. The profile region eu-central-1 is silently adopted by the SDK → the error
   is a bare DNS error on `braket.eu-central-1.amazonaws.com`, not "region not
   supported".
2. `AWSServiceRoleForAmazonBraket` is missing at first → the first task fails
   with AccessDenied.
3. No S3 bucket for task results exists.
4. Hybrid Jobs additionally need an execution role. The SDK finds it
   automatically **only under the path `/service-role/`** — otherwise pass
   `role_arn` explicitly.
5. **Third-party QPUs require a user agreement.** Without accepting it in the
   console, the first task fails with
   `AccessDeniedException: User agreement has not been accepted`.
   Affects IQM, Rigetti, AQT, IonQ, QuEra — **not** SV1/DM1, because those are
   AWS's own simulators. The agreement is a contract with the hardware
   providers and in a company belongs in front of the legal department, not in
   a setup script.

### Environment

Starting state on 2026-09-22: **zero tasks run, no spending limits** in the
series' AWS account.

Region split for the series: **us-west-1** as the workhorse (Cepheus with 108
qubits ≈ the problem size of the Vanguard experiment, cheapest shot price,
simulators on site). **eu-north-1** for article 5, because AQT IBEX-Q1 there
is the only reachable trapped-ion device in the EU.

## Still to obtain

- [ ] Iteration counts from Fig. 4–6 of the Vanguard paper (PDF figures)
- [ ] *Quantum Portfolio Optimization: An Extensive Benchmark* (arXiv:2509.17876)
      — work through it, so far only search hits
- [ ] *Quantum optimization benchmark library — the intractable decathlon*
      (arXiv:2504.03832) — reference [15] of the Vanguard paper, benchmark standard
- [ ] Own measurement series: latency stack on Braket (article 4)
- [ ] Own measurement series: classical MC baseline (article 2)
