#!/usr/bin/env python3
"""
What one run of this system actually costs.

    python tools/measure_cost.py
    python tools/measure_cost.py --runs 10

Asks the five test questions, caching off, and reports what each one cost in
tokens and in wall-clock time. Every number comes off the response or off a
clock on this machine. Nothing here is multiplied out of a pricing page: the
point of the exercise is a measurement, and a measurement is a thing you took.

Caching is forced off for the whole process. A cached answer costs nothing and
returns in about a millisecond, which would make the average look wonderful and
mean nothing.

Two numbers come out, and they are different costs:

  per request   what one question costs, averaged over every run
  per run       what one pass over all five test questions costs

The second is the one that matters for `run_eval.py`, which is three passes.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Before importing anything that reads it.
os.environ["AI201_CACHE"] = "0"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2,
                        help="passes over the question set (default 2, "
                             "which is 10 requests)")
    args = parser.parse_args()

    import config
    import questions
    from app import ask_pipeline
    from generate import token_counts

    assert not config.CACHE_ENABLED, "caching must be off for a cost measurement"

    qs = questions.answered()
    print(f"Measuring {args.runs} passes over {len(qs)} questions "
          f"= {args.runs * len(qs)} requests, caching off.\n")

    rows = []
    for run in range(1, args.runs + 1):
        for q in qs:
            before = token_counts()
            timer_start = __import__("time").monotonic()
            outcome = ask_pipeline(q["question"], source="cost-measurement")
            elapsed = (__import__("time").monotonic() - timer_start) * 1000
            after = token_counts()

            row = {
                "run": run,
                "question": q["question"][:44],
                "outcome": ("failed" if outcome["failed"]
                            else "refused" if outcome["refused"]
                            else "answered"),
                "ms": round(elapsed, 1),
                "in": after["prompt"] - before["prompt"],
                "out": after["output"] - before["output"],
            }
            rows.append(row)
            print(f"  run {run}  {row['outcome']:<8} "
                  f"{row['ms']:>7.0f}ms  {row['in']:>4} in  {row['out']:>3} out  "
                  f"{row['question']}")

    answered = [r for r in rows if r["outcome"] == "answered"]
    if not answered:
        print("\nNothing was answered, so there is no cost to report.")
        return 1

    n = len(answered)
    tin = sum(r["in"] for r in answered)
    tout = sum(r["out"] for r in answered)
    lat = [r["ms"] for r in answered]
    per_pass = len(questions.answered())

    print("\n" + "=" * 62)
    print(f"{n} answered requests over {args.runs} passes")
    print("=" * 62)
    print("\nPer request, averaged:")
    print(f"  input tokens   {tin / n:>9.1f}")
    print(f"  output tokens  {tout / n:>9.1f}")
    print(f"  total tokens   {(tin + tout) / n:>9.1f}")
    print(f"  latency        {statistics.mean(lat):>9.0f} ms  "
          f"(median {statistics.median(lat):.0f}, max {max(lat):.0f})")

    print(f"\nPer run, where one run is all {per_pass} test questions:")
    print(f"  total tokens   {(tin + tout) / args.runs:>9.1f}")
    print(f"  wall clock     {sum(lat) / args.runs:>9.0f} ms")
    print(f"  model calls    {n / args.runs:>9.1f}")

    print("\nHow this was measured")
    print("  Token counts are read off usage_metadata on each response, so")
    print("  they are what the service says it charged, not an estimate.")
    print("  Latency is time.monotonic around the whole pipeline: retrieval,")
    print("  the gate, and the model call together.")
    print("  Caching was forced off; a cached answer costs nothing and would")
    print("  flatter the average.")
    print("  Embedding is not in the token count because it runs on this")
    print("  machine and costs no quota at all - it is inside the latency.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
