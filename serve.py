#!/usr/bin/env python3
"""
The Unofficial Guide — the same pipeline, over HTTP.

    python serve.py                          run it locally on port 5000
    gunicorn serve:app                       run it the way a host runs it

Nothing new happens in this file. It is a wrapper: a request comes in, it
hands the question to `app.py::ask_pipeline` — the exact function the command
line uses — and hands the answer back as JSON. Retrieval, the relevance gate
and the grounded prompt all still live where they lived. If you change how
your system answers, you change it in those files and this one follows.

Two routes:

    POST /ask       {"question": "..."} in, the answer and its sources out
    GET  /health    is the service up, and is there an index to search

Why this exists: `app.py` runs once and exits, which is fine on your laptop
and impossible to deploy. A hosted service has to stay up and wait for
requests. This is the smallest thing that does that.

Logging and timing live in `observability.py` and are wired in below.
The starter shipped this file without them on purpose; adding them is
the exercise, and this is that work.
Week 9 has you build the structured log yourself — the request line, the
timing field everyone skips, the whole instrument-before-you-deploy exercise.
Shipping a logger here would hand you the answer to that. Add yours in week 9;
this file stays the bare shell until then.
"""

import os

from flask import Flask, jsonify, request

import config

app = Flask(__name__)


@app.get("/health")
def health():
    """Is the service up, and is there an index to search?

    Two different questions, and the second one is the one that bites. A
    freshly deployed service answers this route happily while every /ask
    returns "no index" — hosts give you no disk that survives a restart, so
    the index has to be built as part of getting the service up. Checking
    here means you find that out in one request instead of five.
    """
    from store import index_exists

    ready = index_exists(config.CORPUS)
    return jsonify(
        {
            "status": "ok",
            "corpus": config.CORPUS,
            "index_ready": ready,
            "detail": (
                "ready"
                if ready
                else "no index for this corpus — run `python app.py index`"
            ),
        }
    )


@app.post("/ask")
def ask():
    """One question in, one grounded answer out.

    A refused question is a 200, not an error. The gate refusing is your
    system working — it is an answer, and the JSON says so with
    `"refused": true` so whatever calls this can tell the two apart.
    """
    from app import ask_pipeline

    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()

    if not question:
        return (
            jsonify(
                {
                    "error": "Send JSON with a question in it, like "
                    '{"question": "is the housing lottery random?"}'
                }
            ),
            400,
        )

    try:
        # source="http" so one log can hold both the CLI and the service and
        # still be split by where a request came from. ask_pipeline logs the
        # request itself, including a generation failure, so nothing is
        # recorded twice here.
        outcome = ask_pipeline(question, corpus=config.CORPUS, source="http")
    except Exception as exc:  # noqa: BLE001 — a reader gets this, not a traceback
        # Anything still reaching here is a fault outside the generation
        # stage — a missing index, most likely. It is logged, because an
        # error nobody recorded is an error nobody can count.
        import observability as obs
        from failures import classify

        obs.log_request(
            source="http",
            question=question,
            outcome="failed",
            reason=classify(exc),
        )
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 500

    body = {
        "question": question,
        "answer": outcome["answer"],
        "refused": outcome["refused"],
        "failed": outcome["failed"],
        "sources": outcome["sources"],
        "best_distance": round(outcome["best_distance"], 4),
        "threshold": outcome["threshold"],
        "corpus": config.CORPUS,
    }

    if outcome["failed"]:
        # 503, not 200 and not 500. The request was fine and the corpus has
        # the material; a dependency is down. A caller retrying on 503 is
        # doing the right thing, which is not true of either of the others.
        body["reason"] = outcome["reason"]
        return jsonify(body), 503

    return jsonify(body)


def main():
    import observability as obs

    obs.log_startup("http")

    # Hosts tell you which port to listen on through PORT, and they expect you
    # on 0.0.0.0. Binding 127.0.0.1 instead works perfectly on your laptop and
    # then answers nothing at all once deployed, because the host's router
    # can't reach a socket that only accepts connections from inside the
    # container. It is the single most common way a first deploy "succeeds"
    # and is unreachable.
    port = int(os.getenv("PORT", "5000"))

    # Debug mode reloads on save, which is handy, and prints a console that
    # runs arbitrary code, which is not something to leave switched on where
    # strangers can reach it. Off unless you ask for it.
    debug = os.getenv("AI201_DEBUG", "0") == "1"

    print(f"Serving The Unofficial Guide on http://localhost:{port}")
    print(f"Corpus: {config.CORPUS}    (Ctrl-C to stop)\n")
    print("Try it from another terminal:\n")
    print(f"  curl http://localhost:{port}/health")
    print(
        f"  curl -X POST http://localhost:{port}/ask \\\n"
        f"    -H 'Content-Type: application/json' \\\n"
        f"    -d '{{\"question\": \"is the housing lottery random?\"}}'\n"
    )

    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
