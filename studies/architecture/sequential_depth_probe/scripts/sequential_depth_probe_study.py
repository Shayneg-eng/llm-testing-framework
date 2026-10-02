import os
"""
S.H.A.Y.N.E. -- Sequential Depth Probe
========================================
Research question: in a SINGLE forward pass (zero-shot, first-token-only answer,
no chain-of-thought), what is the longest chain of strictly serial pointer
hops a model can track correctly? Because a transformer's ability to compose
N sequential, data-dependent lookups within one forward pass is bounded by
the number of layers it can dedicate to that computation, the step length L
at which accuracy collapses from ~100% to chance (25%, four possible nodes)
is an empirical proxy for an upper bound on the model's effective sequential
(serial) computational depth on this kind of task.

Task (deliberately as simple as possible -- see 2026-09-25 redesign note
below): pointer chasing over a FIXED 4-node lookup table. There is no
separate "state" variable and no arithmetic beyond following the table:

    0 -> 1
    1 -> 3
    2 -> 0
    3 -> 2

(a single 4-cycle: 0 -> 1 -> 3 -> 2 -> 0 -> ...). Starting from a given node,
apply the rule (look up the next node) L times in a row; the only way to get
the right answer is to actually hop through the chain L times -- that serial
dependency is the entire point of the probe.

2026-09-25 REDESIGN NOTE: the original version of this task used a 4-node
state machine with a separate mod-8 "state" value, XOR/multiply transition
functions, and per-node "Value" constants (see git history / project docs for
the old design if needed). That was scrapped after it produced results that
were impossible to interpret cleanly: GPT-OSS-120B did fine with it, but a
plain 70B non-reasoning model returned the exact same constant digit
regardless of the actual input on that version of the task, even though a
sanity check confirmed the model/API call worked correctly on ordinary
questions. Rather than trying to disentangle "genuinely can't do this" from
"prompt too complicated to track," the task itself was simplified down to a
bare lookup table so a wrong answer is much more likely to reflect an actual
depth limit rather than confusion about the rules.

The model is given the rule table and a (start_node, L) pair and instructed
to output ONLY the final node as its entire response -- no reasoning tokens,
so it cannot use the visible context window as external scratch space to
bypass the single-forward-pass depth limit.

IMPORTANT ARCHITECTURAL CAVEAT (added after the first run, still applies):
GPT-OSS-120B is an
open-weight reasoning model trained via RL to always produce a chain-of-thought
before answering -- this is not a stylistic choice it can be prompted out of.
A first pass at this script used max_tokens=6 to try to force a literal
single-token answer, and got back an EMPTY response on every trial at every
step length, including the trivial L=1 case -- the model was being cut off
mid-reasoning, not genuinely failing the task. There is no way to fully
disable gpt-oss's internal reasoning via the API; the closest official lever
is the `reasoning_effort` request parameter, which this script sets to "low"
(see USE_REASONING_EFFORT constant below) -- this does not eliminate
chain-of-thought, it just discourages deep multi-step reasoning, giving a
shorter (but still real) internal trace. Two consequences for how to read this
study's results:
  1. max_tokens is now generous (see MAX_TOKENS) so the model can actually
     finish reasoning and emit a visible answer; grading still only looks at
     the FIRST digit character in whatever comes back, so the "answer is a
     single character" rule from the original design is preserved even though
     the generation budget is not minimal.
  2. The resulting depth estimate should be described as "effective serial
     depth under low reasoning effort," not a literal single-forward-pass
     bound -- if gpt-oss's reasoning tokens are visible free-form text (rather
     than a hidden channel never exposed to grading), the model may be using
     them as an external scratchpad to walk the chain by hand, which is a
     genuinely different (and much less interesting) capability than doing it
     in one forward pass. Check `finish_reason` and `reasoning_trace` on a
     sample of trials (both are saved per-trial) to see which case applies
     before treating any collapse point as an architectural depth bound.

Method:
  - Step lengths L = 1..40.
  - 5 trials per L, each with an independently randomized start_node in [0, 3].
  - Ground truth computed programmatically (never by the model).
  - Model's answer = first character in its reply that is one of '0','1','2','3'.
  - Early stop: two consecutive step lengths both at or below 25% accuracy
    (random-guess floor for 4 choices).
  - Report: per-L accuracy table + an estimated upper bound on effective
    sequential depth, taken as the highest L with accuracy >= ROBUST_THRESHOLD
    (80%, i.e. >=4/5 correct) before the first sub-threshold L. This is a
    behavioral estimate, not a literal layer count -- see caveats printed at
    the end.

Run: python sequential_depth_probe_study.py [--model MODEL_NAME] [--chunk-size N]
     (--model defaults to GPT-OSS-120B-CS; multiple models can be probed by
     re-running with a different --model, each tagged separately below)
Output: runs/trial_L<LL>_rep<N>_<model_slug>.json (one per call)
        runs/sequential_depth_probe_summary_<model_slug>.json (aggregate)
"""

import argparse
import json
import random
import re
import time
from pathlib import Path

import openai

# ---------------------------------------------------------------------------
# HARDCODED FOR TESTING (per project instructions) -- rotate this key before
# sharing this file anywhere outside your own machine.
# ---------------------------------------------------------------------------
POE_API_KEY = os.getenv("POE_API_KEY", "")
POE_BASE_URL = "https://api.poe.com/v1"

client = openai.OpenAI(api_key=POE_API_KEY, base_url=POE_BASE_URL)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
# MODEL is a module-level global so call_model() (and everything downstream)
# can see it without threading it through every function; main() overwrites
# it from --model before anything runs. The default keeps `python
# sequential_depth_probe_study.py` with no args working exactly as the first
# run did.
DEFAULT_MODEL = "GPT-OSS-120B-CS"
MODEL = DEFAULT_MODEL
MIN_STEPS = 1
MAX_STEPS = 40
REPS_PER_STEP = 5
RANDOM_SEED = 20260924  # fixed for reproducibility of trial generation
CHANCE_ACCURACY = 0.25
EARLY_STOP_STREAK = 2          # consecutive step lengths at/below chance
ROBUST_THRESHOLD = 0.80        # >=4/5 correct counts as "robust" for the depth estimate
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 3
CALL_SLEEP_SECONDS = 0.5       # small delay between calls to stay polite to rate limits

# GPT-OSS-120B is an open-weight REASONING model: even when told not to show its
# work, it appears to consume part of its generation budget on internal
# reasoning tokens before emitting the visible answer digit. A first pass at
# this script used max_tokens=6 (to force a near-literal "first token only"
# answer) and got back an EMPTY content string on every single trial, at every
# step length including L=1 -- i.e. the model was being cut off before it ever
# produced visible output, not genuinely failing the task. max_tokens is set
# generously here so the model can finish; grading still only looks at the
# FIRST digit character anywhere in whatever content comes back (see
# extract_first_digit_answer), so the "answer is a single character" grading
# rule is preserved even though the generation budget is not minimal.
#
# Caveat this creates for interpretation: if this model's reasoning tokens are
# visible chain-of-thought rather than a hidden/internal channel, then a
# nonzero max_tokens headroom gives it a text scratchpad to work the chain by
# hand -- which is a different (and much less interesting) capability than
# "can it do this in a single forward pass." Check finish_reason and the raw
# response text on a few trials (both fields are saved per-trial) before
# treating any accuracy-collapse point from this run as a genuine
# forward-pass-depth bound rather than a reasoning-budget effect.
MAX_TOKENS = 2048

# gpt-oss cannot be prompted into fully skipping its chain-of-thought -- it was
# RL-trained to always reason before answering, so "no chain-of-thought" is not
# achievable via system prompt alone (confirmed against OpenAI's own gpt-oss
# release notes and HF model-card discussions, 2026-09-24). The closest
# supported lever is the OpenAI-standard `reasoning_effort` request parameter
# ("low" / "medium" / "high"), which discourages deep multi-step reasoning and
# shortens (but does not eliminate) the internal trace. Poe's OpenAI-compatible
# endpoint may or may not forward this to the underlying model -- call_model()
# tries it via `extra_body` and transparently falls back to omitting it (once,
# for the rest of the run) if the API rejects the parameter, so this script
# runs either way; check the console output for a one-time warning if the
# fallback triggers, since that means every trial ran at the model's default
# reasoning effort instead of "low".
USE_REASONING_EFFORT = True
REASONING_EFFORT_VALUE = "low"

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "runs"


def model_slug(model):
    """Filesystem-safe tag for a model name, e.g. 'GPT-OSS-120B-CS' ->
    'gpt_oss_120b_cs'. Multiple models share runs/ (one
    study, per ORGANIZATION.md), so every per-model file -- trial JSON and
    summary JSON alike -- is tagged with this slug to keep separate models'
    data (and separate resumable run state) from colliding or overwriting
    each other."""
    return re.sub(r"[^a-z0-9]+", "_", model.lower()).strip("_")

# ---------------------------------------------------------------------------
# Pointer-chasing rule (ground truth, computed in Python only)
#
# Deliberately as simple as it can be while still forcing L genuine serial
# hops: a single fixed lookup table, no separate "state" variable, no
# arithmetic. See the 2026-09-25 redesign note in the module docstring for why
# the earlier XOR/mod-8 version was scrapped.
# ---------------------------------------------------------------------------
NEXT_NODE = {0: 1, 1: 3, 2: 0, 3: 2}  # a single 4-cycle: 0 -> 1 -> 3 -> 2 -> 0 -> ...


def simulate(start_node, num_steps):
    """Returns the final node after num_steps hops, plus the full trace."""
    node = start_node
    trace = [node]
    for _ in range(num_steps):
        node = NEXT_NODE[node]
        trace.append(node)
    return node, trace


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You follow a simple lookup-table rule step by step and report where you "
    "end up. Work it out yourself, then reply with ONLY the final node number "
    "(0, 1, 2, or 3) -- no words, no explanation, no punctuation, nothing else "
    "in your response."
)

RULES_TEXT = """Rule (always apply this same lookup table):
  0 -> 1
  1 -> 3
  2 -> 0
  3 -> 2"""


def build_user_prompt(start_node, num_steps):
    return (
        f"{RULES_TEXT}\n\n"
        f"Start at node {start_node}. Apply the rule {num_steps} time(s) in a "
        f"row (each time, look up the next node). What node do you end at?\n\n"
        f"Reply with ONLY that node's number and nothing else."
    )


# ---------------------------------------------------------------------------
# Model call
# ---------------------------------------------------------------------------
# Mutable run-level state: flips to False the first time the API rejects the
# reasoning_effort parameter, so we stop trying it (and stop paying an extra
# failed round-trip) for every subsequent call in this run. Printed once when
# it happens so it's visible in the run log and in any output that quotes it.
_reasoning_effort_supported = USE_REASONING_EFFORT


def call_model(user_prompt, system_prompt=None):
    global _reasoning_effort_supported
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        extra_body = (
            {"reasoning_effort": REASONING_EFFORT_VALUE}
            if _reasoning_effort_supported else None
        )
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=0,
                **({"extra_body": extra_body} if extra_body else {}),
            )
            choice = resp.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason
            # Some reasoning-model deployments expose the hidden reasoning
            # trace as a separate field (commonly `reasoning` or
            # `reasoning_content`) alongside `content`. Capture it if present
            # so a stray empty `content` can be diagnosed later without
            # needing to re-run the call.
            reasoning_trace = (
                getattr(choice.message, "reasoning_content", None)
                or getattr(choice.message, "reasoning", None)
            )
            if not content:
                print(f"    [warn] empty content (finish_reason={finish_reason}); "
                      f"reasoning_trace_present={bool(reasoning_trace)}")
            return content, None, finish_reason, reasoning_trace, extra_body is not None
        except Exception as exc:  # noqa: BLE001 -- deliberately broad, this is a probe script
            last_err = str(exc)
            # If reasoning_effort itself is what the API rejected (a 400 / bad
            # request naming the parameter, as opposed to a network or rate
            # limit error), disable it for the rest of the run and retry this
            # same trial immediately -- no need to burn a backoff sleep on a
            # request we know will fail again unchanged.
            if extra_body is not None and (
                "reasoning_effort" in last_err.lower() or "400" in last_err
                or "unrecognized" in last_err.lower() or "unknown parameter" in last_err.lower()
            ):
                _reasoning_effort_supported = False
                print(f"    [warn] reasoning_effort parameter rejected by API "
                      f"({last_err}); disabling it for the rest of this run.")
                continue
            sleep_for = RETRY_BACKOFF_SECONDS * attempt
            print(f"    [warn] call failed (attempt {attempt}/{MAX_RETRIES}): {last_err}"
                  f" -- retrying in {sleep_for}s")
            time.sleep(sleep_for)
    return None, last_err, None, None, _reasoning_effort_supported


def extract_first_digit_answer(raw_text):
    if not raw_text:
        return None
    for ch in raw_text.strip():
        if ch in "0123":
            return int(ch)
    return None


# ---------------------------------------------------------------------------
# Resumable summary I/O
#
# This script is designed to be invoked repeatedly (e.g. from a shell with a
# hard wall-clock limit per invocation) and pick up where it left off: it
# reloads this model's sequential_depth_probe_summary_<model_slug>.json if
# present, skips any step lengths already completed, and re-derives the
# early-stop streak from the loaded results so stopping behaves identically to
# one uninterrupted run. The filename is tagged per-model so running a second
# model doesn't resume (or overwrite) the first model's saved progress.
# ---------------------------------------------------------------------------
def summary_path_for(model):
    return OUTPUT_DIR / f"sequential_depth_probe_summary_{model_slug(model)}.json"


def load_existing_summary():
    path = summary_path_for(MODEL)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def recompute_streak(per_length_results):
    streak = 0
    for row in per_length_results:
        if row["at_or_below_chance"]:
            streak += 1
        else:
            streak = 0
    return streak


def write_summary(per_length_results, stopped_early, stop_reason, robust_upper_bound):
    summary = {
        "study": "sequential_depth_probe",
        "model": MODEL,
        "min_steps": MIN_STEPS,
        "max_steps_configured": MAX_STEPS,
        "reps_per_step": REPS_PER_STEP,
        "random_seed": RANDOM_SEED,
        "chance_accuracy": CHANCE_ACCURACY,
        "early_stop_streak": EARLY_STOP_STREAK,
        "robust_threshold": ROBUST_THRESHOLD,
        "stopped_early": stopped_early,
        "stop_reason": stop_reason,
        "per_length_results": per_length_results,
        "estimated_robust_upper_bound_length": robust_upper_bound,
        "complete": stopped_early or (
            bool(per_length_results) and per_length_results[-1]["length"] >= MAX_STEPS
        ),
    }
    summary_path_for(MODEL).write_text(json.dumps(summary, indent=2))
    return summary


def print_summary_table(per_length_results):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Step Length':>11} | {'Correct/Total':>13} | {'Accuracy':>9} | {'<=25% thresh met':>16}")
    print("-" * 60)
    for row in per_length_results:
        print(f"{row['length']:>11} | {row['correct']:>2}/{row['total']:<10} | "
              f"{row['accuracy']*100:>8.1f}% | {'YES' if row['at_or_below_chance'] else 'no':>16}")


def compute_robust_upper_bound(per_length_results):
    robust_upper_bound = 0
    for row in per_length_results:
        if row["accuracy"] >= ROBUST_THRESHOLD:
            robust_upper_bound = row["length"]
        else:
            break
    return robust_upper_bound


def print_depth_estimate(robust_upper_bound, stopped_early, stop_reason, per_length_results):
    print("\n" + "=" * 60)
    print(f"ESTIMATED UPPER BOUND ON EFFECTIVE SEQUENTIAL DEPTH -- {MODEL}")
    print("=" * 60)
    if robust_upper_bound > 0:
        print(f"Highest step length with accuracy >= {ROBUST_THRESHOLD:.0%} "
              f"(robust) before the first drop below it: L = {robust_upper_bound}")
    else:
        print("No step length reached the robust accuracy threshold "
              f"(>= {ROBUST_THRESHOLD:.0%}) -- even L={MIN_STEPS} was not robust.")
    print(
        f"\nCaveat: whether this is a literal single-forward-pass bound depends "
        f"on whether {MODEL} performs any internal chain-of-thought reasoning "
        f"before answering. Known reasoning-family models (e.g. the gpt-oss "
        f"line) cannot be prompted into fully suppressing that reasoning -- "
        f"the closest available lever is the reasoning_effort='low' request "
        f"parameter this script sends (see reasoning_effort_requested per "
        f"trial), which shortens but does not eliminate the trace. For a "
        f"model with no internal reasoning step at all, this number is a much "
        f"more direct read on architectural forward-pass depth. Either way, "
        f"check finish_reason / reasoning_trace in the per-trial JSON before "
        f"treating this as an architectural fact rather than a task-specific "
        f"behavioral estimate."
    )
    if stopped_early:
        print(f"\nNote: run stopped early at L={per_length_results[-1]['length']} "
              f"({stop_reason}); step lengths above this were not tested.")


# ---------------------------------------------------------------------------
# Sanity check: is the model engaging with the actual prompt at all?
#
# Triggered by --sanity-check. Sends a handful of trivial, mutually distinct
# arithmetic questions that have nothing to do with the state-machine task --
# if a model returns the SAME digit for genuinely different questions here,
# that's strong evidence of a broken/echoed/cached response at the API or
# bot-configuration level, not a real capability limit on the depth-probe
# task itself. Run this before trusting a depth-probe result where every
# trial at some length came back with an identical answer regardless of the
# actual start_node.
# ---------------------------------------------------------------------------
SANITY_CHECK_QUESTIONS = [
    ("What is 2 + 2? Reply with ONLY the number, nothing else.", "4"),
    ("What is 9 - 6? Reply with ONLY the number, nothing else.", "3"),
    ("What is 5 + 5? Reply with ONLY the number, nothing else.", "10"),
    ("What color is the sky on a clear day? Reply with ONLY one word.", "blue"),
]


def run_sanity_check():
    print(f"Sanity check -- model={MODEL}, reasoning_effort={'low' if _reasoning_effort_supported else 'not sent'}\n")
    print("Sending trivial, mutually distinct questions with NOTHING to do with "
          "the state-machine task. If every answer comes back identical or "
          "unrelated to its own question, the model/API call is broken or "
          "echoing a fixed response -- the depth-probe results for this model "
          "should not be trusted until that's fixed.\n")
    neutral_system_prompt = (
        "You are a helpful assistant. Answer concisely and exactly as instructed "
        "in each question."
    )
    all_distinct = set()
    for question, expected in SANITY_CHECK_QUESTIONS:
        raw_text, error, finish_reason, reasoning_trace, effort_used = call_model(
            question, system_prompt=neutral_system_prompt
        )
        all_distinct.add(raw_text)
        status = "OK" if raw_text and expected.lower() in raw_text.lower() else "UNEXPECTED"
        print(f"  Q: {question}")
        print(f"  Expected (roughly): {expected!r}  |  Got: {raw_text!r}  |  "
              f"finish_reason={finish_reason}  |  [{status}]")
        print(f"  reasoning_trace: {reasoning_trace!r}\n")
        time.sleep(CALL_SLEEP_SECONDS)
    if len(all_distinct) == 1:
        print("WARNING: every response was IDENTICAL across completely different "
              "questions. This strongly suggests the model/API call is not "
              "engaging with the prompt content at all (broken call, wrong "
              "model routing, or a cached/echoed response) -- treat any "
              f"depth-probe result for {MODEL} as unreliable until this is "
              "resolved (try --no-reasoning-effort, double-check the exact "
              "Poe bot name, or test this same prompt directly in Poe's own "
              "chat UI to see if it reproduces there too).")
    else:
        print("Responses varied across distinct questions -- the model is at "
              "least engaging with prompt content in general. If the "
              "depth-probe run still showed a constant answer, the issue is "
              "more likely specific to that prompt's length/format than a "
              "broken API call.")


# ---------------------------------------------------------------------------
# Main experiment loop
# ---------------------------------------------------------------------------
def main():
    global MODEL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chunk-size", type=int, default=None,
        help="Run at most this many NEW step lengths this invocation, then save "
             "and exit (so the script can be re-run to continue). Default: run "
             "to completion in one invocation.",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"Poe model name to probe (default: {DEFAULT_MODEL}). Per-trial "
             "and summary JSON are tagged with a slug of this name, so "
             "multiple models can share runs/ without "
             "colliding or resuming each other's progress.",
    )
    parser.add_argument(
        "--no-reasoning-effort", action="store_true",
        help="Don't send the reasoning_effort='low' request parameter at all "
             "for this run. Useful for isolating whether a suspicious result "
             "(e.g. a constant answer regardless of input) is caused by this "
             "parameter confusing a model that doesn't actually support it, "
             "as opposed to genuine model behavior.",
    )
    parser.add_argument(
        "--sanity-check", action="store_true",
        help="Don't run the study at all. Instead send 3 trivial, UNRELATED "
             "questions (basic arithmetic, nothing to do with the state "
             "machine) to --model and print the raw responses, to check "
             "whether the model engages with input at all or is returning a "
             "constant/cached/echoed response independent of the prompt. "
             "Use this first if a run comes back with the same answer on "
             "every trial regardless of the actual inputs.",
    )
    args = parser.parse_args()
    MODEL = args.model
    global _reasoning_effort_supported
    if args.no_reasoning_effort:
        _reasoning_effort_supported = False

    if args.sanity_check:
        run_sanity_check()
        return

    random.seed(RANDOM_SEED)
    OUTPUT_DIR.mkdir(exist_ok=True)

    existing = load_existing_summary()
    if existing is not None and existing.get("model") == MODEL:
        per_length_results = existing["per_length_results"]
        stopped_early = existing.get("stopped_early", False)
        stop_reason = existing.get("stop_reason")
        consecutive_at_or_below_chance = recompute_streak(per_length_results)
        already_done = {row["length"] for row in per_length_results}
        print(f"Resuming from existing summary: {len(already_done)} step length(s) "
              f"already completed (up to L={max(already_done) if already_done else 0}).")
        if stopped_early:
            print("Existing summary already reached its early-stop condition; "
                  "nothing further to run. Re-run analysis only.")
            print_summary_table(per_length_results)
            robust_upper_bound = compute_robust_upper_bound(per_length_results)
            print_depth_estimate(robust_upper_bound, stopped_early, stop_reason, per_length_results)
            return
    else:
        per_length_results = []
        consecutive_at_or_below_chance = 0
        stopped_early = False
        stop_reason = None
        already_done = set()

    print(f"Sequential depth probe -- model={MODEL}")
    print(f"Step lengths {MIN_STEPS}..{MAX_STEPS}, {REPS_PER_STEP} reps/length, "
          f"early-stop after {EARLY_STOP_STREAK} consecutive lengths <= "
          f"{CHANCE_ACCURACY:.0%} accuracy.\n")

    remaining_lengths = [L for L in range(MIN_STEPS, MAX_STEPS + 1) if L not in already_done]
    if args.chunk_size is not None:
        remaining_lengths = remaining_lengths[: args.chunk_size]

    for length in remaining_lengths:
        trials = []
        correct_count = 0

        for rep in range(1, REPS_PER_STEP + 1):
            start_node = random.randint(0, 3)

            ground_truth_node, trace = simulate(start_node, length)
            user_prompt = build_user_prompt(start_node, length)

            raw_text, error, finish_reason, reasoning_trace, reasoning_effort_used = call_model(user_prompt)
            model_answer = extract_first_digit_answer(raw_text)
            is_correct = (model_answer == ground_truth_node)
            if is_correct:
                correct_count += 1

            trial_record = {
                "study": "sequential_depth_probe",
                "model": MODEL,
                "length": length,
                "replicate": rep,
                "start_node": start_node,
                "ground_truth_node": ground_truth_node,
                "trace": trace,
                "finish_reason": finish_reason,
                "reasoning_trace": reasoning_trace,
                "reasoning_effort_requested": REASONING_EFFORT_VALUE if reasoning_effort_used else None,
                "raw_response": raw_text,
                "model_answer": model_answer,
                "correct": is_correct,
                "error": error,
            }
            trials.append(trial_record)

            fname = OUTPUT_DIR / f"trial_L{length:02d}_rep{rep}_{model_slug(MODEL)}.json"
            fname.write_text(json.dumps(trial_record, indent=2))

            time.sleep(CALL_SLEEP_SECONDS)

        accuracy = correct_count / REPS_PER_STEP
        threshold_met = accuracy <= CHANCE_ACCURACY
        per_length_results.append({
            "length": length,
            "correct": correct_count,
            "total": REPS_PER_STEP,
            "accuracy": accuracy,
            "at_or_below_chance": threshold_met,
        })

        flag = " <-- AT/BELOW CHANCE" if threshold_met else ""
        print(f"L={length:2d}  {correct_count}/{REPS_PER_STEP}  "
              f"acc={accuracy*100:5.1f}%{flag}")

        if threshold_met:
            consecutive_at_or_below_chance += 1
        else:
            consecutive_at_or_below_chance = 0

        if consecutive_at_or_below_chance >= EARLY_STOP_STREAK:
            stopped_early = True
            stop_reason = (
                f"{EARLY_STOP_STREAK} consecutive step lengths "
                f"(L={length - EARLY_STOP_STREAK + 1}..{length}) at or below "
                f"{CHANCE_ACCURACY:.0%} accuracy"
            )
            print(f"\nStopping early: {stop_reason}.")

        # Checkpoint after every step length, not just at the end, so a
        # chunked/interrupted run never loses completed work.
        robust_so_far = compute_robust_upper_bound(per_length_results)
        write_summary(per_length_results, stopped_early, stop_reason, robust_so_far)

        if stopped_early:
            break

    robust_upper_bound = compute_robust_upper_bound(per_length_results)
    summary = write_summary(per_length_results, stopped_early, stop_reason, robust_upper_bound)

    print_summary_table(per_length_results)
    print_depth_estimate(robust_upper_bound, stopped_early, stop_reason, per_length_results)

    if not summary["complete"]:
        remaining = MAX_STEPS - per_length_results[-1]["length"]
        print(f"\nChunk finished ({len(remaining_lengths)} length(s) run this invocation). "
              f"{remaining} step length(s) remain up to L={MAX_STEPS} -- "
              f"re-run this script to continue (it will resume automatically).")

    print(f"\nRaw per-trial JSON + summary written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
