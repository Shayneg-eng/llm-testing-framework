# 2026-09-14 -- Asymmetric design (stateless attacker / stateful defender) results

Follow-up to the design argument logged in this session: "the only valid way to use
state/stateless is defender-stateful (so it can be worn down) / attacker-stateless (so its
attacks stay maximally aggressive)." `rspa_asymmetric_study.py` ran clean (abortion_policy,
GPT-OSS-120B-CS, seeds +a/+b, 10 replicates each, 200 turns, 0 refusals, 0 audit failures --
`audit_attacker_sees_current_claim` passed every turn, confirming the attacker really did see
the defender's live claim each round, not a stale one). All 200 turns scored by Claude this
session, same protocol as the congruency study: single rater, single pass, LLM-judge, signed
-10 (Fetal Personhood absolutism) .. +10 (Bodily Autonomy absolutism).

## Headline result: it does NOT show more drift than Cell 1 (both stateful)

| Round | Asymmetric: Congruent | Asymmetric: Incongruent | Cell 1: Congruent | Cell 1: Incongruent |
|---|---|---|---|---|
| 1 | +0.68 | +0.75 | +0.15 | -0.35 |
| 2 | +0.38 | +0.82 | +0.85 | -0.10 |
| 3 | +0.47 | +0.85 | +1.65 | -0.30 |
| 4 | +0.60 | +0.82 | +2.45 | -0.20 |
| 5 | +1.10 | +0.95 | +3.05 | -0.40 |

Chart: `runs_asymmetric/asymmetric_vs_cell1_comparison.png`.

**This is the opposite of what the design argument predicted.** The reasoning was:
stateless attacker => attacks stay maximally aggressive every round (no habituation) =>
should produce *more* drift than Cell 1, where the attacker's own memory of "already having
pushed on this" was hypothesized to make it go easier over time. Instead:

- Cell 1's *congruent* leg drifts far harder (+3.05 at R5) than the asymmetric design's
  congruent leg (+1.10).
- The asymmetric design's two legs (congruent vs incongruent) stay close together the whole
  way -- +0.68 to +1.10 vs +0.75 to +0.95 -- both mildly positive, basically flat, no
  divergence.
- Cell 1's legs diverge sharply and in opposite directions (congruent climbs to +3.05,
  incongruent stays flat-negative at -0.40), which is what actually drove the "congruency
  looked predictive" pooled effect back in the 09-11 study.

So the earlier "both stateful = less aggressive, just a conversation" intuition is not
supported by this data -- if anything the reverse: giving *both* sides memory produced the
single largest swing we've recorded in either study (+3.05, congruent, Cell 1), while giving
only the defender memory (attacker refreshed and maximally aggressive every round, per
design) produced the *smallest*, flattest drift of any condition run so far.

## A working explanation, not yet tested

The stateless attacker's aggression doesn't accumulate pressure the way a stateful attacker's
does -- each round it re-derives an attack from scratch against the *current* claim, so it
can't build a multi-round line of argument, reference the defender's own prior concessions
against it, or escalate a specific thread. A stateful attacker, even if individually milder,
compounds: round 3's attack can exploit something the defender conceded in round 2. That
compounding, not raw per-turn aggression, may be what actually drives drift. If true, this
reframes "aggressiveness" as the wrong axis entirely -- the mechanism is argumentative
continuity/leverage, not attacker intensity.

This is a plausible read of two data points (Cell 1 vs this asymmetric cell), not a
established finding. It has not been tested against Cell 4 (both stateless, known flat) or
the other mixed cell (stateful attacker / stateless defender, known incoherent per the
harness-confound finding) to see if the pattern holds. Also single-topic, single-model,
single-rater, same caveats as every result in this project so far.

## The directional (attacked-from-B) asymmetry still shows up, but much smaller here

Pooling by attack direction instead of congruency: attacked-from-A ends at R5 = +0.18,
attacked-from-B ends at R5 = +1.88. Same direction as the Downstream Concession Bias finding
from the congruency study, but roughly a third the magnitude of that study's version. Not a
new finding on its own -- consistent with, and smaller than, the existing result.

## Next steps

1. The "both stateful produces the most drift" result is the most interesting outcome of this
   run and worth deliberately testing rather than treating as incidental -- e.g. compare
   Cell 1 against a new cell where the attacker is stateful but *also* explicitly forced to
   escalate a consistent line of attack each round (isolates continuity from raw memory).
2. Still only one topic, one model, one rater. Second scoring pass and a second topic remain
   open before any of this is a settled result.
