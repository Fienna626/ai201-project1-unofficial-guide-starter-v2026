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
