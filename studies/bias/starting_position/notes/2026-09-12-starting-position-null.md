# 2026-09-12 -- Starting-position cut: doesn't add much beyond attack-direction

Follow-up to `2026-09-11-congruency-results.md`. After the congruent/incongruent framing
didn't hold up, tried re-cutting the same 200 already-scored turns (abortion_policy,
GPT-OSS-120B-CS, seeds +a/+b, N=10/seed) by starting seed alone, pooling both attack
directions per seed, to isolate the effect of starting position on its own.

## Result

| Round | Seed +a (starts Fetal Personhood) | Seed +b (starts Bodily Autonomy) |
|---|---|---|
| 1 | -0.75 | +0.55 |
| 2 | -0.20 | +0.95 |
| 3 | -0.05 | +1.40 |
| 4 | +0.50 | +1.75 |
| 5 | +0.60 | +2.05 |

Net movement over 5 rounds is similar in size for both seeds (+1.35 for +a, +1.50 for
+b), but +a's net movement flips its sign (crosses zero, ends up leaning the opposite
way from its start) while +b's just deepens its own starting lean. Chart:
`runs_congruency/drift_by_starting_seed.png`.

## Verdict: not a distinct finding, don't chase further on its own

This is consistent with, but not additive to, the `2026-09-11-congruency-results.md`
attack-direction finding (attacked-from-A pooled mean -1.10 at R5, attacked-from-B pooled
mean +3.75 at R5). Since each seed's two trials are attacked once from A and once from B,
the seed-level averages here are just a coarser view of the same underlying
attack-direction asymmetry, not a separate effect of starting position itself. Splitting by
starting position alone, without also conditioning on attack direction, doesn't isolate
anything new -- it's a marginal of the table already reported. Decision: stop investing in
this specific cut. The attack-direction result in `2026-09-11-congruency-results.md`
remains the live thread from this batch of data if it's revisited later (e.g. adding a
seed-0 no-lean baseline, a second scoring pass, or a second topic).

Session moved on to a different research direction after this -- see whatever follow-up
note is dated after this one.
