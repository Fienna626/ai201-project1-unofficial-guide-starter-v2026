"""
One structured record per request, so the system can be asked about afterwards.

`serve.py` says, in its own header, that it has no logging and no timing in it
on purpose — building that is the exercise. This is that file.

Why JSON lines rather than sentences. A log that reads "answered the laundry
question in 1.4 seconds" is pleasant and useless: counting how many requests
failed with reason `auth` last Tuesday means writing a parser for English. One
JSON object per line stays readable in a terminal, appends safely, and answers
that question with `grep` or six lines of Python. `tools/logstats.py` is those
six lines.

What gets recorded, and why each field is here rather than merely available:

    ts             when, ISO 8601 with a timezone, so two runs can be ordered
    event          request | startup — one line per request, one per process
    source         cli | http — the same pipeline gets used both ways
    question       what was asked, truncated; the log is evidence, not a corpus
    outcome        answered | refused | failed — the three things that can
                   happen, kept distinct on purpose. A refusal is the gate
                   working; a failure is the system not working. Collapsing
                   them would hide an outage inside a healthy-looking number.
    reason         the failure reason from failures.classify, else null
    best_distance  how close retrieval got, so a refusal can be second-guessed
    threshold      the cutoff in force, because it is tunable and has changed
    top_k          likewise, and it changed between weeks
    n_results      how many chunks actually came back
    sources        which documents went into the prompt
    latency_ms     end to end, measured around the whole pipeline
    model_ms       just the model call, so a slow run can be attributed
    prompt_tokens  what the service said it charged, not an estimate
    output_tokens  likewise

Nothing in here is allowed to break a request. Logging that takes down the
thing it is logging is worse than no logging, so every write is wrapped.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
from pathlib import Path

import config

LOG_DIR = config.ROOT / "logs"
LOG_PATH = Path(os.getenv("AI201_LOG", str(LOG_DIR / "guide.jsonl")))

_lock = threading.Lock()

# How much of a question goes in the log. Long enough to recognise, short
# enough that the log does not become a copy of the corpus.
MAX_QUESTION_CHARS = 200


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def log_event(**fields) -> None:
    """
    Append one record. Never raises.

    The lock matters under `serve.py`: two requests finishing at once on
    different threads would otherwise interleave half-lines, and a corrupted
    line is worse than a missing one because it breaks every later read.
    """
    try:
        record = {"ts": _now(), **fields}
        if isinstance(record.get("question"), str):
            q = record["question"]
            if len(q) > MAX_QUESTION_CHARS:
                record["question"] = q[:MAX_QUESTION_CHARS] + "..."
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _lock:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception:
        pass  # a log write never takes down the request it is describing


class Timer:
    """Wall-clock milliseconds around a block.

    `time.monotonic` rather than `time.time` because the latter can go
    backwards when the clock is adjusted, and a negative latency in a log is
    the kind of thing that costs an hour to explain.
    """

    def __init__(self) -> None:
        self.ms: float = 0.0
        self._start = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *exc) -> None:
        self.ms = round((time.monotonic() - self._start) * 1000, 1)
        return None


def log_request(
    *,
    source: str,
    question: str,
    outcome: str,
    best_distance: float | None = None,
    threshold: float | None = None,
    n_results: int | None = None,
    sources: list[str] | None = None,
    latency_ms: float | None = None,
    model_ms: float | None = None,
    reason: str | None = None,
    prompt_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    """One line for one request. `outcome` is answered | refused | failed."""
    log_event(
        event="request",
        source=source,
        question=question,
        outcome=outcome,
        reason=reason,
        best_distance=round(best_distance, 4) if best_distance is not None else None,
        threshold=threshold,
        top_k=config.TOP_K,
        n_results=n_results,
        sources=sources or [],
        latency_ms=latency_ms,
        model_ms=model_ms,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
    )


def log_startup(source: str) -> None:
    """One line when a process starts, so a log can be split into sessions."""
    log_event(
        event="startup",
        source=source,
        corpus=config.CORPUS,
        model=config.MODEL,
        top_k=config.TOP_K,
        threshold=config.THRESHOLD,
        embedding_model=config.EMBEDDING_MODEL,
        hybrid=config.HYBRID,
    )
