"""
Article 6: the smallest QAE circuit on real hardware (variant C).

Circuit: tail-probability oracle from qae_tail.py with 3 data qubits, grid
mean +- 3 sd, threshold at mean + 1.5 sd -> a = 6.6%. Ideal readout of the
flag after k Grover steps: k=0 6.6%, k=1 49%, k=2 93%. Noise pulls all of
them towards 50%; where the three stop being distinguishable, the rotation
has disappeared.

Lowering: QPUs on Braket accept no control modifiers, and IonQ has no CCNOT.
Everything is lowered to CNOT + single-qubit gates (h, t, ti, ry, x), the
same circuit for every device. Toffoli: standard 6-CNOT decomposition.
C^3 Z (the reflection S_0 on data + flag): H . V-chain . H with one of the
comparator's clean carry qubits as ancilla.

Plan (variant C):   k = 0, 1, 2  x  1,000 shots  on IQM Garnet, IQM Emerald,
                    Rigetti Cepheus-1;  x 200 shots on IonQ Forte.

Commands (nothing is sent to a QPU without --submit):
    python hw_qae.py check         # lowered circuits vs. theory, gate counts
    python hw_qae.py preview       # density-matrix simulation with the
                                   # device error rates, what to expect
    python hw_qae.py cost          # cost per task, total, spending limits
    python hw_qae.py submit --max-usd 70 --submit
    python hw_qae.py collect       # fetch results of submitted tasks

Prices: AWS Braket on-demand pricing page, checked 24.09.2026.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

import qae_tail as q

N, SIGMAS, THRESH_SD = 3, 3.0, 1.5
KS = [0, 1, 2]

DEVICES = {
    "IQM Garnet": {"arn": "arn:aws:braket:eu-north-1::device/qpu/iqm/Garnet",
                   "shots": 1000, "per_shot": 0.00145},
    "IQM Emerald": {"arn": "arn:aws:braket:eu-north-1::device/qpu/iqm/Emerald",
                    "shots": 1000, "per_shot": 0.00160},
    "Rigetti Cepheus-1": {"arn": "arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q",
                          "shots": 1000, "per_shot": 0.000425},
    "IonQ Forte": {"arn": "arn:aws:braket:us-east-1::device/qpu/ionq/Forte-1",
                   "shots": 200, "per_shot": 0.08},
    # Fallbacks while Forte-1 is offline (24.09.2026): same IonQ family, and a
    # second trapped-ion vendor. Braket lists one price for all Forte devices.
    "IonQ Forte Enterprise 1": {
        "arn": "arn:aws:braket:us-east-1::device/qpu/ionq/Forte-Enterprise-1",
        "shots": 200, "per_shot": 0.08},
    "AQT IBEX Q1": {"arn": "arn:aws:braket:eu-north-1::device/qpu/aqt/Ibex-Q1",
                    "shots": 200, "per_shot": 0.0235},
}
PER_TASK = 0.30
TASKS_FILE = "hw_tasks.json"
DEVICE_DATA = "data/braket_devices_2026-09-24.json"


# --------------------------------------------------------------------------
# Lowering to CNOT + single-qubit gates
# --------------------------------------------------------------------------

def toffoli(c, a, b, t):
    """Nielsen & Chuang Fig. 4.9: 6 CNOT, 7 T/T-dagger, 2 H."""
    c.h(t); c.cnot(b, t); c.ti(t); c.cnot(a, t); c.t(t); c.cnot(b, t)
    c.ti(t); c.cnot(a, t); c.t(b); c.t(t); c.h(t); c.cnot(a, b); c.t(a)
    c.ti(b); c.cnot(a, b)


def mcz(c, controls, target, ancillas):
    """C^k Z with a V-chain of k-2 clean ancillas (k >= 3), CZ via H-CNOT-H."""
    k = len(controls)
    c.h(target)
    if k == 1:
        c.cnot(controls[0], target)
    elif k == 2:
        toffoli(c, controls[0], controls[1], target)
    else:
        assert len(ancillas) >= k - 2, "not enough clean ancillas"
        chain = [(controls[0], controls[1], ancillas[0])]
        for i in range(2, k - 1):
            chain.append((controls[i], ancillas[i - 2], ancillas[i - 1]))
        for a, b, t in chain:
            toffoli(c, a, b, t)
        toffoli(c, controls[k - 1], ancillas[k - 3], target)
        for a, b, t in reversed(chain):
            toffoli(c, a, b, t)
    c.h(target)


def lower(circ, ancillas):
    """Rewrite ccnot and controlled-z instructions; keep everything else."""
    from braket.circuits import Circuit
    out = Circuit()
    for ins in circ.instructions:
        name = ins.operator.name.lower()
        tg = [int(x) for x in ins.target]
        ctrl = [int(x) for x in ins.control] if ins.control else []
        if name == "ccnot":
            toffoli(out, tg[0], tg[1], tg[2])
        elif name == "z" and ctrl:
            mcz(out, ctrl, tg[0], ancillas)
        elif ctrl:
            raise ValueError(f"unexpected controlled {name}")
        else:
            out.add_instruction(ins)
    return out


def oracle():
    return q.TailOracle(N, sigmas=SIGMAS, threshold_sd=THRESH_SD)


def hw_circuit(k: int):
    o = oracle()
    return lower(o.circuit(k), ancillas=o.carry), o


def counts(circ):
    two = sum(1 for i in circ.instructions if i.operator.name.lower() == "cnot")
    one = sum(1 for i in circ.instructions if len(i.target) == 1)
    return two, one, circ.depth


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_check():
    from braket.devices import LocalSimulator
    sim = LocalSimulator()
    rows = []
    for k in KS:
        c, o = hw_circuit(k)
        p1 = float(sim.run(c.copy().probability(target=[o.flag]), shots=0)
                   .result().values[0][1])
        th = o.theta
        ideal = math.sin((2 * k + 1) * th) ** 2
        two, one, depth = counts(c)
        ops = sorted({i.operator.name.lower() for i in c.instructions})
        rows.append({"k": k, "p_sim": p1, "p_theory": ideal, "cnot": two,
                     "single": one, "depth": depth, "ops": ops})
        print(f"k={k}: P(flag=1) sim {p1:.6f} theory {ideal:.6f} | "
              f"{two} CNOT, {one} 1q, depth {depth} | ops {ops}")
    o = oracle()
    print(f"a = {o.dist['a']:.5f}, qubits used = {o.nqubits}")
    json.dump({"a": o.dist["a"], "circuits": rows},
              open("results_hw_check.json", "w"), indent=2)


def noise_model_circuit(circ, p2, p1=1e-4, readout=0.0):
    """Depolarizing after every gate, bit flip before readout.

    Braket's TwoQubitDepolarizing(p) has average gate fidelity 1 - 4p/5, so a
    reported two-qubit infidelity r maps to p = 5r/4. A rough model: no
    crosstalk, no leakage, and no SWAPs from qubit routing, which the real
    compilers add on IQM and Rigetti. The preview is therefore optimistic.
    """
    from braket.circuits import Circuit, Gate
    from braket.circuits.noises import BitFlip, Depolarizing, TwoQubitDepolarizing
    c = circ.copy()
    c.apply_gate_noise(TwoQubitDepolarizing(min(5 * p2 / 4, 15 / 16)),
                       target_gates=[Gate.CNot])
    c.apply_gate_noise(Depolarizing(min(3 * p1 / 2, 0.75)),
                       target_gates=[Gate.H, Gate.T, Gate.Ti, Gate.Ry, Gate.X])
    if readout:
        c.apply_readout_noise(BitFlip(readout))
    return c


def cmd_preview():
    from braket.devices import LocalSimulator
    sim = LocalSimulator("braket_dm")
    devs = json.load(open(DEVICE_DATA))["devices"]
    err = {"IQM Garnet": 1 - devs["IQM Garnet"]["fidelity_median"],
           "IQM Emerald": 1 - devs["IQM Emerald"]["fidelity_median"],
           "Rigetti Cepheus-1": 1 - devs["Rigetti Cepheus"]["fidelity_median"],
           "IonQ Forte (listed)": 1 - devs["IonQ Forte"]["fidelity_mean_2q"],
           "IonQ Forte (IonQ spec 0.4%)": 0.004,
           "IonQ Forte Enterprise 1": 1 - devs["IonQ Forte Enterprise 1"]["fidelity_mean_2q"],
           "IonQ Forte Enterprise 1 (IonQ spec 0.4%)": 0.004}
    out = {}
    for name, p2 in err.items():
        row = []
        for k in KS:
            c, o = hw_circuit(k)
            nc = noise_model_circuit(c, p2).probability(target=[o.flag])
            row.append(float(sim.run(nc, shots=0).result().values[0][1]))
        out[name] = {"two_qubit_error": p2, "p_flag": row}
        print(f"{name:28} err {p2:.2%}  P(flag=1) k=0,1,2: "
              + "  ".join(f"{x:.3f}" for x in row))
    ideal = [math.sin((2 * k + 1) * oracle().theta) ** 2 for k in KS]
    print(f"{'ideal':28}               " + "  ".join(f"{x:.3f}" for x in ideal))
    out["ideal"] = ideal
    json.dump(out, open("results_hw_preview.json", "w"), indent=2)


def plan():
    rows, total = [], 0.0
    for name, d in DEVICES.items():
        cost = len(KS) * (PER_TASK + d["shots"] * d["per_shot"])
        rows.append((name, len(KS), d["shots"], cost))
        total += cost
    return rows, total


def cmd_cost():
    rows, total = plan()
    for name, tasks, shots, cost in rows:
        print(f"{name:20} {tasks} tasks x {shots:>5} shots   ${cost:8.2f}")
    print(f"{'total':20} {'':25} ${total:8.2f}")
    try:
        import boto3
        for region in sorted({d["arn"].split(":")[3] for d in DEVICES.values()}):
            c = boto3.client("braket", region_name=region)
            r = c.search_spending_limits()
            lims = r.get("spendingLimits", [])
            print(f"spending limits in {region}: "
                  + (", ".join(f"{l.get('deviceArn','?').split('/')[-1]}: "
                               f"{l.get('spendingLimit')} (used "
                               f"{l.get('totalSpend', l.get('queuedSpend', '?'))})"
                               for l in lims) or "none set"))
    except Exception as e:                       # read-only; report and go on
        print(f"spending limits: could not read ({type(e).__name__}: {e})")


def cmd_submit(args):
    if "--submit" not in args:
        sys.exit("dry run only: add --submit to send tasks to real hardware")
    max_usd = float(args[args.index("--max-usd") + 1]) if "--max-usd" in args \
        else sys.exit("--max-usd is required")
    only = args[args.index("--only") + 1].split(",") if "--only" in args else None
    rows, total = plan()
    if only:
        total = sum(r[3] for r in rows if r[0] in only)
    if total > max_usd:
        sys.exit(f"planned ${total:.2f} exceeds --max-usd {max_usd}")
    from braket.aws import AwsDevice
    # new tasks go to the unredacted file; hw_tasks.json is the public copy
    store = "hw_tasks.private.json" if os.path.exists("hw_tasks.private.json") \
        else TASKS_FILE
    tasks = json.load(open(store)) if os.path.exists(store) else []
    for name, d in DEVICES.items():
        if only and name not in only:
            continue
        dev = AwsDevice(d["arn"])
        if dev.status != "ONLINE":
            print(f"{name}: {dev.status}, skipped")
            continue
        for k in KS:
            c, o = hw_circuit(k)
            t = dev.run(c, shots=d["shots"])
            tasks.append({"device": name, "k": k, "shots": d["shots"],
                          "arn": t.id, "submitted": time.strftime("%FT%T%z"),
                          "flag_qubit": o.flag})
            print(f"{name} k={k}: {t.id}")
            json.dump(tasks, open(store, "w"), indent=2)


def cmd_collect():
    """Fetch results. Reads hw_tasks.private.json if present -- the published
    hw_tasks.json has the AWS account ID in the ARNs replaced by <account-id>
    -- and skips tasks whose results are already stored."""
    from braket.aws import AwsQuantumTask
    src = "hw_tasks.private.json" if os.path.exists("hw_tasks.private.json") \
        else TASKS_FILE
    tasks = json.load(open(src))
    for t in tasks:
        if t.get("state") == "COMPLETED" and "p_flag" in t:
            print(f"{t['device']:20} k={t['k']} COMPLETED  {t['p_flag']}")
            continue
        if "<account-id>" in t["arn"]:
            print(f"{t['device']:20} k={t['k']} redacted ARN, skipped")
            continue
        task = AwsQuantumTask(t["arn"])
        st = task.state()
        t["state"] = st
        if st == "COMPLETED" and "p_flag" not in t:
            r = task.result()
            # measurements only hold the qubits the circuit touches; map the
            # flag through measured_qubits instead of indexing by its number
            col = list(r.measured_qubits).index(t["flag_qubit"])
            m = r.measurements[:, col]
            t["p_flag"] = float(m.mean())
            t["hits"] = int(m.sum())
            md = task.metadata()
            t["createdAt"] = str(md.get("createdAt"))
            t["endedAt"] = str(md.get("endedAt"))
        print(f"{t['device']:20} k={t['k']} {st:10} "
              f"{t.get('p_flag', ''):}")
    json.dump(tasks, open(src, "w"), indent=2)
    if src != TASKS_FILE:                   # refresh the redacted public copy
        pub = json.loads(json.dumps(tasks).replace(
            t["arn"].split(":")[4], "<account-id>")) if tasks else tasks
        json.dump(pub, open(TASKS_FILE, "w"), indent=2)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "submit":
        cmd_submit(sys.argv[2:])
    else:
        {"check": cmd_check, "preview": cmd_preview, "cost": cmd_cost,
         "collect": cmd_collect}[cmd]()
