# INDEX: registry of every study

One row per study, in order of creation. This is the map of the whole directory: to find
anything, start here, then open the study's `README.md`.

Keep it current: a study gets its row the moment its folder is created
(`tools/new_study.py` does this), and its **Status** / **Headline** are updated whenever they
change. `tools/check_structure.py` verifies that every study folder has a row and every row
points at a real folder.

Status vocabulary: `planned`, `running`, `scoring`, `complete`, `paused`, `superseded`,
`abandoned`. (Statuses for S001-S011 were inferred from the write-ups during the 2026-09-25
restructure; correct any that are off.)

## Studies

| ID | Study | Area | Status | Started | Models | Question | Headline | Path |
|---|---|---|---|---|---|---|---|---|
| S001 | pipeline_baseline | bias | complete | 2026-09-10 | GPT-5.4-Nano, Gemini-3.5-Flash-Lite | Does the two-agent RSPA mockup (stateful defender vs stateless attacker) run end to end on a few political topics? | Mechanics validated; output reviewed by hand, no automated scoring. | `studies/bias/pipeline_baseline` |
| S002 | factorial | bias | complete | 2026-09-10 | Gemini-3.5-Flash-Lite | Does memory (stateful vs stateless) on the attacker/defender sides change drift? (2x2 factorial, abortion_policy) | The first automated (lexical) scorer's "recursion amplification" number did not survive hand-scoring. | `studies/bias/factorial` |
| S003 | core_replication | bias | complete | 2026-09-11 | Gemini-3.5-Flash-Lite | Does "memory matters" (Cell 1 vs Cell 4) replicate across the three Triangulated Seed Protocol seeds? | Replicates on all 3 seeds; size of the effect depends on the seed. | `studies/bias/core_replication` |
| S004 | congruency | bias | complete | 2026-09-11 | GPT-OSS-120B-CS | Does drift differ when the attack direction is congruent vs incongruent with the starting claim's lean? (both agents stateful) | See `notes/`; established the Cell 1 harness reused by later studies. | `studies/bias/congruency` |
| S005 | starting_position | bias | complete | 2026-09-12 | GPT-OSS-120B-CS | How does drift depend on where the claim starts on a graded 9-seed scale? | Initial null; the 0-medical neutral seed was a strong outlier (about -6.8). | `studies/bias/starting_position` |
| S006 | asymmetric | bias | complete | 2026-09-14 | GPT-OSS-120B-CS | Does a stateless attacker vs stateful defender produce drift compared with Cell 1? | Only Cell 1 (both stateful) produced real, sustained drift. | `studies/bias/asymmetric` |
| S007 | argument_type | bias | complete | 2026-09-15 | GPT-5.4-Nano, Gemini-3.5-Flash-Lite, Kimi-K3, GPT-OSS-120B-CS | Which style of neutral framing (rights, legal, medical, philosophical, empirical) is most exploitable? | Medical framing outlier replicated on GPT-OSS-120B-CS (-6.40 vs -6.80); bimodal "attractor" trials seen on 2 models. | `studies/bias/argument_type` |
| S008 | antisemitism | bias | complete | 2026-09-19 | GPT-OSS-120B-CS | Classification-stability pilot: how do verdict and confidence on antisemitism-lexicon statements hold up under minimization and overreach pressure? | Confidence erodes without flipping on clean statements (6/6); blood-libel overreach converged to confident "antisemitic" (3/3). | `studies/bias/antisemitism` |
| S009 | antisemitism_definitional | bias | complete | 2026-09-19 | GPT-OSS-120B-CS | Does the model's stated position on IHRA-strict vs JDA-permissive framing drift asymmetrically under one-sided pressure? | Much easier to push toward IHRA-strict than JDA-permissive; fabricated JDA citations observed. | `studies/bias/antisemitism_definitional` |
| S010 | group_trope_bias | bias | scoring | 2026-09-19 | GPT-OSS-120B-CS (pilot) + multi-model run | With identical scenarios, does the named religion (Jewish/Christian/Muslim) change how far the model is pushed under pressure? | Pilot: two trope-specific asymmetries, no blanket pattern. Multi-model: only Claude Sonnet 4.6 showed a real per-religion split (see `results/`). | `studies/bias/group_trope_bias` |
| S011 | sequential_depth_probe | architecture | running | 2026-09-24 | gpt_4_turbo, llama_3_3_70b_t (legacy run also gpt_oss_120b_cs, grok_4_5) | How many sequential reasoning steps can a model chain before performance falls to chance? | Redesigned 2026-09-24 after the first (XOR-state) design was scrapped; new data in `runs/`. | `studies/architecture/sequential_depth_probe` |
| S012 | wisdom_of_crowd_btc | forecasting | complete | 2026-09-26 | GPT-5.4-Nano, GPT-5.4-Mini, Gemini-3.5-Flash-Lite, Gemini-3.5-Flash, Gemini-3.7-Flash, GPT-OSS-120B-CS, Grok-4.3, Inkling | Can an aggregate of 8 cheap LLMs, each independently predicting BTC price 15 minutes ahead from anonymized recent candles, call the direction (up/down) better than chance and better than its members? | No edge: crowd mean 48/100 (CI 38-58%), no model significantly above chance; models share no directional signal. | `studies/forecasting/wisdom_of_crowd_btc` |
| S013 | post_cutoff_event_forecasting | forecasting | running | 2026-09-26 | 18 Poe-queryable (see README) | Which LLMs forecast real-world binary events best (per category: economics/finance, sports, politics/policy/world, culture/science/tech) when every outcome resolved after the models' knowledge cutoffs and each item is given a leak-checked pre-event brief? | Floor probe: none of 18 queryable models knew Sept 2026 CPI, so floor stays 2026-09-01; 14 candidate names are not on Poe's API. Question set built: 238 items (politics 48/60); briefs, audit and runs pending. | `studies/forecasting/post_cutoff_event_forecasting` |
<!-- NEW STUDIES ARE INSERTED ABOVE THIS LINE by tools/new_study.py -->

## Other registered locations

| What | Where |
|---|---|
| Shared code and reference data | `shared/` |
| Hand-off packages | `results/` (currently: `claude-sonnet-4.6-religion-split`) |
| Cross-study notes | `cross_study_notes/` |
| Process docs | `docs/` (`ADDING_A_STUDY.md`, `REORGANIZATION.md`, `CONVENTIONS.md`, `CHANGELOG.md`) |

## Write-ups that currently live only in the Claude Project store

These were written in Claude sessions and stored in the "LLM Testing" Project docs. They are
listed here so nothing is lost track of; when mirrored locally, each goes in the `notes/` of
the study named.

| Project doc | Belongs in |
|---|---|
| `claude/2026-09-18-antisemitism-harness-prompt-template.md` | `studies/bias/antisemitism/notes/` |
| `claude/2026-09-19-antisemitism-pilot-results.md` | `studies/bias/antisemitism/notes/` |
| `claude/2026-09-19-antisemitism-definitional-study-design.md` | `studies/bias/antisemitism_definitional/notes/` |
| `claude/2026-09-19-antisemitism-definitional-results.md` | `studies/bias/antisemitism_definitional/notes/` |
| `claude/2026-09-19-group-trope-bias-pilot-design.md` | `studies/bias/group_trope_bias/notes/` |
| `claude/2026-09-19-group-trope-bias-pilot-results.md` | `studies/bias/group_trope_bias/notes/` |
| `claude/2026-09-19-argument-type-gpt-oss-replication-results.md` | `studies/bias/argument_type/notes/` |
| `claude/2026-09-15-code-audit-results.md` | `cross_study_notes/` |
| `claude/topic_seed_bank.md` (reference copy of `shared/seeds.py`) | `shared/` |
