#!/usr/bin/env python3
"""
Read logs/guide.jsonl and answer the questions worth asking of it.

    python tools/logstats.py
    python tools/logstats.py --log logs/guide.jsonl

This is the payoff for writing the log as JSON lines rather than sentences.
Every number below is a count or a percentile over records that already exist —
no new instrumentation, no re-running anything. That is what "observable" means
in the glossary for this unit: you can answer a question about a system that
already ran without going back and adding code first.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile. No numpy, and honest about small samples."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered) + 0.5) - 1))
    return ordered[k]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default=str(ROOT / "logs" / "guide.jsonl"))
    args = parser.parse_args()

    path = Path(args.log)
    if not path.exists():
        print(f"No log at {path}. Ask the system something first.")
        return 1

    requests, startups, broken = [], 0, 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                broken += 1
                continue
            if record.get("event") == "startup":
                startups += 1
            elif record.get("event") == "request":
                requests.append(record)

    print(f"Log: {path}")
    print(f"  {len(requests)} requests over {startups} sessions")
    if broken:
        print(f"  {broken} unparseable lines")
    if not requests:
        return 0

    outcomes = Counter(r.get("outcome") for r in requests)
    total = len(requests)
    print("\nOutcomes")
    for name in ("answered", "refused", "failed"):
        n = outcomes.get(name, 0)
        print(f"  {name:<9} {n:>4}  {n / total:>5.0%}")

    reasons = Counter(r.get("reason") for r in requests if r.get("reason"))
    if reasons:
        print("\nFailure reasons")
        for reason, n in reasons.most_common():
            print(f"  {reason:<15} {n}")

    sources = Counter(r.get("source") for r in requests)
    print("\nWhere requests came from")
    for src, n in sources.most_common():
        print(f"  {src:<6} {n}")

    lat = [r["latency_ms"] for r in requests if r.get("latency_ms") is not None]
    if lat:
        print("\nLatency, end to end (ms)")
        print(f"  median {statistics.median(lat):>8.0f}")
        print(f"  p95    {percentile(lat, 95):>8.0f}")
        print(f"  max    {max(lat):>8.0f}")

    model = [r["model_ms"] for r in requests if r.get("model_ms") is not None]
    if model and lat:
        share = statistics.median(model) / statistics.median(lat)
        print("\nModel call (ms)")
        print(f"  median {statistics.median(model):>8.0f}  "
              f"({share:.0%} of a median request)")

    answered = [r for r in requests if r.get("outcome") == "answered"]
    tokens_in = sum(r.get("prompt_tokens") or 0 for r in answered)
    tokens_out = sum(r.get("output_tokens") or 0 for r in answered)
    if answered:
        print("\nCost, from the service's own numbers")
        print(f"  {tokens_in} prompt + {tokens_out} output tokens "
              f"over {len(answered)} answered requests")
        print(f"  {tokens_in / len(answered):.0f} in / "
              f"{tokens_out / len(answered):.0f} out per answered request")
        print("  Refused and failed requests cost 0 tokens: the gate stops a "
              "refusal\n  before the model, and a failure never got an answer "
              "back.")

    dists = [r["best_distance"] for r in requests if r.get("best_distance") is not None]
    if dists:
        print("\nBest retrieval distance")
        print(f"  median {statistics.median(dists):.3f}  "
              f"min {min(dists):.3f}  max {max(dists):.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
