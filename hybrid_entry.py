"""Entry point executed INSIDE a Braket Hybrid Job.

Deliberately identical in shape to the laptop loop: submit a circuit, block on
the result, move to the next parameter. The only difference is where the
classical driver runs -- here it sits inside AWS next to the device instead of
on a laptop in Germany. That difference is the whole measurement.

Self-contained on purpose so the job needs no extra packaging.
"""
import os
import statistics
import time

from braket.aws import AwsDevice
from braket.circuits import Circuit
from braket.jobs import save_job_result

SHOTS = 100
N_QUBITS = 4
ITERATIONS = 25


def ansatz(theta: float) -> Circuit:
    c = Circuit().rx(0, theta)
    for q in range(N_QUBITS - 1):
        c.cnot(q, q + 1)
    return c


def main():
    device = AwsDevice(os.environ["AMZN_BRAKET_DEVICE_ARN"])

    per_iter = []
    t_start = time.perf_counter()
    for i in range(ITERATIONS):
        t0 = time.perf_counter()
        device.run(ansatz(0.1 * i), shots=SHOTS).result()
        per_iter.append((time.perf_counter() - t0) * 1000)
    wall = time.perf_counter() - t_start

    ordered = sorted(per_iter)
    save_job_result({
        "iterations": ITERATIONS,
        "shots": SHOTS,
        "per_iter_ms": per_iter,
        "median_ms": statistics.median(per_iter),
        "min_ms": min(per_iter),
        "p90_ms": ordered[int(len(ordered) * 0.9)],
        "max_ms": max(per_iter),
        "wall_s": wall,
        "region": os.environ.get("AWS_DEFAULT_REGION", "?"),
    })
