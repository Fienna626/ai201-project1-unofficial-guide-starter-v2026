#!/usr/bin/env python3
"""
Run the five capstone acceptance criteria and report a number for each.

    python tools/capstone_test.py --trial 1

One trial of all five. The criteria are in criteria.md under "Capstone
acceptance criteria"; this file only measures them.

Criterion 5 is not in here. It needs a clone into an empty folder and a fresh
virtual environment, which is a shell job rather than a Python one, and
automating it inside the repo it is supposed to be independent of would be
measuring the wrong thing. It is run by hand and recorded separately.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
if not Path(PY).exists():                      # posix layout
    PY = str(ROOT / ".venv" / "bin" / "python")

LOG = ROOT / "logs" / "guide.jsonl"


# ─── helpers ─────────────────────────────────────────────────────────────────

def log_len() -> int:
    if not LOG.exists():
        return 0
    with open(LOG, encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def log_tail(since: int) -> list[dict]:
    """Records written after line `since`, plus a count of unparseable ones."""
    out, bad = [], 0
    with open(LOG, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i < since or not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
    out.append({"__unparseable__": bad})
    return out


def run_child(code: str, env_extra: dict[str, str]) -> tuple[str, int]:
    """Run a snippet in a child process so env changes cannot leak."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["AI201_CACHE"] = "0"
    env.update(env_extra)
    proc = subprocess.run(
        [PY, "-c", code], cwd=str(ROOT), env=env,
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    return (proc.stdout or "") + (proc.stderr or ""), proc.returncode


# ─── criterion 1: six failure modes, named, no traceback ────────────────────

INJECT = {
    "no_key": ('GEMINI_API_KEY', ''),
    "auth": ('GEMINI_API_KEY', 'AIzaBogus123456789012345678901234567'),
}

PROBE = '''
import sys
sys.path.insert(0, r"{root}")
import config
{setup}
from app import ask_pipeline
o = ask_pipeline("How often does the campus shuttle run on weekends?")
print("RESULT", o["failed"], o["reason"])
'''


def criterion_1() -> tuple[int, int, list[dict]]:
    """Returns (passed, total, detail)."""
    modes = [
        ("no_key", {"GEMINI_API_KEY": ""}, ""),
        ("auth", {"GEMINI_API_KEY": "AIzaBogus123456789012345678901234567"}, ""),
        ("timeout", {}, "config.REQUEST_TIMEOUT = 0.001"),
        ("network", {}, 'import generate; generate._client = None\n'
                        'config.MODEL = config.MODEL\n'
                        'import os; os.environ["GOOGLE_GEMINI_BASE_URL"] = '
                        '"https://no-such-host-ai201.invalid"'),
        ("bad_request", {}, 'config.MODEL = "models/definitely-not-a-model-xyz"'),
        ("empty_response", {}, _empty_response_setup()),
    ]

    detail = []
    passed = 0
    for name, env, setup in modes:
        code = PROBE.format(root=str(ROOT), setup=setup)
        out, rc = run_child(code, env)
        line = next((l for l in out.splitlines() if l.startswith("RESULT")), "")
        traceback_shown = "Traceback (most recent call last)" in out
        reason = line.split()[-1] if line else None
        failed = " True " in f" {line} "
        ok = (failed and reason not in (None, "unknown") and not traceback_shown)
        passed += 1 if ok else 0
        detail.append({
            "mode": name, "reason": reason, "failed": failed,
            "traceback": traceback_shown, "ok": ok,
        })
    return passed, len(modes), detail


def _empty_response_setup() -> str:
    """Make the SDK return a response whose .text is empty."""
    return (
        'import generate\n'
        'class _Resp:\n'
        '    text = ""\n'
        '    usage_metadata = None\n'
        'class _Models:\n'
        '    def generate_content(self, **kw): return _Resp()\n'
        'class _Client:\n'
        '    models = _Models()\n'
        'generate._get_client = lambda: _Client()'
    )


# ─── criterion 2: 30 concurrent requests, 30 log records ────────────────────

def criterion_2(port: int) -> tuple[int, int, int]:
    """Returns (records_seen, expected, unparseable)."""
    questions = [
        "How often does the campus shuttle run on weekends?",
        "What is the capital of Mongolia?",
        "How late in the semester can I declare a course pass/fail?",
        "Who won the 1994 World Cup?",
        "What does a wash and dry cost in Old Brewhouse?",
        "How do I write a for loop in Rust?",
    ]
    n = 30
    before = log_len()
    results: list[int] = []
    lock = threading.Lock()

    def one(i: int) -> None:
        body = json.dumps({"question": questions[i % len(questions)]}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/ask", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                code = resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        except Exception:
            code = 0
        with lock:
            results.append(code)

    threads = [threading.Thread(target=one, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    time.sleep(1.0)  # let the last append land
    tail = log_tail(before)
    unparseable = tail[-1]["__unparseable__"]
    records = [r for r in tail[:-1] if r.get("event") == "request"]
    return len(records), n, unparseable


# ─── criterion 3: warm p95 under 2000ms ─────────────────────────────────────

def criterion_3(port: int) -> tuple[float, int]:
    """Returns (p95_ms, n). Assumes the server is already warm."""
    before = log_len()
    questions = [
        "How often does the campus shuttle run on weekends?",
        "How late in the semester can I declare a course pass/fail?",
        "What does a wash and dry cost in Old Brewhouse?",
        "When does the withdrawal deadline fall?",
        "How long is the wait at Kestrel Commons at lunch?",
    ]
    for i in range(30):
        body = json.dumps({"question": questions[i % len(questions)]}).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/ask", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=120).read()
        except Exception:
            pass
    time.sleep(0.5)

    lat = [
        r["latency_ms"]
        for r in log_tail(before)[:-1]
        if r.get("event") == "request"
        and r.get("outcome") == "answered"
        and r.get("latency_ms") is not None
    ]
    if not lat:
        return 0.0, 0
    ordered = sorted(lat)
    k = max(0, min(len(ordered) - 1, round(0.95 * len(ordered) + 0.5) - 1))
    return ordered[k], len(lat)


# ─── criterion 4: run cost within 10% of 2238 tokens ────────────────────────

def criterion_4() -> tuple[int, bool]:
    out, _ = run_child(
        f'import sys; sys.path.insert(0, r"{ROOT}")\n'
        'import os; os.environ["AI201_CACHE"]="0"\n'
        'import questions\n'
        'from app import ask_pipeline\n'
        'from generate import token_counts\n'
        'b = token_counts()\n'
        '[ask_pipeline(q["question"], source="criterion4") for q in questions.answered()]\n'
        'a = token_counts()\n'
        'print("TOKENS", a["total"] - b["total"])',
        {},
    )
    line = next((l for l in out.splitlines() if l.startswith("TOKENS")), "TOKENS 0")
    total = int(line.split()[-1])
    return total, 2014 <= total <= 2462


# ─── driver ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", type=int, required=True)
    parser.add_argument("--port", type=int, default=5099)
    parser.add_argument("--only", type=int, default=0, help="run one criterion")
    args = parser.parse_args()

    report: dict = {"trial": args.trial}

    if args.only in (0, 1):
        p, t, detail = criterion_1()
        report["c1"] = {"passed": p, "total": t, "detail": detail}
        print(f"C1 failure modes named : {p}/{t}")
        for d in detail:
            mark = "ok " if d["ok"] else "MISS"
            print(f"     {mark} {d['mode']:<15} reason={d['reason']} "
                  f"traceback={d['traceback']}")

    if args.only in (0, 2):
        seen, exp, bad = criterion_2(args.port)
        report["c2"] = {"records": seen, "expected": exp, "unparseable": bad}
        print(f"C2 log records         : {seen}/{exp}, {bad} unparseable")

    if args.only in (0, 3):
        p95, n = criterion_3(args.port)
        report["c3"] = {"p95_ms": p95, "n": n}
        print(f"C3 warm p95            : {p95:.0f} ms over {n} answered")

    if args.only in (0, 4):
        total, inside = criterion_4()
        report["c4"] = {"tokens": total, "inside": inside}
        print(f"C4 run cost            : {total} tokens, "
              f"{'inside' if inside else 'OUTSIDE'} 2014-2462")

    out = ROOT / "results" / f"capstone_trial{args.trial}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
