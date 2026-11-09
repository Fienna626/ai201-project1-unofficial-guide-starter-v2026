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
    # Checked before `auth` because they want different fixes: `no_key` means
    # nobody has set GEMINI_API_KEY, `auth` means they set one and the service
    # rejected it. Found by cloning this repo into an empty folder and
    # following RUNNING.md, where a fresh checkout has no .env at all and the
    # whole thing was landing in `unknown`.
    ("no_key", ("no gemini_api_key", "gemini_api_key found", "no api key")),
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


def _status_code(message: str) -> int | None:
    """Pull an HTTP status out of an error message, if there is one.

    The SDK puts the code in the text rather than on the exception, so this
    looks for a bare three-digit number in the 400-599 range. Matching on the
    number rather than on the words around it is the point: "404 NOT_FOUND"
    and "404 Not Found" and "code: 404" are the same failure and used to be
    three different strings to remember.
    """
    import re

    for match in re.finditer(r"\b([45]\d{2})\b", message):
        code = int(match.group(1))
        if 400 <= code <= 599:
            return code
    return None


_STATUS_REASONS = {
    400: "bad_request",
    401: "auth",
    403: "auth",
    404: "bad_request",   # a model name that does not exist is a bad request
    408: "timeout",
    429: "rate_limit",
}

# Exception types that mean the request never reached the service. Checked by
# type rather than by message, because the message is written by whichever
# layer of the network stack failed and differs per platform.
_NETWORK_TYPES = (
    "gaierror", "timeouterror", "connecterror", "connecttimeout",
    "readtimeout", "connectionerror", "remoteprotocolerror",
    "sslerror", "socketerror", "oserror",
)


def classify(exc: BaseException) -> str:
    """
    Name the reason a model call failed.

    Three passes, cheapest and most reliable first:

      1. The exception type, for failures that never reached the service.
      2. An HTTP status code lifted out of the message.
      3. The signature table, for everything the first two cannot see.

    It used to be pass 3 alone, and that is exactly how it failed its own
    acceptance criterion. `_SIGNATURES` is a list of strings I had personally
    seen, so it could only ever name a failure someone had already met. Two
    modes landed in `unknown`: a DNS failure, which says "getaddrinfo failed"
    on Windows where my entry said "name or service not known" — the Linux
    phrasing of the identical fault — and an unknown model name, which returns
    404 where my entry only knew about 400. A platform and a status code I had
    not happened to encounter.

    Passes 1 and 2 do not have that shape. An `OSError` is an `OSError` on
    every platform, and 404 is 404 whatever words follow it.
    """
    type_name = type(exc).__name__.lower()
    if any(needle in type_name for needle in _NETWORK_TYPES):
        # A timeout is a more specific thing to say than "network", and some
        # timeout classes subclass OSError, so it is checked first.
        if "timeout" in type_name:
            return "timeout"
        return "network"

    message = f"{type(exc).__name__} {exc}".lower()

    # A wrapped network error: the type is the SDK's, the cause is the socket.
    cause = exc.__cause__ or exc.__context__
    if cause is not None:
        cause_name = type(cause).__name__.lower()
        if any(needle in cause_name for needle in _NETWORK_TYPES):
            return "timeout" if "timeout" in cause_name else "network"

    # errno 11001 (Windows) and 11004 are DNS resolution failures and carry no
    # consistent wording at all.
    if "getaddrinfo" in message or "errno 11001" in message or "errno 11004" in message:
        return "network"

    status = _status_code(message)
    if status is not None:
        if status in _STATUS_REASONS:
            # 401/403 reach here as "auth", but an expired key also says so in
            # words, and the words are checked below for the cases where the
            # service returns 400 with an API_KEY_INVALID body.
            if _STATUS_REASONS[status] == "bad_request" and any(
                needle in message
                for needle in ("api key", "api_key", "unauthenticated")
            ):
                return "auth"
            return _STATUS_REASONS[status]
        if 500 <= status <= 599:
            return "service"

    for reason, needles in _SIGNATURES:
        if any(needle in message for needle in needles):
            return reason
    return "unknown"


def describe(reason: str) -> str:
    """A short human sentence for a reason code, for the command line."""
    return {
        "no_key": "no GEMINI_API_KEY is set — copy .env.example to .env and "
                  "paste your key in",
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
