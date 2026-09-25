"""The serial loop whose latency Article 4 measures.

Deliberately the shape of a variational optimiser: submit a circuit, wait for
the result, decide the next parameter, repeat. The circuit is trivial on
purpose -- we are measuring the machinery around it, not the computation.

The same function runs unchanged on a laptop and inside a Braket Hybrid Job,
which is the whole point of the comparison.
"""
import time

from braket.circuits import Circuit

SHOTS = 100
N_QUBITS = 4
HARD_TIMEOUT_S = 600      # SV1 bills per minute and is NOT covered by
                          # Braket spending limits -- never run unbounded.


def ansatz(theta: float) -> Circuit:
    """A tiny parameterised circuit; one rotation, one entangling layer."""
    c = Circuit().rx(0, theta)
    for q in range(N_QUBITS - 1):
        c.cnot(q, q + 1)
    return c


def serial_loop(device, iterations: int, s3_folder=None, shots: int = SHOTS):
    """Submit -> wait -> next. Returns per-iteration wall-clock in ms."""
    per_iter, started = [], time.perf_counter()
    for i in range(iterations):
        if time.perf_counter() - started > HARD_TIMEOUT_S:
            raise TimeoutError(f"hard timeout after {i} iterations")
        theta = 0.1 * i
        t0 = time.perf_counter()
        kw = {"shots": shots}
        if s3_folder:
            kw["s3_destination_folder"] = s3_folder
        task = device.run(ansatz(theta), **kw)
        task.result()                      # blocking -- this is the point
        per_iter.append((time.perf_counter() - t0) * 1000)
    return per_iter
