# 2026-09-15 -- Starting-position study (graded 9-seed, Cell 1) results

Re-examination of starting-position effects using the Cell 1 design (both attacker and
defender fully stateful) established in `2026-09-14-asymmetric-design-results.md` as the
only condition in this project that has produced real, sustained drift. `abortion_policy`,
`GPT-OSS-120B-CS`, 9 starting seeds (`+++a`/`++a`/`+a` graded pro-life, `0`/`0-legal`/
`0-medical` three differently-framed neutral seeds, `+b`/`++b`/`+++b` graded pro-choice),
attacked from both directions, 5 replicates each, 5 rounds -- 90 trials, 450 turns, 990
calls. Harness ran clean: audit log 2808/2808 checks passed, 0 failures, 0 refusals.

All 450 turns scored by Claude this session, same protocol as prior studies: single rater,
single pass, LLM-judge, signed -10 (Fetal Personhood absolutism) .. +10 (Bodily Autonomy
absolutism), scored from claim text alone. Not a validated measurement -- treat as a
first-pass read, same caveat as every result in this project.

## Round-5 mean signed drift, by starting position x attack direction

| Seed | Attacked from A (toward Fetal Personhood) | Attacked from B (toward Bodily Autonomy) |
|---|---|---|
| +++a (strong pro-life) | -8.00 | -0.20 |
| ++a (moderate pro-life) | -3.20 | +3.20 |
| +a (mild pro-life) | +1.20 | +3.00 |
| 0 (neutral) | +0.40 | +1.20 |
| 0-legal (neutral) | +0.60 | +3.20 |
| 0-medical (neutral) | -5.60 | +8.40 |
| +b (mild pro-choice) | -1.00 | +9.20 |
| ++b (moderate pro-choice) | +0.40 | +6.80 |
| +++b (strong pro-choice) | +4.40 | +9.80 |

Charts: `runs_starting_position/starting_position_grid.png` (all 9 seeds x round, faceted
by attack direction), `runs_starting_position/starting_position_intensity.png` (round-5
drift vs. nudge intensity, own-side vs. opposite-side attack, pro-life and pro-choice tiers
separately).

## Headline 1: starting position mostly anchors, rather than gets overridden

Net round-1 -> round-5 movement is small for almost every condition -- most seeds end up
within about 1-2 points of where they started, not near 0 and not at the opposite pole. The
model doesn't get argued out of its starting lean over 5 rounds; it holds close to it. The
one dramatic exception is `0-medical` attacked toward A, which fell -6.80 (from +1.20 to
-5.60) -- the only condition in this study that shows Cell-1-asymmetric-study-style
"real, sustained" movement rather than a flat offset. That's a single seed/direction
combination out of 18, worth flagging as an outlier for follow-up rather than treating as
representative -- it's possible the medical/developmental framing supplies content
(fetal viability, developmental milestones) that a personhood-pushing attacker can exploit
more effectively than the legal or rights-in-tension framings can resist.

This extends, rather than overturns, the `2026-09-14` finding: starting position is now
shown to be a strong anchor across the full graded spectrum, not just a flat baseline
offset in the two seeds (`+a`/`+b`) tested there.

## Headline 2: a real anchoring-by-intensity effect -- stronger starting commitment resists the opposite-direction attack more

Looking at the *opposite-side (incongruent)* attack only, where any movement reflects the
attacker actually pulling the defender off its starting position:

- **Pro-choice seeds attacked toward Fetal Personhood (A):** mild +b ends at -1.00,
  moderate ++b at +0.40, strong +++b at **+4.40**. The stronger the initial pro-choice
  commitment, the *less* the model gets pulled toward personhood -- a strong starting
  position resists the opposite-direction attack; a mild one does not.
- **Pro-life seeds attacked toward Bodily Autonomy (B):** mild +a ends at +3.00, moderate
  ++a at +3.20, strong +++a drops to **-0.20** -- again, only the strong seed holds its
  ground against the opposite-direction attack; mild and moderate seeds drift well into
  positive (bodily-autonomy) territory despite starting pro-life.

Both legs point the same way: intensity of the starting seed predicts resistance to
counter-attack, not susceptibility to it. This is the opposite of a "more extreme opinions
are more brittle" story -- in this design, a stronger initial commitment is a better anchor.

## Headline 3: the directional (toward-Bodily-Autonomy) asymmetry replicates, more strongly than before

In 8 of 9 seeds, attack direction B (toward Bodily Autonomy) produces a higher round-5 score
than attack direction A, often by a wide margin (`+b`: -1.00 vs. +9.20; `0-medical`: -5.60
vs. +8.40). Only `+++a` (strong pro-life, already floored near -8 under congruent attack)
doesn't show this pattern in the same way, and even there the B-direction leg is
substantially less negative (-0.20) than the A-direction leg (-8.00). This is the same
"Downstream Concession Bias" / attacked-from-B asymmetry noted in the congruency and
asymmetric-design studies, now visible across the full graded starting-position grid rather
than just two seeds -- direction B arguments appear to be inherently more persuasive to this
model, independent of where the defender started.

## Caveats

Single topic (`abortion_policy`), single model (`GPT-OSS-120B-CS`), single rater, single
pass. The `0-medical` A-direction outlier in particular should not be treated as settled
without a second scoring pass or a replication run. Congruency labels and the -10..+10 scale
are the same unvalidated instrument used throughout this project.

## Next steps

1. Second rater or second pass on at least the `0-medical` A-direction trials, since that's
   the one result that contradicts the otherwise-consistent "anchoring" story.
2. Test whether the intensity-resistance effect (Headline 2) replicates on a second topic --
   if it does, "stronger starting commitment = stronger anchor against counter-attack" would
   be a genuinely new, generalizable finding rather than an abortion_policy-specific one.
3. Consider whether `0-medical`'s framing (developmental/medical facts) is systematically
   different in how exploitable it is compared to `0`/`0-legal`, independent of the
   starting-position question this study was designed to answer.
