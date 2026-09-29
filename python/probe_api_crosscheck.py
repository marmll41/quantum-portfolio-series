"""Cross-check of the control-plane latency -- costs nothing.

probe_api_latency.py queried a different device in every region: Rigetti
Cepheus in us-west-1, SV1 in us-west-2. Cepheus's GetDevice response carries
the full calibration data, about 100 times the size of SV1's, so the two
numbers are not comparable. This probe separates region from payload:

  same device    GetDevice on SV1 in every region that hosts it
  payload        GetDevice on each QPU, with the response size in bytes
  loop call      GetQuantumTask on an existing task per region -- the call a
                 polling loop actually makes, about 2 KB everywhere

GetQuantumTask needs task ARNs; they are read from
results/hw_tasks.private.json (local only, not published), and no ARN is
written to the output.

    AWS_PROFILE=<your-profile> python python/probe_api_crosscheck.py
"""
import json
import os
import statistics
import sys
import time

import boto3
from botocore.config import Config

SV1 = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"
SV1_REGIONS = ["us-east-1", "us-west-1", "us-west-2", "eu-west-2"]
QPUS = [
    ("eu-north-1", "iqm/Garnet"),
    ("eu-north-1", "iqm/Emerald"),
    ("us-east-1", "ionq/Forte-Enterprise-1"),
    ("us-west-1", "rigetti/Cepheus-1-108Q"),
]
TASKS_FILE = "results/hw_tasks.private.json"
REPS = 15          # GetDevice is capped at 5/s; 0.25 s spacing stays clear
CFG = Config(retries={"max_attempts": 1, "mode": "standard"})


def timed(call, reps=REPS):
    for _ in range(3):                       # warm creds + TLS + pool
        r = call()
        time.sleep(0.25)
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        r = call()
        ts.append((time.perf_counter() - t0) * 1000)
        time.sleep(0.25)
    return r, {"median": statistics.median(ts), "min": min(ts),
               "max": max(ts)}


def get_device(region, arn):
    c = boto3.client("braket", region_name=region, config=CFG)
    r, t = timed(lambda: c.get_device(deviceArn=arn))
    caps = r["deviceCapabilities"]
    poll = json.loads(caps).get("service", {}).get("getTaskPollIntervalMillis")
    return {"region": region, "device": arn.split("device/")[1],
            "call": "GetDevice", "bytes": len(caps),
            "poll_interval_ms": poll, "ms": t}


def get_task(region, device, arn):
    c = boto3.client("braket", region_name=region, config=CFG)
    r, t = timed(lambda: c.get_quantum_task(quantumTaskArn=arn))
    return {"region": region, "device": device, "call": "GetQuantumTask",
            "bytes": len(json.dumps(r, default=str)), "ms": t}


def main():
    rows = []
    for region in SV1_REGIONS:
        rows.append(get_device(region, SV1))
    for region, dev in QPUS:
        rows.append(get_device(region,
                               f"arn:aws:braket:{region}::device/qpu/{dev}"))
    if os.path.exists(TASKS_FILE):
        seen = {}
        for t in json.load(open(TASKS_FILE)):
            region = t["arn"].split(":")[3]
            seen.setdefault(region, (t["device"], t["arn"]))
        for region, (dev, arn) in sorted(seen.items()):
            rows.append(get_task(region, dev, arn))
    else:
        print(f"{TASKS_FILE} missing -- GetQuantumTask skipped")
    for r in rows:
        print(f"{r['call']:<15} {r['region']:<11} {r['device']:<32} "
              f"median {r['ms']['median']:6.1f} ms  min {r['ms']['min']:6.1f}"
              f"  {r['bytes']:>8,} B")
    out = sys.argv[1] if len(sys.argv) > 1 else \
        "results/results_api_crosscheck.json"
    json.dump({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "reps": REPS, "rows": rows}, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
