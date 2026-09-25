"""Free baseline: how fast is a circuit when there is no cloud involved?

Runs the same circuit on the Braket LOCAL simulator -- no AWS calls, no cost.
This is the floor of the latency stack in Article 4: pure simulated gate
execution with zero network, zero queue, zero task overhead. Everything the
cloud adds later is measured against this.
"""
import statistics
import time

from braket.circuits import Circuit
from braket.devices import LocalSimulator


def ghz(n: int) -> Circuit:
    """A standard entangling circuit -- cheap, and every qubit participates."""
    c = Circuit().h(0)
    for q in range(n - 1):
        c.cnot(q, q + 1)
    return c


def bench(device, circ, shots: int, reps: int = 5) -> dict:
    device.run(circ, shots=shots)                      # warm up
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        device.run(circ, shots=shots).result()
        ts.append(time.perf_counter() - t0)
    med = statistics.median(ts)
    return {"median_s": med, "min_s": min(ts), "per_shot_us": med / shots * 1e6}


if __name__ == "__main__":
    dev = LocalSimulator()
    print("Braket LocalSimulator -- no AWS, no cost\n")
    print(f"{'qubits':>7} {'shots':>8} {'median(s)':>11} {'µs/shot':>10}")
    import json, platform, subprocess
    rows = []
    for n in (5, 10, 15, 20):
        for shots in (100, 1000):
            r = bench(dev, ghz(n), shots)
            rows.append({"qubits": n, "shots": shots, **r})
            print(f"{n:>7} {shots:>8} {r['median_s']:>11.4f} "
                  f"{r['per_shot_us']:>10.1f}")
    cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                         capture_output=True, text=True).stdout.strip()
    json.dump({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "cpu": cpu,
               "python": platform.python_version(), "rows": rows},
              open("results_local_sim.json", "w"), indent=2)
    print("\nwrote results_local_sim.json")
