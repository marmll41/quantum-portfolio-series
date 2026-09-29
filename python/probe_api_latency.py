"""Cloud round-trip latency to the Braket control plane -- costs nothing.

GetDevice is a free API call. No quantum task is submitted, so no shots are
billed.

The probe separates two things that a naive timing conflates:

  handshake  DNS + TCP + TLS to the regional endpoint. This is dominated by
             physical distance and is the floor no API can beat.
  API call   a warm GetDevice on an established connection. Handshake is
             already paid, so what remains is service-side processing plus
             one round trip.

Reporting only the second would hide where the time goes; reporting only the
first would understate it.
"""
import os
import socket
import ssl
import statistics
import time

import boto3
from botocore.config import Config

# Uses the default AWS credential chain; set AWS_PROFILE to choose a profile.

TARGETS = [
    ("eu-north-1", "Stockholm", "iqm/Garnet"),
    ("eu-north-1", "Stockholm", "aqt/Ibex-Q1"),
    ("us-east-1", "N. Virginia", "ionq/Forte-Enterprise-1"),
    ("us-west-1", "N. California", "rigetti/Cepheus-1-108Q"),
    # no QPU left in Oregon; the SV1 simulator is queried there instead
    ("us-west-2", "Oregon", "sim:amazon/sv1"),
]
REPS = 15          # GetDevice is capped at 5/s; 0.25 s spacing stays clear


def handshake_ms(region: str, reps: int = 7) -> dict:
    """Fresh DNS + TCP + TLS each time -- the physical floor."""
    host = f"braket.{region}.amazonaws.com"
    ctx = ssl.create_default_context()
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                pass
        ts.append((time.perf_counter() - t0) * 1000)
        time.sleep(0.1)
    return {"median": statistics.median(ts), "min": min(ts)}


def api_ms(region: str, device: str, reps: int = REPS) -> dict:
    """Warm GetDevice -- connection already established."""
    arn = (f"arn:aws:braket:::device/quantum-simulator/{device[4:]}"
           if device.startswith("sim:")
           else f"arn:aws:braket:{region}::device/qpu/{device}")
    cfg = Config(retries={"max_attempts": 1, "mode": "standard"})
    c = boto3.client("braket", region_name=region, config=cfg)
    for _ in range(3):                       # warm creds + TLS + pool
        c.get_device(deviceArn=arn)
        time.sleep(0.25)
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        c.get_device(deviceArn=arn)
        ts.append((time.perf_counter() - t0) * 1000)
        time.sleep(0.25)
    ts_sorted = sorted(ts)
    return {
        "median": statistics.median(ts),
        "min": min(ts),
        "p90": ts_sorted[int(len(ts_sorted) * 0.9)],
        "max": max(ts),
    }


if __name__ == "__main__":
    print("Braket control-plane latency from this machine")
    print("Free API calls only -- no quantum task submitted, nothing billed\n")
    print(f"{'region':<12} {'site':<15} {'handshake':>11} "
          f"{'API med':>9} {'API min':>9} {'API p90':>9} {'API max':>9}")
    import json, sys
    seen, rows = {}, []
    for region, site, device in TARGETS:
        if region not in seen:
            seen[region] = handshake_ms(region)
        h = seen[region]
        a = api_ms(region, device)
        print(f"{region:<12} {site:<15} {h['median']:>9.1f}ms "
              f"{a['median']:>7.1f}ms {a['min']:>7.1f}ms "
              f"{a['p90']:>7.1f}ms {a['max']:>7.1f}ms")
        rows.append({"region": region, "site": site, "device": device,
                     "handshake_ms": h, "api_ms": a})
    out = sys.argv[1] if len(sys.argv) > 1 else "results_api_latency.json"
    json.dump({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "reps": REPS, "rows": rows}, open(out, "w"), indent=2)
    print(f"\nwrote {out}")
