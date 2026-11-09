# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in week 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next week costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:** Four of my five questions are answered by a single
document, and one of them, the Old Brewhouse laundry question, competes
against six other residence-hall laundry posts that are word-for-word identical
except for the price and the payment method. I expect that one to lose to a
near-duplicate, so I set the bar at 4 of 5 rather than 5 of 5.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:** All five, because naming a source costs the pipeline
nothing it doesn't already have — every chunk carries its `source` filename
through `store.py` into the prompt, so citing one is a formatting requirement,
not a retrieval problem. For this to miss, generation would have to ignore
material it was handed, and that's a bug I'd want to see rather than budget for.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" 
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:**
<!-- What did your distances look like when you set the cutoff in Milestone 4?
     Was there a clean gap, or did the two groups overlap? -->
     I expected the four completely unrelated questions (Mongolia, diesel engines, the 1994 World Cup, Rust loops) to sit far from anything in a corpus about one campus, and I expected the ibuprofen question to be the near miss, because health_center.txt is a document about a health centre. I set the target at 4 of 5 to leave room for that one to slip through.

     When I measured in Milestone 4 the separation was much cleaner than I expected, and my guess about which question was risky was wrong. The five in-corpus questions came back between 0.180 and 0.243; the five out-of-scope ones between 0.825 and 0.934. The closest out-of-scope question was Mongolia at 0.825, not ibuprofen, and the ibuprofen question's nearest match was money_textbooks.txt rather than the health centre at all. With a gap that wide I'm leaving the target at 4 of 5 rather than raising it — one clean measurement isn't proof the gate holds for questions I haven't thought of yet.

---

## 4. No chunk is a bare title line

<!-- YOU WRITE THIS ONE.

     How would you know if your chunks were the right size? Name something
     countable or observable.

     Examples of the right shape — don't copy these, they should come from
     what you actually saw in Milestone 3:
       - "At least 4 of 5 sampled chunks read as a complete thought, with no
          sentence cut in half at either end."
       - "No chunk is shorter than 200 characters, since anything below that
          in my corpus turned out to be a heading with no content under it." -->
No chunk is a bare title line: all 10 chunks sampled with python app.py chunks -n 10 contain at least one full sentence of body text under the heading.


**Why this target:** Every doc is Title\n\nBody, so any strategy that splits on paragraph breaks strands the heading as its own useless chunk


---

## 5. Citations point at the document that actually has the fact

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. It could be about
     speed, about refusals, about a particular kind of question your corpus
     handles badly, about source attribution being correct rather than merely
     present — anything, as long as it names a number or an observable
     outcome. -->
For all 5 test questions, every source document named in the answer contains the fact the answer attributes to it. 0 of 5 answers cite a file that doesn't support the claim.

**Why this target:**
Criterion 2 only asks that a source be named, and on this corpus that's clearable while still being wrong. Seven residence halls have laundry posts identical except for the price, and seven dining halls identical except for the wait times, so an answer saying "$1.50, coin only" while citing housing_innisfree_hall_laundry.txt passes criterion 2 and is still misinformation.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     WEEK 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in week 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->


---

# Capstone acceptance criteria

Five criteria for the capstone extension — the failure handling and the
instrumentation — written before any of them was run.

The five above are the retrieval project's and stay as they are. These are
numbered 1 to 5 again because they are a separate set about a separate piece of
work.

Four of the five are about the extension rather than the system it extends,
and criterion 1 is about the bad path. I have deliberately picked targets whose
answers I do not already know: three of the nine failure reason codes have been
produced on demand and the rest have not, the logger has never been run
concurrently, and the latency numbers I have include a cold start.

---

## 1. Every failure I can inject is named, and none of them reaches the reader as a traceback

I can deliberately trigger six failure modes: no key set, a key the service
rejects, a timeout, an unreachable host, a request the service considers
malformed, and a model response with no text in it. For each of the six, the
system must return the unavailable message, record a reason code from the
closed set in `failures.py` that is **not** `unknown`, and show the reader no
traceback.

**Target: 6 of 6, in each of three trials.**

**Why this target:** 6 of 6 rather than 5 of 6 because `unknown` is not a
near-miss, it is the category that exists to be empty. The clean-clone test in
Milestone 3 already caught one mode landing in `unknown` — a missing key — and
the only reason I found it was that I happened to run from a fresh checkout. A
reason code is the one field in the log that tells me what to go and fix; a log
of `unknown` tells me only that something broke, which I already knew from the
absence of an answer. I have produced three of these six on demand. The other
three I have never triggered, which is the point of putting all six in the
target rather than the three I am confident about.

---

## 2. No request is missing from the log, even when they arrive at once

With `serve.py` running, 30 POST `/ask` requests sent concurrently must produce
exactly 30 `event: "request"` records in `logs/guide.jsonl`, every one of them
parseable as JSON on its own line.

**Target: 30 of 30 records, 0 unparseable lines, in each of three trials.**

**Why this target:** this is the criterion I expect to be hardest, and it is
the reason instrumentation is worth having at all. A log that drops records
under load is worse than no log, because it produces a number that looks like a
measurement and is not — I would read "28 requests" and have no way of knowing
whether two were lost or two never happened. Flask serves requests on separate
threads, `observability.py::log_event` takes a lock around the append, and I
have never tested that under contention. Interleaved half-lines are the
specific failure: one corrupted line breaks every later read of the file, so
the cost of being wrong here is not one lost row but the whole log after it.
0 unparseable rather than "few" because a corrupted line has no acceptable
quantity.

---

## 3. A warm server answers within 2 seconds, 95% of the time

With `serve.py` already up and having served at least one request, the
end-to-end latency recorded in `latency_ms` for answered requests must have a
95th percentile under 2,000 ms, measured over 30 requests.

**Target: p95 under 2,000 ms, in each of three trials.**

**Why this target:** 2,000 ms because my own measurements say a median request
is 703 ms and that roughly 100% of it is the one network call — so a request
taking three times the median means the service was slow, not that my code was.
I am excluding the cold start deliberately and saying so: the first call of a
process took 2,532 ms because it loads the embedding model, and a number that
includes it would describe a situation that happens once per deployment rather
than once per request. p95 rather than mean because one slow call should not
be able to hide behind nine fast ones, and rather than max because a single
outlier from the far end of someone else's network is not a fact about my
system.

---

## 4. The cost of a run is reproducible to within 10%

A run of all five test questions through `tools/measure_cost.py`, with caching
off, must report a total token count within 10% of 2,238 — that is, between
2,014 and 2,462 — on each of three trials.

**Target: 3 of 3 trials inside the band.**

**Why this target:** a cost figure that moves by more than a tenth between runs
is not a figure I can put in a README and defend. Input tokens are near enough
fixed — the same five questions retrieve the same three chunks each — so
essentially all the movement is in the output, which was 248 tokens across one
run and is the model choosing how long to be. I measured 19 output tokens on
the shuttle question and 87 on the withdrawal question, so the spread within a
single run is already more than fourfold, and whether that averages out across
five questions is exactly what I do not know. 10% rather than 5% because I am
measuring a generative system and some variance is the system working
correctly; 10% rather than 25% because at 25% the number stops being worth
quoting.

---

## 5. Someone who is not me can run this from a clean clone

Cloning this repository into an empty folder and following the capstone section
of `RUNNING.md` exactly, with no step taken that is not written down, must
reach a successful `POST /ask` that returns a 200 with an answer.

**Target: 3 of 3 attempts, each from a newly cloned folder.**

**Why this target:** 3 of 3 and not 2 of 3 because an instruction that works
two times out of three is not an instruction, it is a coincidence. This already
failed once: the first clean-clone attempt in Milestone 3 found that my
documented command assumed a virtual environment and a `.env` that a fresh
checkout does not have, and I rewrote `RUNNING.md` around what it found. What I
do not know is whether fixing the thing I tripped over exposed something behind
it. Repeating it from scratch three times is the cheapest way to find out, and
"it worked on the machine that already had everything" is the exact failure
this criterion exists to catch.

---

## Self-check

Each of the five, against the question "could someone test this from the
sentence alone, and could it fail?"

| # | Names a number | Could fail | Measurable twice the same way | What makes it fail |
|---|---|---|---|---|
| 1 | 6 of 6, three trials | Yes — 3 of 6 modes never triggered | Yes, reason codes are a closed set | A mode classifying as `unknown` |
| 2 | 30 of 30, 0 corrupt | Yes — never run concurrently | Yes, count lines and parse them | A dropped or interleaved line |
| 3 | p95 under 2,000 ms | Yes — my p95 so far is 2,094 ms | Yes, `latency_ms` is in the log | A slow service, or my own overhead |
| 4 | within 10% of 2,238 | Yes — output varies fourfold per question | Yes, token counts come off the response | Output length drifting between runs |
| 5 | 3 of 3 clean clones | Yes — it failed once already | Yes, either `/ask` returns 200 or it does not | An undocumented step |

None of the five is satisfied by construction. Criterion 3 is the one I am
least sure is fair rather than merely hard: the p95 I have measured is 2,094 ms
and the target is 2,000 ms, so I am setting it just under a number I have
already seen. That is deliberate — it includes a cold start I am now excluding,
so the question is whether removing it is worth the 94 ms, and I would rather
find out than pick 2,500 ms and be told nothing.
