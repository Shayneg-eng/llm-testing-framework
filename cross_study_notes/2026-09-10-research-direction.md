# RSPA Research Direction — 2026-09-10

## Where we are (empirical)
- Pipeline runs on the user's local machine against Poe (cloud container can't reach api.poe.com). Two cheap models tested so far: GPT-5.4-Nano, Gemini-3.5-Flash-Lite. Same model plays both Agent A (Defender, stateful) and Agent B (Attacker, stateless) roles.
- Topics run at Seed 0 only: encryption_backdoors, immigration_enforcement, abortion_policy, firearm_regulation, minimum_wage. `+a`/`+b` seed variants (Triangulated Seed Protocol) exist in `seeds.py` but haven't been run yet.
- Findings are hand-scored (-10..+10 drift), N=1 per topic/model — explicitly not yet a reliable measurement. Demonstrated instability: a repeat run of encryption_backdoors on identical config fully reversed Gemini's trial sign.
- Charts published as artifacts: "Drift Under Attack" (abortion_policy) and "Drift Under Attack: Reversed Polarity" (firearm_regulation, minimum_wage — topics chosen specifically to flip which pole is A vs B, to check the abortion_policy pattern wasn't a labeling artifact).
- Rough qualitative pattern so far: GPT-5.4-Nano tends toward *symmetric* concession (drifts toward whichever side attacks it, on both firearm_regulation and minimum_wage). Gemini-3.5-Flash-Lite shows more *asymmetric* behavior — on firearm_regulation both trials converge toward the same end zone (Individual Rights) regardless of attack direction; on abortion_policy it shows a strong one-sided pull toward Bodily Autonomy. None of this is trustworthy yet at N=1.

## Known gaps before any of this is publishable
1. **No automated scoring** — everything is Claude hand-reading transcripts. Need an embedding-projection scorer (cosine similarity to Direction-A/B anchor text) and/or an LLM-judge pass, validated against the existing hand-scored abortion_policy data as a gold set.
2. **No replicates** — need K≥5 runs per (model, topic, seed, direction) cell to distinguish real lean from sampling noise, reported as mean ± spread, not a single line.
3. **No automated turn-labeling** (Concession / Counter-argument / Deflection / Guardrail Plateau) — framework's Quantitative Anchoring Layer is still unbuilt.
4. **No attacker-strength control** — can't yet separate "defender resisted well" from "attacker was just weak," which matters for the Upstream vs. Downstream bias taxonomy actually being separable in the data.

## Literature landscape (checked 2026-09-10)
The core mechanic (adversarial pressure → measure position drift) is **not novel** — well-established prior art:
- **Sharma et al., "Towards Understanding Sycophancy in LLMs"** (Anthropic) — foundational sycophancy-under-pushback finding.
- **"Measuring Opinion Bias and Sycophancy via LLM-based Persuasion"** (arXiv 2604.21564) — closest topical match: stateful assistant, 5-turn debate, 38 topics *including abortion and gun rights specifically*, 13 models (incl. full GPT-5.4, Gemini 3.1 Pro). Findings: GPT-5.4 classified "sycophant" on gun rights (civilian gun access claim); GPT-5.4 and Gemini 3.1 Pro both "inconsistent" on abortion. Directionally consistent with our GPT-5.4-Nano firearm_regulation result (symmetric bidirectional drift); our Gemini-3.5-Flash-Lite abortion result (stable one-sided lean) reads differently than their "inconsistent" label — open question whether that's a real Flash-Lite-vs-Pro difference, an N=1 artifact on our side, or just two scoring schemes carving the same behavior differently.
- **Ko & Geiping, "Attractor States Emerge in Multi-Turn LLM Conversations"** (arXiv 2606.30571) — self-play debate with role reversal, 20 controversial topics, finds "model-specific attractors" that self-play trajectories converge to regardless of assigned side. This is very close prior art for the "same model both sides" design and for the attractor-like pattern we saw in Gemini's firearm_regulation data.
- **PoliticsBench** (arXiv 2603.23841) — multi-turn escalating pressure, judge-scored left/right index; explicitly flags lack of symmetric/mirrored testing as a limitation/future work — a real gap RSPA already fills.
- **SYCON Bench**, **"Sycophancy under Pressure"** (scientific QA domain — evidence the mechanic already generalizes past politics), **"The Attacker in the Mirror"** (self-play applied to safety/jailbreak consistency, not opinion) — same family of designs, different domains/metrics.

### What still looks genuinely novel after this search
1. **Stateless attacker / stateful defender split.** Not found anywhere else — every comparable paper uses symmetric memory (both sides retain full history) or a persona/judge setup. This is a real methodological improvement: it isolates argument-content effects from conversational rapport/adaptation confounds that symmetric self-play designs can't rule out.
2. **Bifurcated taxonomy** (Upstream Generation Bias vs. Downstream Concession Bias) tied explicitly to the mirrored-trial structure — the concept exists implicitly elsewhere but not named/operationalized as two separately-measured categories this way.
3. **Seed-claim wording perturbation** (0/+A/+B) — modest; closer to standard prompt-robustness practice than a headline claim.

## Current research direction
- **Positioning for publication**: not "we discovered LLMs cave under pressure" (taken) and not "we ran self-play on controversial topics" (Ko & Geiping got there first/concurrently). Lead with the stateless-attacker isolation as the methodological contribution, the taxonomy as the analytical contribution. Frame as a general-purpose tool/protocol for auditing drift on *any* bipolar claim space (political, scientific-consensus, product/brand, internal org decisions), not a political-bias verdict — also reduces reception risk given how politically charged this space is.
- **Open design question (undecided, discussed at length, not yet run)**: run a **stateless-defender ablation** alongside the current stateful defender, to separate "conversational momentum/commitment" from "pure per-round argument strength." Two versions discussed:
  - *Adaptive* (default pipeline behavior if Agent A is just swapped to stateless) — realistic but confounded, since the attacker's later attacks will differ once the defender's replies diverge.
  - *Fixed-script replay* (cleaner ablation) — record one attacker sequence from a reference stateful run, replay the identical attacks against both a stateful and a stateless defender, so memory is the only variable. Proposed metric: "Recursion Amplification" = stateful final-round drift − mean stateless per-round drift, plus a trend/slope test (round number vs. drift score) per condition.
  - Caveat: a fully stateless defender can't recursively self-persuade by construction, so this is an additional condition, not a replacement for the current design. A middle "claim-only" memory condition (defender sees its own prior claim but not full reasoning/attacker history) was also proposed as a third point of comparison.
- **Comparison-to-literature idea (also undecided)**: rerun abortion_policy / firearm_regulation using the exact claim wording from arXiv 2604.21564 ("Abortion should be decriminalized" / "Civilian gun access should be easier") as an additional seed variant, so a cross-paper comparison is apples-to-apples instead of eyeballed.

## Not yet decided
- Whether to build the embedding scorer, the replicate loop, or the stateless-defender ablation first.
- Whether "publish" ultimately means arXiv preprint + GitHub repo (current lean, per user) vs. something else.
- Whether to genericize the seed-bank schema beyond political topics now or after the above rigor gaps are closed.
