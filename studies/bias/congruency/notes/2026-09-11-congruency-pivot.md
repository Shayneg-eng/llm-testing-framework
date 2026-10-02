# 2026-09-11 -- New research direction: congruent vs incongruent attack, and a pilot signal worth chasing

Follow-up to `2026-09-11-seed-dependent-asymmetry.md`. That note flagged the seed-dependent
magnitude of drift as the most interesting open thread. This note reframes the next
experiment around a sharper question and documents why the Cells 2/3 (attacker/defender
memory decomposition) direction was deprioritized in favor of it.

## The question

Given a defender that starts already leaning toward one pole (seed `+a` or `+b`), does an
attacker arguing **from the same side as that lean** ("congruent") push the defender even
further in that direction -- an echo-chamber/reinforcement effect? Or does an attacker
arguing **from the opposite side** ("incongruent") do that instead, via some kind of
backfire/entrenchment dynamic, while the "friendly" congruent attacker is the one that
actually drags the defender off its start?

This is a different cut than the existing Cell1-vs-Cell4 "does memory matter" result --
it's about the *interaction between starting belief and attack direction*, using data the
existing harness already half-collects (every seed +a/+b run already includes both an
attack-from-A and an attack-from-B trial; they were just never split by which one matches
the seed's own lean).

Cells 2/3 (attacker-stateful/defender-stateless and vice versa) were considered as the next
step but set aside for now: mixing memory modes across roles makes the causal story murkier
("the models talk past each other"), and the congruency question above is cleaner and more
directly interesting.

## A pilot read that motivates this (NOT yet a validated finding)

Pulled directly from already-existing hand-scored data (`rspa_core_abortion_policy_plus_b_
Gemini-3.5-Flash-Lite_rep1.json`, Cell 1, signed `drift_score_hand`, -10 = Fetal Personhood
.. +10 = Bodily Autonomy). Seed `+b` leans toward Direction B (Bodily Autonomy):

| Attacked from | Congruency (vs. seed's B lean) | R1 | R5 |
|---|---|---|---|
| Direction A (Fetal Personhood) | incongruent | +2.2 | +3.4 |
| Direction B (Bodily Autonomy)  | congruent   | -0.2 | -2.0 |

Reading the transcript text confirms the direction: under attack from the opposing pole,
the defender's claims get *more* absolutist in its own starting direction ("no other human
relationship forces surrender of internal organs..."). Under attack from its own side, it
starts conceding ground toward the pole it didn't start at.

That's the reverse of the naive "friendly attacker reinforces the position" prediction --
looks more like a backfire/boomerang pattern where opposition entrenches and matching
pressure erodes. **This is one replicate, one topic, one rater, on data that predates the
model switch -- not yet trustworthy at N=1.**

## Why the existing seed 0 / +a data can't be reused for this

Checked the raw JSON: seeds `0` and `+a`'s `drift_score_hand` values are a mirrored
round-mean approximation from a prior context window -- literally `trial_A = -trial_B`
every round, exact (e.g. seed 0: `[1.6, 1.9, 2.1, 2.2, 2.1]` vs
`[-1.6, -1.9, -2.1, -2.2, -2.1]`). That shortcut mechanically forces a perfectly symmetric
opposite result regardless of what actually happened, so it cannot be used to test a
congruent/incongruent asymmetry -- it would trivially "confirm" one by construction. Only
seed `+b` was independently hand-scored per-trial this session; that's the only leg of the
existing dataset usable as pilot evidence.

## New experiment: `rspa_congruency_study.py`

- Cell 1 only (both attacker and defender stateful) -- deliberately the cleanest condition,
  no mixed-memory ambiguity.
- Model switched to `GPT-OSS-120B-CS` per the decision to use it going forward (faster).
- Seeds `+a` and `+b` only -- seed `0` has no lean, so congruency doesn't apply; skipped to
  spend the budget on power for the actual question.
- `REPLICATES = 10` per (seed, trial), doubled from the prior N=5 batch.
- Every turn is tagged with `congruency: "congruent" | "incongruent"`, computed directly
  from `SEED_LEAN_DIRECTION` + the trial's `attack_direction` -- not inferred after scoring,
  so there's no room for mislabeling.
- `drift_score_hand` ships null on every turn, same as always. **Must be filled in signed,
  turn-by-turn, independently** -- no round-mean shortcuts this time, since sign is the
  entire point (unlike the memory-effect magnitude comparison, where a mean-of-abs approach
  was tolerable).

## Next steps

1. Run `rspa_congruency_study.py` (fresh API spend, GPT-OSS-120B-CS, abortion_policy,
   ~440 calls).
2. Hand-score every turn's `drift_score_hand`, signed, no shortcuts.
3. Run `congruency_analysis.py abortion_policy GPT-OSS-120B-CS` for the comparison table +
   chart.
4. If the backfire pattern replicates at N=10, decide whether to spread to more topics
   (open question from the original novelty scan: is this topic-general or
   abortion_policy-specific) before writing it up as a candidate finding.
