"""
What happens when the generation stage goes wrong.

The rest of this system already handles the failures someone thought about in
advance: `generate.py` backs off and retries a rate limit, `QuotaGuard` stops a
runaway session, and `store.py` tells you to run `app.py index` when there is no
index. Everything else fell through to a traceback.

That is the gap this file closes. It does two things:

1. Turns an exception from the model call into a named reason, so a log can say
   `auth` or `timeout` rather than carrying a 400-line stack trace.

2. Holds the message a reader gets when the call fails, which is deliberately
   NOT the relevance gate's refusal.

On that second point, because it is a promise rather than a detail. The gate's
refusal says "I don't have enough information about that." When the model call
fails, that sentence is false: for a question like the Old Brewhouse laundry
one, the documents do contain the answer and retrieval found it at distance
0.240. Reusing the refusal would blame the corpus for an outage, which is the
same species of confidently-wrong output the gate exists to prevent. A failed
call says so, and the log records it as its own outcome, so an outage is never
counted as a question the corpus could not answer.
"""

from __future__ import annotations

# What a reader sees when the generation stage could not complete.
UNAVAILABLE = (
    "I couldn't reach the answer service just now, so I can't answer this yet. "
    "Your question did match documents in the corpus — this is a problem at my "
    "end, not with what you asked. Try again in a minute."
)


class GenerationFailure(Exception):
    """
    The model call did not produce an answer, and retrying here will not help.

    Carries a `reason` from `classify` so callers and logs can tell an expired
    key apart from a network drop without re-parsing the error text.
    """

    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


# Ordered most specific first — the first match wins, so `auth` is checked
# before the generic `service` bucket that a 400 would otherwise land in.
_SIGNATURES: list[tuple[str, tuple[str, ...]]] = [
    ("auth", ("api key not valid", "api_key_invalid", "unauthenticated",
              "permission denied", "401", "403")),
    ("quota", ("quota", "resource_exhausted", "resource exhausted")),
    ("rate_limit", ("429", "rate limit", "too many requests")),
    ("timeout", ("timeout", "timed out", "deadline exceeded", "readtimeout")),
    ("network", ("connection", "network", "dns", "unreachable", "ssl",
                 "name or service not known")),
    ("service", ("500", "502", "503", "504", "internal error", "unavailable",
                 "bad gateway", "overloaded")),
    ("bad_request", ("400", "invalid_argument", "invalid argument")),
]


def classify(exc: BaseException) -> str:
    """
    Name the reason a model call failed.

    Matching on message text is not elegant, and it is what the SDK gives us:
    the same `ClientError` type carries an expired key, a malformed request and
    a server fault, and only the message tells them apart. The reason codes are
    a closed set so the log stays countable — an unrecognised error becomes
    `unknown` rather than inventing a new category per incident.
    """
    message = f"{type(exc).__name__} {exc}".lower()
    for reason, needles in _SIGNATURES:
        if any(needle in message for needle in needles):
            return reason
    return "unknown"


def describe(reason: str) -> str:
    """A short human sentence for a reason code, for the command line."""
    return {
        "auth": "the API key was rejected — check GEMINI_API_KEY in .env",
        "quota": "the daily quota is used up — it resets tomorrow",
        "rate_limit": "still rate limited after retrying — wait a minute",
        "timeout": "the service took too long to respond",
        "network": "could not reach the service — check your connection",
        "service": "the service returned an error of its own",
        "bad_request": "the service rejected the request as malformed",
        "empty_response": "the service replied, but with no text in it",
        "unknown": "an unrecognised error",
    }.get(reason, "an unrecognised error")
