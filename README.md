# The Unofficial Guide

Fienna Angeline — corpus: `campus_life`

> **This file is your submission.** Fill it in as you go — most sections get
> written during the milestone that produces them, not at the end.
>
> How the starter works, and every command you'll need, is in `RUNNING.md`.
> Leave that file alone.
>
> **Paste everything as text.** No screenshots, no video. A typed table gets
> full credit; a picture of the same table gets none, because the grader can't
> read it.
>
> Delete these instruction blocks as you replace them. The `<!-- -->` comments
> are notes to you and don't show up when the page renders — you can leave them
> or remove them.

---

# Week 1

## What This Does

The corpus is `campus_life`: 88 short posts written by students about a
fictional campus — residence halls, dining halls, courses, and registrar
deadlines. It is the unofficial kind of knowledge, the things students tell
each other rather than anything on the university website. The system answers
specific factual questions from those posts — what laundry costs in a given
hall, when the withdrawal deadline falls, how long the lunch queue runs — and
names the document each answer came from. When the posts do not cover a
question, a relevance gate stops it before the model runs and the system says
it does not have enough information instead of guessing.

## Chunking Strategy

- **Chunk size:** 500 characters — a ceiling, not a stride
- **Overlap:** 0
- **Minimum chunk:** 150 characters

I read the documents before picking these. They are short: 178 to 549
characters, and every single one is a title line followed by one to four
paragraphs. That made a fixed character window the wrong tool in both
directions. The starter's 800-character window produced 88 chunks from 88
documents — it never split anything at all. Dropping the window to 500 made it
worse rather than better: 90 chunks, the shortest of them 16 characters,
because a fixed stride slices a fragment off the tail of any document that
does not divide evenly.

So I split on paragraph breaks instead and kept 500 only as a ceiling for the
rare paragraph that runs long. Two problems fell out of that. Short paragraphs
cannot answer anything alone — "The good: the most characterful building on
campus" is 80 characters and tells you nothing on its own — so anything under
150 characters merges forward into the next paragraph. And a bare paragraph
loses track of which building it is about, so the title is repeated at the top
of every chunk. That is what keeps "$1.50" attached to "Old Brewhouse" instead
of floating loose among seven near-identical laundry posts.

Result: 88 documents became 103 chunks, 275 characters on average, shortest
174, longest 422. The 15 documents that split are exactly the ones that bundled
separate topics into a single post — all seven residence-hall overviews, seven
course overviews, and the shuttle document.

## Sample Chunks

Produced by `chunker.py::split_documents`. Chunks 4 and 5 are the two halves of
one document, included to show the paragraph split actually happening.

**Chunk 1** — source: `admin_add_drop_deadline.txt#0` — produced by: `chunker.py::split_documents`

```
On the add/drop deadline

You can add a course through the end of the second week. Dropping is a longer window — through the end of week six — but a drop after week two shows as a W on your transcript. Nothing anywhere on the registrar's site says this plainly, and students find out from each other.
```

**Chunk 2** — source: `course_biol_160_workload.txt#0` — produced by: `chunker.py::split_documents`

```
Workload for BIOL 160 Cell Biology

People keep asking so: 9 to 11 hours a week, the heaviest first-year course by reputation. That's real time, not optimistic time.

It's front-loaded — the first month is heavier than the rest, partly because you're learning the format.
```

**Chunk 3** — source: `course_math_220.txt#0` — produced by: `chunker.py::split_documents`

```
MATH 220 Linear Algebra

I lived here my sophomore year. Format is chalk-and-talk lecture, weekly problem sets marked for correctness. Assessment: two midterms and a cumulative final. Curved to a b- median.
```

**Chunk 4** — source: `housing_old_brewhouse.txt#0` — produced by: `chunker.py::split_documents`

```
Old Brewhouse — what it's actually like

Took this last spring. Built 1902 as a brewery, converted to housing in 1998. Rooms are doubles and triples with unusual floor plans, no two alike.

The good: the most characterful building on campus and people get attached to it.
```

**Chunk 5** — source: `housing_old_brewhouse.txt#1` — produced by: `chunker.py::split_documents`

```
Old Brewhouse — what it's actually like

The bad: the heating is uneven — some rooms run hot all winter and can't be adjusted.

Laundry costs $1.50 wash, $1.50 dry, coin only, and the machines are old. On noise: sound carries strangely because of the original brick; a room two floors up can be louder than next door.
```

## Sample Answer

**Question:** What does a wash and dry cost in Old Brewhouse, and how do the
machines take payment?

**Answer:**

```
  (best distance 0.240, cutoff 0.55)

In Old Brewhouse, a wash costs $1.50 and a dry costs $1.50, and the machines
take coin only (housing_old_brewhouse.txt and housing_old_brewhouse_laundry.txt).

Sources retrieved: housing_calder_annexe.txt, housing_calder_annexe_laundry.txt,
housing_fenwick_court_laundry.txt, housing_old_brewhouse.txt,
housing_old_brewhouse_laundry.txt
```

I picked this question because it is the one I expected to fail. Three of the
five retrieved chunks are the *wrong* building's laundry post — Calder Annexe
and Fenwick Court both came back, because those posts are word-for-word
identical to Old Brewhouse's except for the price and the payment method. The
answer still cited only the two Old Brewhouse files.

**My relevance cutoff:**

<!-- The number you set in config.py, and how you got there.

     You ran five questions your corpus covers and the five in OUT_OF_SCOPE
     that it clearly doesn't, and wrote down the best distance for each. What
     did those two groups look like? Where was the gap? Put the actual numbers
     here — the table below wants all ten rows.

     Milestone 4. -->

0.55, set in config.py. I measured the best distance for each of my five test questions and each of the five OUT_OF_SCOPE questions:
In corpus (5) - 0.180, 0.198, 0.206, 0.240, 0.243
Out of scope (5) - 0.825, 0.844, 0.877, 0.886, 0.934
The two groups don't overlap. There's a gap from 0.243 to 0.825 with nothing in it. 0.55 is roughly the midpoint. The starter's default of 0.6 also falls inside the gap, so it would have worked, but 0.55 is the number my own corpus gave me rather than the one I was handed.

The closest call in the in-corpus group was the Old Brewhouse laundry question: its top two chunks came back at 0.240 and 0.246, nearly tied, which is the seven near-identical laundry posts competing with each other. It still returned the right one.

## How I Used AI

<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

**1. Summarising the milestones.** The project pages are long, so I pasted
them into Claude and asked for a short version plus a step-by-step list, then
asked follow-up questions where the wording was unclear - for example whether
Milestone 1 was the setup step or the run-it-once step. It was the run-it-once
step; I had them confused. I used it as a reference while working rather than
copying the summary anywhere.

**2. Writing the chunker from my strategy.** I decided the strategy myself -
split on paragraph breaks, repeat the title on each chunk, merge short
paragraphs forward - and asked Claude to turn it into Python. Pasting it in
went wrong twice: the first time the tail of the function was missing so it
still called `fallback_split`, and the second time the loop body vanished and
`split_documents` returned `None`, which showed up as "0 chunks". I found both
by running `python chunker.py` and reading the number, which is the habit that
actually mattered - the summary line tells you immediately whether the chunker
ran at all.

**3. Week 2: finding the pattern in my results.** Every criterion passed, which
left me with nothing to diagnose. I asked for help working out what my test had
missed rather than what it had found, and the useful move was counting how many
on-topic chunks exist in the corpus at all - 11, across five questions, against
a `top_k` of 5. That reframed the problem from "retrieval is confused by
near-duplicates" to "retrieval is being asked for more rows than there is
material", which is what the fix follows from. I also had it argue against my
own conclusion that hybrid search would help; the counter-argument was that RRF
only sees ranks, and checking that turned out to be correct.

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Week 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     week 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

Produced by `run_eval.py::main`, raw log in
`results/run_2026-11-08_1958_before.md`. Retrieval `store.py::search`, chunks
from `chunker.py::split_documents`. top-k 5, cutoff 0.55, caching off.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. No chunk is a bare title line | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 5. Citations point at the right document | 0 of 5 wrong | 0 wrong | 0 wrong | 0 wrong | MET |

Criteria 3 and 4 give the same number in all three columns on purpose.
Retrieval and the gate are deterministic, and chunking does not depend on the
run at all - there is one measurement and it goes in every column. Criteria 1,
2 and 5 depend on the generated answer and could have moved. They did not.

**Criterion 1** - real output, question 3, run 1. The answer chunk
`housing_old_brewhouse_laundry.txt#0` came back at distance 0.246:

```
Laundry in Old Brewhouse

Machines take $1.50 wash, $1.50 dry, coin only, and the machines are old. There
are eight washers and six dryers for the building, which is the wrong ratio and
means the dryers back up on Sunday evenings.
```

**Criterion 2** - real output, question 5, run 2. Produced by
`generate.py::answer_from_chunks`:

```
The campus shuttle runs every 40 minutes on weekends (transit_shuttle.txt).
```

**Criterion 3** - real output from `run_eval.py::check_out_of_scope`, cutoff
0.55, no model calls made:

```
| What is the capital of Mongolia?                            | 0.825 | refused |
| How do I change the oil in a diesel engine?                 | 0.934 | refused |
| Who won the 1994 World Cup?                                 | 0.886 | refused |
| What is the recommended dosage of ibuprofen for a headache? | 0.844 | refused |
| How do I write a for loop in Rust?                          | 0.877 | refused |
-> gate refused 5 of 5
```

**Criterion 4** - `chunker.py::split_documents` over all 103 chunks, not just
the 10 sampled:

```
total chunks: 103
chunks with no full sentence of body text: 0
shortest 174  longest 422  avg 275
```

**Criterion 5** - real output, question 4, run 1. Both cited files were opened
and checked; `admin_withdrawal_deadline.txt` contains "week ten" and
`admin_add_drop_deadline.txt` contains the week-two W rule:

```
The withdrawal deadline runs to week ten, whereas dropping a course ends at
week six (*admin_withdrawal_deadline.txt* and *admin_add_drop_deadline.txt*).
Additionally, withdrawing requires an adviser signature and places a "W" on the
transcript that does not affect GPA, while dropping a course after week two
also shows as a "W" on the transcript.
```

## Verdicts

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunk contains the answer, 4 of 5 | MET | Opened the retrieved chunks for each question and checked the `expects` phrase was literally present in one of them. 5 of 5 on every run. |
| 2 | Every answer names a source, 5 of 5 | MET | All 15 generated answers name at least one `.txt` file. Not one came back bare. |
| 3 | Gate stops out-of-corpus questions, 4 of 5 | MET | `run_eval.py` put all five through the gate at cutoff 0.55. The closest was 0.825, which is not close. 5 of 5. |
| 4 | No chunk is a bare title line, 10 of 10 | MET | Checked all 103 chunks rather than the 10 I promised: every one has at least one sentence-ending mark in its body. 0 failures. |
| 5 | Citations point at the right document, 0 of 5 wrong | MET | Opened every cited file for all 15 answers and confirmed it contains the fact attributed to it. The Old Brewhouse answer cited only the two Brewhouse files even though three wrong-building posts were in its context. |

No criterion was revised. Nothing turned out to be unmeasurable, so there was
nothing to revise - and lowering a target I hit would be backwards.

## Diagnoses

**I missed nothing, and I do not think that means the system is good.** Five of
five criteria met on the first attempt, with the same numbers all three runs.
Milestone 3 asks me to say honestly whether my targets were set low. Two of
them were.

**Criterion 2 was close to free.** I said so when I wrote it - every chunk
already carries its `source` through `store.py` into the prompt, so naming one
is a formatting requirement, not a retrieval problem. A criterion that passes
because the pipeline cannot easily fail it is not measuring anything.

**Criterion 4 could not be missed given my chunker.** My documents are 178-549
characters and my chunker never emits a title without its body, so "no chunk is
a bare title line" was guaranteed by construction. I wrote it to catch a
paragraph-splitting bug I thought I might introduce, and then did not introduce
it. The honest version would have been about whether a chunk covers one topic
or several - which my chunker does still get wrong, see below.

**Criterion 3 had far more headroom than I predicted.** I guessed the ibuprofen
question would nearly slip through because `health_center.txt` is about a health
centre. It did not: its nearest match was `money_textbooks.txt` at 0.844, and
the closest out-of-scope question overall was Mongolia at 0.825. With a gap
running from 0.243 to 0.825, a 4-of-5 target was never going to bite.

**Which I would tighten, and to what.** Criterion 4, from "no chunk is a bare
title line, 10 of 10" to **"no chunk contains facts about more than one of:
price, hours, noise, wait times - 0 of 10 sampled chunks cover more than one."**
That one I would currently miss. `housing_old_brewhouse.txt#1` holds heating,
laundry cost and noise in a single chunk, because they are one paragraph in the
source and my chunker splits on paragraph breaks and nothing finer.

**The one real weakness the test found** is not a criterion at all, which is
itself a finding about my criteria. Across my five questions retrieval returns
25 chunks, and only 8 of them come from a document that bears on the question -
32% precision. For the Old Brewhouse question, three of the five retrieved
chunks are a different building's laundry post. Every one of those is noise
handed to the model as though it were evidence.

- **Stage:** retrieval.
- **Mechanism:** `top_k` is fixed at 5, but only 11 on-topic chunks exist in
  the whole corpus across all five of my questions - one of them, pass/fail,
  has exactly one. Asking for five guarantees at least 14 irrelevant chunks
  enter the prompts. The embedding is not confused; it is being made to return
  more rows than there is relevant material to fill them with.
- **Pattern:** every question shows it, and the near-duplicate families
  (7 dining halls, 7 residence halls) make it worst, because the next-closest
  chunk after the right answer is always a sibling document differing in a
  building name and a price.

## The Improvement

**What I changed:** `TOP_K` in `config.py`, from 5 to 3. One line.

**Why I picked it:** my diagnosis says retrieval returns more chunks than there
is relevant material to fill them with - 11 on-topic chunks exist across five
questions, and asking for 5 each forces 14 noise chunks into the prompts - so
asking for fewer is the change that addresses the named mechanism directly.

**What I tried first, and why it is not what I shipped.** My diagnosis pointed
at near-duplicate competition, so I built hybrid search: BM25 over the semantic
candidate pool, fused with the vector ranking (`store.py::_rerank`, `HYBRID` in
`config.py`). It changed one chunk in 25.

Measuring *why* is what produced the real fix. BM25 ranks the correct chunk
`housing_old_brewhouse.txt#0` second, where semantic search has it thirteenth -
the keyword signal is working. But reciprocal rank fusion could never promote
it, because the wrong building's laundry post out-ranks it on *both* lists, and
RRF only ever sees ranks. I switched to blending normalised scores instead,
which does keep BM25's 7.6-against-6.9 margin, and swept the weighting from
pure-semantic to pure-keyword:

| HYBRID_ALPHA | 1.0 | 0.8 | 0.6 | 0.5 | 0.4 | 0.2 | 0.0 |
|---|---|---|---|---|---|---|---|
| on-target chunks | 8/25 | 8/25 | 8/25 | 8/25 | 8/25 | 8/25 | 9/25 |

One chunk, at pure keyword. That told me the ranking was not the problem - the
number of rows was. The code is still in the repo with `HYBRID = False` so the
measurement can be reproduced, but it is not the change I am claiming.

Hybrid at `top_k` 3 measures 53% against 47% for `top_k` 3 alone. I did not
ship it, because two changes at once means I could not say which one did the
work.

### Run Log — After

Produced by `run_eval.py::main`, raw log in
`results/run_2026-11-08_2003_after.md`. Identical setup except top-k 3.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. No chunk is a bare title line | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 5. Citations point at the right document | 0 of 5 wrong | 0 wrong | 0 wrong | 0 wrong | MET |

Measured alongside the criteria, since none of them moved:

| | Before (top-k 5) | After (top-k 3) |
|---|---|---|
| On-target retrieved chunks | 8 of 25 (32%) | 7 of 15 (47%) |
| Questions where the answer chunk was retrieved | 5 of 5 | 5 of 5 |
| Input tokens, 15 answers | 8,808 | 5,970 |
| Closest out-of-scope distance | 0.825 | 0.825 |

**Did it help?**

Yes, but not in a way any of my five criteria could see, which is the most
useful thing this test told me.

Retrieval precision went from 32% to 47% and nothing was lost: all five
questions still retrieve a chunk containing the answer, all 15 answers are
still correct, all citations still point at the right file, and the gate still
refuses 5 of 5 out-of-scope questions at the same distances. Prompt cost fell
32%, from 8,808 input tokens to 5,970, because two fewer chunks go into every
prompt.

The honest caveat is that the before-and-after criteria tables are identical -
every criterion was MET before the change and MET after it. A change that
improves the system while every acceptance criterion sits unchanged at the top
of its range is evidence that the criteria were measuring the wrong thing, not
evidence that the change did nothing. If I had written criterion 4 about topic
mixing, or written a criterion about retrieval precision at all, this table
would have moved.

## What's Still Broken

No criterion is still missed, because none was missed to begin with. What is
left is the gap between that and a system I would trust.

**Chunks still mix topics.** `housing_old_brewhouse.txt#1` carries heating,
laundry cost and noise in one chunk, because the source has them in one
paragraph and `chunker.py::split_documents` splits on paragraph breaks and
nothing finer. The fix is sentence-level grouping - start a new chunk when a
sentence opens a new subject, for example at "On noise:" - and I would measure
it with the tightened criterion 4 in my Diagnoses section. I stopped because it
changes chunking, which would have invalidated the before-and-after comparison
I was in the middle of running, and the one-change-at-a-time rule cuts both
ways.

**Retrieval precision is 47%, which is not good.** More than half the material
in every prompt is still a different building or a different course. `top_k` 3
is a blunt instrument; what this corpus actually wants is a variable `top_k` -
one chunk for pass/fail, four for Old Brewhouse. A distance-gap cutoff, taking
chunks until the distance jumps, would do that. Hybrid search at `top_k` 3
measured 53% and is the cheapest next thing to try, since the code is already
written and switched off.

**Criteria 2 and 4 cannot fail.** Diagnosed above. They stay as written - the
point of writing them before the results was to be held to them - but I would
not call a run that passes them evidence of much.

**I have no `scorer.py`.** Every verdict in this document was reached by me
reading output, which means criteria 1 and 5 depend on my judgement on the day.
I checked each citation by opening the file, but I cannot prove I would score it
identically next week, and that is the same measurability problem the brief
warns about.

**My `expects` strings are brittle.** Two of them are "week eight" and "week
ten". A correct answer written as "week 8" would score as a failure. It did not
happen across 15 answers, but the scorer I have not built yet would inherit the
problem.

## What I'd Do Differently

**Criterion 4** is the one I would write differently, and I would write it about
topic mixing rather than title lines: *no chunk contains facts about more than
one of price, hours, noise, or wait times, in 0 of 10 sampled chunks.* As
written it was guaranteed by my chunker's construction. As rewritten it would
have failed, pointed straight at `housing_old_brewhouse.txt#1`, and given me a
real miss to diagnose.

**Criterion 2** I would either drop or fold into criterion 5. "Names a source"
is satisfied by string formatting; "names a source that contains the fact" is
the thing I actually care about, and I already wrote it as criterion 5. Spending
one of five criteria on the weaker version wasted it.

**I would add one criterion about retrieval precision** - something like *at
least half the retrieved chunks come from a document bearing on the question.*
The single real weakness my test found was invisible to all five of my criteria,
which is the clearest signal that I chose them badly. I wrote five criteria my
system passed and none that told me what to fix. The number that moved, 32% to
47%, is one I had to invent after the fact to see my own improvement.

**I would keep criterion 3 exactly as it is**, including the prediction I got
wrong about the ibuprofen question. Writing down which failure I expected and
then being wrong about it is the most informative thing in `criteria.md`.


---

# Capstone

## The Shape

**System:** The Unofficial Guide - the same `campus_life` retrieval system in
this repo, not a new one.

**Shape B, Path B.** I am hardening the system against failure, and running it
locally with a committed record rather than hosting it.

Right now this system only behaves well when everything goes right. The parts
that can fail have been handled unevenly: a rate limit backs off and retries, a
runaway session is stopped by `QuotaGuard`, and a missing index prints a clear
instruction. But every *other* way the model call can fail falls straight
through to a traceback. I know this from experience rather than from reading the
code - during week 1 my `.env` still held the placeholder key, and
`python app.py ask` answered with a raw `ClientError` stack trace. Retrieval and
the gate had both worked perfectly and said so, and the system still looked
broken rather than temporarily unavailable.

So the extension is this: **every failure in the generation stage returns a
readable message instead of a traceback, and every request writes one structured
log line recording what happened.**

Concretely, that means a timeout on the model call so it cannot hang, an
exception boundary that catches anything the retry logic does not already
handle, and a JSON-lines log carrying the question, the best retrieval distance,
the gate decision, the latency, the token count, and the outcome.

One decision inside that is worth naming, because it is a promise to whoever is
reading the answer. When the model call fails, the system will **not** reuse the
existing refusal, "I don't have enough information about that." That sentence is
false in this situation: for a question like the Old Brewhouse laundry one, the
documents do contain the answer and retrieval found it - the system simply could
not reach the model. Blaming the corpus for an outage is the kind of
confidently-wrong output the relevance gate exists to prevent in the first
place. A failed call gets its own distinguishable message, and the log gets its
own distinguishable outcome, so the two are never counted as the same event.

Instrumentation is not part of my one-thing budget. The unit requires a run path
and a log whichever shape is picked, so it comes alongside the hardening rather
than instead of something else.


## What's in results/

Three run logs, and one of them is not what it looks like.

| File | What it is |
|---|---|
| `run_2026-11-08_1958_before.md` | The real test, top-k 5, before last unit's fix |
| `run_2026-11-08_2003_after.md` | The real test, top-k 3, after it |
| `run_2026-11-08_2033_failtest.md` | **Not a test of the system's answers.** A deliberate failure injection |

The third one was produced by running the evaluation with a key I knew was
invalid:

```bash
GEMINI_API_KEY="AIzaBogus..." python run_eval.py --runs 1 --label failtest
```

Every question in it reads `FAILED (auth)`, and that is the result I wanted.
Before the capstone work, the first failed call raised through `run_eval.py`
and killed the whole run — the questions already answered were lost along with
the quota they cost, and no file was written at all. Now the run completes,
each failed attempt is recorded with its reason, and a failed run scores as
neither pass nor fail, so an outage is never counted as the system giving a
wrong answer.

So that file is evidence about the hardening, not evidence about the retrieval.
Nothing in it should be read as a verdict on any of my five acceptance
criteria, and it is one run rather than three because it was not measuring
anything that varies.

## Out of Scope

Three things I considered and am deliberately not doing.

**Not turning hybrid search back on.** The code is already written and sitting
in `store.py::_rerank` behind `HYBRID = False`, and I measured it at 53%
retrieval precision against 47% for what ships. Turning on a flag is a one-line
change and genuinely tempting. It is still out, because it would change what the
system retrieves at the same time as I am changing how it fails, and I would not
be able to tell which one moved the numbers. This is the same reason I did not
ship it last unit.

**Not touching chunking.** I know `chunker.py::split_documents` still produces
chunks that mix topics - `housing_old_brewhouse.txt#1` carries heating, laundry
cost and noise together - and I wrote in the last unit that I would tighten
criterion 4 to catch exactly that. Fixing it means re-indexing, which invalidates
every distance I have measured, including the 0.55 cutoff. That is a chunking
unit of work, not a failure-handling one.

**Not hosting it.** Path B, and for a specific reason rather than as a hedge:
this system loads `all-MiniLM-L6-v2` locally, about 80 MB of model plus its
runtime, and the free hosting tier offers 512 MB of memory. Embedding on my own
machine is a design choice in this project - it is why the system costs no API
quota to retrieve - and it is not compatible with that tier. The run record and
the documented single command do the same job here that a URL would.

**Scope check.** Two pieces of work: the failure handling, and the logging. The
second is required by the unit regardless of shape, so there is one thing I
chose. Anything that re-indexes, re-ranks, or changes what the system retrieves
is out.
