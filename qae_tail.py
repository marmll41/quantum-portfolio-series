"""
Quantum amplitude estimation of a tail probability, built from standard gates.

The quantity: a = P(L >= K), the probability that the one-day portfolio loss
of the S&P 500 top-100 portfolio exceeds a threshold K. It is the building
block of every QAE risk calculation: VaR needs a bisection over K on top of
it, CVaR an additional expectation encoding. Both multiply the cost measured
here.

The circuit A = comparator . state_preparation acts on
    data   n qubits   the discretised loss distribution (qubit 0 = MSB)
    carry  n-1 qubits  clean ancillas of the comparator
    flag   1 qubit     |1> exactly for grid points x >= K
so that A|0> = sqrt(1-a)|bad>|0> + sqrt(a)|good>|1>.

Grover operator Q = A S_0 A^dagger S_chi (up to a global phase):
    S_chi  Z on the flag
    S_0    reflection about |0> on data + flag (the carries are always clean)
After k applications, P(flag = 1) = sin^2((2k+1) theta), a = sin^2(theta).

Everything here is built from RY, X, H, CNOT, CCNOT and one multi-controlled Z
per Grover step, so gate counts are honest. For the resource table they are
converted to two-qubit gates: CNOT = 1, CCNOT = 6 (standard decomposition),
C^c Z = 6 * (2c - 3) for c >= 2 controls (V-chain with c-2 clean ancillas).

Estimation: maximum-likelihood QAE (Suzuki et al., Quantum Inf. Process. 19,
75 (2020)) with the exponentially incremented schedule k = 0, 1, 2, 4, ...

Usage:
    python qae_tail.py validate     # circuits vs. sin^2((2k+1)theta)
    python qae_tail.py scaling      # error vs. oracle calls, MLAE vs. MC
    python qae_tail.py resources    # gate counts, depth, time, fidelity
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time

import numpy as np
from scipy.stats import norm

from mc_baseline import CONFIDENCE, build_model

# --------------------------------------------------------------------------
# Discretised loss distribution
# --------------------------------------------------------------------------

SIGMAS = 4.0      # grid covers loss mean +- 4 sd


def discretise(n: int, threshold_quantile: float = CONFIDENCE,
               sigmas: float = SIGMAS, threshold_sd: float | None = None):
    """Loss grid of 2^n bins over mean +- 4 sd, probabilities from the CDF.

    The threshold is snapped to the first bin edge at or above the true VaR.
    Returns bin edges, probabilities, threshold index K and the exact tail
    probability of the discretised distribution (the value QAE estimates).
    """
    m = build_model()
    mu, sd = m.loss_mean, m.loss_sd
    lo, hi = mu - sigmas * sd, mu + sigmas * sd
    edges = np.linspace(lo, hi, 2 ** n + 1)
    cdf = norm.cdf(edges, mu, sd)
    p = np.diff(cdf)
    p /= p.sum()
    var = mu + sd * (norm.ppf(threshold_quantile) if threshold_sd is None
                     else threshold_sd)
    K = int(np.searchsorted(edges, var))          # first edge >= VaR
    K = min(max(K, 1), 2 ** n - 1)
    a = float(p[K:].sum())
    return {"edges": edges, "p": p, "K": K, "a": a,
            "threshold": float(edges[K]), "var_true": float(var),
            "bin_width": float(edges[1] - edges[0])}


# --------------------------------------------------------------------------
# Circuit building blocks (Braket)
# --------------------------------------------------------------------------

def _gray(i):
    return i ^ (i >> 1)


def ucry(circ, controls, target, angles):
    """Uniformly controlled RY (Moettoenen et al., QIC 5, 467 (2005)): 2^k RY + 2^k CNOT.

    angles[j] is applied when the control register reads j, with
    controls[0] as the most significant bit.
    """
    k = len(controls)
    if k == 0:
        circ.ry(target, angles[0])
        return
    N = 2 ** k
    # theta'_i = 2^-k sum_j (-1)^{popcount(j & gray(i))} theta_j
    tp = [sum(((-1) ** bin(j & _gray(i)).count("1")) * angles[j]
              for j in range(N)) / N for i in range(N)]
    for i in range(N):
        circ.ry(target, tp[i])
        changed = _gray(i) ^ _gray((i + 1) % N)
        bit = changed.bit_length() - 1                 # 0 = LSB of j
        circ.cnot(controls[k - 1 - bit], target)


def state_preparation(circ, qubits, p):
    """Load sqrt(p) as amplitudes, qubits[0] = most significant bit."""
    n = len(qubits)
    p = np.asarray(p, dtype=float)
    for level in range(n):
        block = 2 ** (n - level)
        sums = p.reshape(-1, block)
        left = sums[:, : block // 2].sum(axis=1)
        tot = sums.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = np.where(tot > 0, left / tot, 1.0)
        angles = 2 * np.arccos(np.sqrt(np.clip(ratio, 0, 1)))
        ucry(circ, qubits[:level], qubits[level], list(angles))


def comparator(circ, data, carry, flag, K, uncompute=True):
    """flag ^= [x >= K], x read from data (data[0] = MSB).

    x >= K  <=>  x + (2^n - K) >= 2^n: the carry out of adding the constant
    T = 2^n - K. Carries propagate from the LSB; a carry that is a known
    constant 0 is tracked symbolically, so no gates are spent on it.
    """
    n = len(data)
    T = 2 ** n - K
    bits_lsb = [data[n - 1 - i] for i in range(n)]
    ops = []                      # recorded to uncompute in reverse
    c = None                      # None = constant 0, else a qubit
    for i in range(n):
        x, t = bits_lsb[i], (T >> i) & 1
        out = flag if i == n - 1 else carry[i]
        if c is None:
            if t:                 # x OR 0 = x
                ops.append(("cnot", x, out))
                c = out
            else:                 # x AND 0 = 0
                c = None
                if i == n - 1:
                    pass          # flag stays 0
            continue
        if t:                     # x OR c = NOT(NOT x AND NOT c)
            ops += [("x", x), ("x", c), ("ccnot", x, c, out), ("x", out),
                    ("x", x), ("x", c)]
        else:                     # x AND c
            ops.append(("ccnot", x, c, out))
        c = out
    for op in ops:
        _apply(circ, op)
    if uncompute:                 # clean the carries, keep the flag
        for op in reversed(ops):
            touches_flag = op[-1] == flag and op[0] in ("cnot", "ccnot")
            flips_flag = op[0] == "x" and op[1] == flag
            if not (touches_flag or flips_flag):
                _apply(circ, op)
    return ops


def _apply(circ, op):
    if op[0] == "x":
        circ.x(op[1])
    elif op[0] == "cnot":
        circ.cnot(op[1], op[2])
    elif op[0] == "ccnot":
        circ.ccnot(op[1], op[2], op[3])


class TailOracle:
    """Holds the register layout and builds A, A^dagger and Q."""

    def __init__(self, n: int, **kw):
        self.n = n
        self.dist = discretise(n, **kw)
        self.data = list(range(n))
        self.carry = list(range(n, 2 * n - 1))
        self.flag = 2 * n - 1
        self.nqubits = 2 * n

    def A(self):
        from braket.circuits import Circuit
        c = Circuit()
        state_preparation(c, self.data, self.dist["p"])
        comparator(c, self.data, self.carry, self.flag, self.dist["K"])
        return c

    def Q(self):
        from braket.circuits import Circuit
        A = self.A()
        c = Circuit()
        c.z(self.flag)                                  # S_chi
        c.add_circuit(A.adjoint())                      # A^dagger
        reg = self.data + [self.flag]                   # S_0 on data + flag
        for q in reg:
            c.x(q)
        c.z(reg[-1], control=reg[:-1])
        for q in reg:
            c.x(q)
        c.add_circuit(A)                                # A
        return c

    def circuit(self, k: int):
        from braket.circuits import Circuit
        c = Circuit().add_circuit(self.A())
        Q = self.Q()
        for _ in range(k):
            c.add_circuit(Q)
        return c

    @property
    def theta(self):
        return math.asin(math.sqrt(self.dist["a"]))


# --------------------------------------------------------------------------
# Gate accounting
# --------------------------------------------------------------------------

def two_qubit_count(circ) -> int:
    """CNOT = 1, CCNOT = 6, C^c Z / C^c X = 6 (2c - 3) for c >= 2."""
    total = 0
    for ins in circ.instructions:
        name = ins.operator.name.lower()
        nctrl = len(ins.control) if ins.control else 0
        if name == "cnot":
            total += 1
        elif name == "ccnot":
            total += 6
        elif nctrl == 1:
            total += 1
        elif nctrl >= 2:
            total += 6 * (2 * nctrl - 3)
    return total


# --------------------------------------------------------------------------
# Maximum-likelihood amplitude estimation
# --------------------------------------------------------------------------

def mlae_schedule(m: int):
    return [0] + [2 ** j for j in range(m - 1)] if m > 0 else [0]


def mlae_estimate(ks, hits, shots):
    """Global maximum of the MLAE log-likelihood
        sum_k h log sin^2((2k+1)t) + (N-h) log cos^2((2k+1)t),  t in [0, pi/2].

    Coarse grid with 40 points per fringe of the largest k, then the 20 best
    local maxima are refined. A first version searched sequentially in a
    window around the previous estimate; it locked into a wrong fringe in
    ~1-3% of runs and put a floor of ~1% under the error. Those runs were a
    property of the search, not of MLAE.
    """
    def loglik(t):
        out = np.zeros_like(t)
        for k, h in zip(ks, hits):
            s = np.sin((2 * k + 1) * t) ** 2
            s = np.clip(s, 1e-300, 1 - 1e-16)
            out += h * np.log(s) + (shots - h) * np.log(1 - s)
        return out
    kmax = max(ks)
    npts = 40 * (2 * kmax + 1) + 1
    grid = np.linspace(1e-9, math.pi / 2 - 1e-9, npts)
    ll = loglik(grid)
    step = grid[1] - grid[0]
    peaks = np.where((ll[1:-1] >= ll[:-2]) & (ll[1:-1] >= ll[2:]))[0] + 1
    peaks = np.concatenate([peaks, [0, npts - 1]])
    best_t, best_ll = None, -np.inf
    for idx in peaks[np.argsort(ll[peaks])[-20:]]:
        fine = np.linspace(max(grid[idx] - step, 1e-12),
                           min(grid[idx] + step, math.pi / 2), 401)
        lf = loglik(fine)
        if lf.max() > best_ll:
            best_ll, best_t = lf.max(), fine[np.argmax(lf)]
    return math.sin(best_t) ** 2


def oracle_calls(ks, shots):
    """Applications of A: each shot at depth k uses 2k + 1 of them."""
    return shots * sum(2 * k + 1 for k in ks)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_validate():
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator
    sim = LocalSimulator()
    rows = []
    for n in (3, 4, 5):
        o = TailOracle(n)
        for k in (0, 1, 2, 3):
            c = o.circuit(k).probability(target=[o.flag])
            t0 = time.perf_counter()
            p1 = float(sim.run(c, shots=0).result().values[0][1])
            dt = time.perf_counter() - t0
            expect = math.sin((2 * k + 1) * o.theta) ** 2
            rows.append({"n": n, "k": k, "p_sim": p1, "p_theory": expect,
                         "abs_diff": abs(p1 - expect), "sim_s": dt,
                         "two_qubit_gates": two_qubit_count(o.circuit(k))})
            print(f"n={n} k={k}  sim {p1:.10f}  theory {expect:.10f}  "
                  f"diff {abs(p1 - expect):.1e}  ({dt*1e3:.0f} ms)")
    # carries must come back clean: check full distribution for k = 1
    o = TailOracle(4)
    c = o.circuit(1).probability(target=o.carry)
    pc = sim.run(c, shots=0).result().values[0]
    print(f"carry register clean after k=1: P(|0..0>) = {pc[0]:.12f}")
    sp = {}
    for n in (4, 6):
        o = TailOracle(n)
        c = Circuit()
        state_preparation(c, o.data, o.dist["p"])
        c.probability(target=o.data)
        pr = sim.run(c, shots=0).result().values[0]
        sp[str(n)] = {"max_abs_diff": float(np.abs(pr - o.dist["p"]).max()),
                      "cnots": two_qubit_count(c), "expected": 2 ** n - 2}
        print(f"state preparation n={n}: max |p - target| = "
              f"{sp[str(n)]['max_abs_diff']:.1e}, CNOTs {sp[str(n)]['cnots']}")
    json.dump({"validate": rows, "carry_clean_p0": float(pc[0]),
               "state_preparation": sp},
              open("results_qae_validate.json", "w"), indent=2)


def cmd_scaling(shots=100, n=10, reps=400, max_m=12, seed=2026):
    """RMSE of MLAE vs. oracle calls; the same budget spent on k = 0 only is
    plain amplitude sampling, i.e. Monte Carlo on the quantum computer."""
    o = TailOracle(n)
    a, theta = o.dist["a"], o.theta
    rng = np.random.default_rng(seed)
    out = {"n": n, "a": a, "shots": shots, "reps": reps, "mlae": [], "mc": []}
    print(f"n={n}  a={a:.6f}  theta={theta:.6f}  shots/circuit={shots}")
    for m in range(1, max_m + 1):
        ks = mlae_schedule(m)
        Nq = oracle_calls(ks, shots)
        ests = []
        for _ in range(reps):
            hits = [rng.binomial(shots, math.sin((2 * k + 1) * theta) ** 2)
                    for k in ks]
            ests.append(mlae_estimate(ks, hits, shots))
        r = np.abs(np.array(ests) - a) / a
        rel = math.sqrt(np.mean(r ** 2))
        out["mlae"].append({"m": m, "kmax": max(ks), "oracle_calls": Nq,
                            "relerr": rel, "median": float(np.median(r)),
                            "p90": float(np.percentile(r, 90)),
                            # a wrong fringe shifts theta by ~pi/(2k+1)
                            "wrong_fringe_share": float(np.mean(
                                r > 10 * np.median(r))) if m > 3 else 0.0})
        # plain sampling with the same number of A applications
        mc = rng.binomial(Nq, a, size=reps) / Nq
        rel_mc = math.sqrt(np.mean((mc - a) ** 2)) / a
        out["mc"].append({"oracle_calls": Nq, "relerr": rel_mc,
                          "relerr_theory": math.sqrt((1 - a) / (a * Nq))})
        e = out["mlae"][-1]
        print(f"  m={m:2d} kmax={max(ks):5d} calls={Nq:>9,}  MLAE rmse {rel:.2e} "
              f"median {e['median']:.2e} p90 {e['p90']:.2e} "
              f"outl {e['wrong_fringe_share']:.1%}  sampling {rel_mc:.2e}")
    fit = lambda key, f: float(np.polyfit(
        np.log([r["oracle_calls"] for r in out[key][3:]]),
        np.log([r[f] for r in out[key][3:]]), 1)[0])
    out["slope_mlae_rmse"] = fit("mlae", "relerr")
    out["slope_mlae_median"] = fit("mlae", "median")
    out["slope_mc"] = fit("mc", "relerr")
    print(f"slopes: MLAE rmse {out['slope_mlae_rmse']:+.3f}  median "
          f"{out['slope_mlae_median']:+.3f}   sampling {out['slope_mc']:+.3f}")
    json.dump(out, open(f"results_qae_scaling_s{shots}.json", "w"), indent=2)


def cmd_resources():
    rows = []
    for n in range(3, 13):
        o = TailOracle(n)
        A = o.A()
        Q = o.Q()
        rows.append({"n": n, "qubits": o.nqubits, "grid_points": 2 ** n,
                     "bin_width_rel_var": o.dist["bin_width"] / o.dist["var_true"],
                     "a_discrete": o.dist["a"],
                     "A_two_qubit": two_qubit_count(A), "A_depth": A.depth,
                     "Q_two_qubit": two_qubit_count(Q), "Q_depth": Q.depth})
        r = rows[-1]
        print(f"n={n:2d} qubits={r['qubits']:2d}  VaR grid {r['bin_width_rel_var']:.1%}"
              f"  A: {r['A_two_qubit']:>6,} 2q, depth {r['A_depth']:>6,}   "
              f"Q: {r['Q_two_qubit']:>6,} 2q, depth {r['Q_depth']:>6,}")
    json.dump(rows, open("results_qae_resources.json", "w"), indent=2)


def cmd_budget(n=10, shots=400, eps=1e-3):
    """What eps = 1e-3 costs on hardware, from the measured pieces.

    Schedule: the smallest MLAE schedule whose measured relative RMSE
    (results_qae_scaling_s<shots>.json) is <= eps. Gate counts from the
    circuits of n qubits. Times are gates only and serial in depth -- no
    readout, no reset, no cloud: the most favourable reading.
    """
    sc = json.load(open(f"results_qae_scaling_s{shots}.json"))
    row = next(r for r in sc["mlae"] if r["relerr"] <= eps)
    ks = mlae_schedule(row["m"])
    res = {r["n"]: r for r in json.load(open("results_qae_resources.json"))}[n]
    A2, Q2, Ad, Qd = (res["A_two_qubit"], res["Q_two_qubit"],
                      res["A_depth"], res["Q_depth"])
    kmax = max(ks)
    deep_2q, deep_depth = A2 + kmax * Q2, Ad + kmax * Qd
    total_2q = shots * sum(A2 + k * Q2 for k in ks)
    total_layers = shots * sum(Ad + k * Qd for k in ks)
    a = sc["a"]
    n_mc = (1 - a) / (a * eps ** 2)
    out = {"n": n, "shots": shots, "eps": eps, "schedule": ks,
           "oracle_calls": row["oracle_calls"], "measured_relerr": row["relerr"],
           "deepest_two_qubit": deep_2q, "deepest_depth": deep_depth,
           "total_two_qubit": total_2q, "total_layers": total_layers,
           "mc_samples_same_eps": n_mc,
           "gate_time_s": {"IQM 20-40 ns": [20e-9, 40e-9]},
           "time": {}, "survival_deepest": {}, "max_gates_for_half": {}}
    # Device figures as reported through AWS Braket (GetDevice), stored once
    # by hand in data/braket_devices_<date>.json so this runs offline.
    import glob
    dev_file = sorted(glob.glob("data/braket_devices_*.json"))[-1]
    devs = json.load(open(dev_file))["devices"]
    t2q = devs["IonQ Forte"]["timing_s"]["2Q"]
    out["gate_time_s"]["IonQ Forte (Braket)"] = [t2q, t2q]
    out["device_file"] = dev_file
    for name, (t_lo, t_hi) in out["gate_time_s"].items():
        out["time"][name] = {"deepest_shot_s": [deep_depth * t_lo, deep_depth * t_hi],
                             "all_shots_s": [total_layers * t_lo, total_layers * t_hi]}
    for p_err in (1e-3, 5e-3, 1e-2):
        out["survival_deepest"][str(p_err)] = math.exp(deep_2q * math.log1p(-p_err))
        out["max_gates_for_half"][str(p_err)] = math.log(2) / -math.log1p(-p_err)
    r3 = {r["n"]: r for r in json.load(open("results_qae_resources.json"))}[3]
    errors = {name: 1 - d["fidelity_median"] for name, d in devs.items()
              if "fidelity_median" in d}
    errors["IonQ Forte"] = 1 - devs["IonQ Forte"]["fidelity_mean_2q"]
    errors["hypothetical 0.1%"] = 1e-3
    out["devices"] = {}
    for name, pe in errors.items():
        g50 = math.log(2) / -math.log1p(-pe)
        ks_ok = [k for k in range(50)
                 if r3["A_two_qubit"] + k * r3["Q_two_qubit"] <= g50]
        out["devices"][name] = {
            "error": pe, "gates_50pct": g50,
            "max_k_n3": max(ks_ok) if ks_ok else None,
            "survival_one_step_n10": (1 - pe) ** Q2,
            "survival_state_prep_n3": (1 - pe) ** (2 ** 3 - 2),
            "survival_A_n3": (1 - pe) ** r3["A_two_qubit"]}
    # Classical side of the same estimate: n_mc samples at measured rates.
    b1 = json.load(open("results_1core.json"))
    red = max(b1["results"]["reduced"], key=lambda c: c["n"])["paths_per_s"]
    tp = json.load(open("throughput.json"))
    full14 = max(tp["rows"], key=lambda r: r["workers"])
    vr = json.load(open("results_vr_sp100_normal.json"))["methods"]["full"]
    per_path_direct = vr["timing"]["14"]["time_median_s"] / vr["n_run"]
    out["classical"] = {
        "one_dim_1core_s": n_mc / red,
        "full_14core_throughput_s": n_mc / full14["paths_per_s"],
        "full_14core_end_to_end_rate_s": n_mc * per_path_direct}
    json.dump(out, open("results_qae_budget.json", "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    {"validate": cmd_validate, "scaling": cmd_scaling,
     "resources": cmd_resources, "budget": cmd_budget}[cmd](*[int(x) for x in sys.argv[2:]])
