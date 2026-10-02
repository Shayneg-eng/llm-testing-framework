# S013 post_cutoff_event_forecasting: dataset and study design (2026-09-26)

Status: design approved in chat 2026-09-26, no data collected yet. Written from the
brainstorming session; the implementation plan is the next document.

## Goal

Build 250 real-world binary forecasting items whose outcomes cannot be in any tested model's
training data, and rank LLMs by how well they forecast them, overall and per category
(economics/finance, sports, politics/policy/world, culture/science/tech).

## Decisions made (and why)

| Decision | Choice | Reason |
|---|---|---|
| Contamination strategy | Post-cutoff retrospective only | Outcomes that resolved after a model's training cutoff cannot be memorized; usable now, no waiting |
| Cutoff rule | One global floor for all models | Every model sees identical items; simplest to analyze |
| Item format | Binary question, model returns a probability | Clean resolution; Brier / log loss / calibration |
| Model input | Question + pre-event brief only (no bare-question arm) | Tests reasoning over supplied evidence, closest to real forecasting |
| Categories | 4, scored separately | User wants "better at economy vs sports" style answers |
| Source spine | Settled Kalshi markets, topped up from scheduled-data sources | Explicit resolution rules, settled outcomes, price history for a benchmark |

## 1. The floor

Floor: **2026-09-01** (confirmed after probe round 1, see below) (an item counts only if it resolved on or after this date).
About 25 days of resolved events as of 2026-09-26.

Published cutoffs are unreliable (third-party trackers, several models unlisted, and sources
disagree, e.g. Claude-Sonnet-5). Latest confirmed by a third-party tracker: 2026-06
(Claude-Fable-5.1). Not listed anywhere found: GPT-6-Astra, Gemini-3.6/3.7/3.8-Flash,
Grok-4.5/4.6, Kimi-K3, Inkling, Muse-Spark-1.1, Gemini-Omni.

**Floor verification probe (runs before any scoring):** ask every candidate model about a few
events from Aug-Sep 2026 that could only be known if trained past that point. A model that
answers confidently and correctly has a cutoff at or past the floor: either the floor moves
past it (which shrinks the window) or that model is excluded from the run. Record the probe
prompts and results in `runs/`.

## 2. Unit of analysis

The unit is the real-world **event**, not the Kalshi market. Kalshi lists threshold ladders
("CPI above 0.2 / 0.3 / 0.4%") that are one event repeated many times, and many rungs are
near-certain. Rules:

- Take at most 1-2 thresholds per event or ladder.
- Choose rungs whose market price at t0 was between about 15% and 85%; drop near-certain items.
- Exclude auto-generated multi-leg parlays (series `KXMVE*`, e.g. `KXMVECROSSCATEGORY`).
  In the 2026-09-01 to 09-26 pull they were all settled "no" at tiny prices.
- Randomize question polarity (ask "will X" or "will not X") so "yes" is not systematically
  the likely answer.
- Scoring and confidence intervals use a cluster bootstrap by event.

## 3. Categories and quotas

| Category | Target | Main sources |
|---|---|---|
| Economics and finance | 65 | Kalshi economics series (CPI, jobs, GDP, Fed, central banks), commodities and indices, earnings and company metrics |
| Sports | 65 | Kalshi game winners, spreads, totals (football, tennis, soccer, baseball) |
| Politics, policy, world | 60 | Kalshi politics, elections, courts, international |
| Culture, science, tech | 60 | Kalshi entertainment charts and awards, AI, space, climate |

Economics may run short (few distinct releases in 25 days). Top up with international
inflation, central-bank decisions and earnings before lowering the target; any shortfall is
reported, not hidden.

Power caveat: n of about 60 per category gives a 95% interval of roughly +/-10-12 points on
accuracy; only large model differences will be detectable per category. Raising N or merging
to 3 categories are the levers if this proves too weak.

## 4. Item and brief

Each item has: question, exact resolution criteria, as-of time **t0** (at least 24 hours
before resolution), and a brief of up to about 400 words built only from sources dated
before t0.

- Sports: team stats, form, injuries, schedule.
- Economics: previous prints, consensus forecasts, relevant releases.
- Politics/world: dated reporting.
- Culture/science/tech: prior charts, announced schedules, dated reporting.

The Kalshi price at t0 is stored as a benchmark and **never** appears in the brief.

## 5. Leak control

1. A writer agent builds each brief from dated sources and lists the sources with dates.
2. An independent checker agent, seeing only the brief and question, tries to guess the outcome
   and flags any wording that reveals post-t0 information.
3. Hand audit: every flagged brief plus a random ~10% sample of the rest.
4. Items whose resolution rule is ambiguous are dropped. Dropped items and reasons are logged.

## 6. Scoring

Each model returns a probability per item at temperature 0 (1 replicate). Metrics: Brier score,
log loss, calibration curve, all reported per category and overall. Baselines: Kalshi price at
t0, category base rate, and a constant 50%. Uncertainty by cluster bootstrap over events.
Every write-up states: replicates per cell, number of models, no judge for scoring (mechanical
against resolved outcome), halted or missing trials, per-category interval width, and the
floor-probe result.

## 7. Dataset schema (JSONL, one row per item)

`item_id`, `event_id`, `category`, `source`, `kalshi_ticker`, `question`,
`resolution_criteria`, `t0`, `resolved_at`, `brief`, `brief_sources` (list with dates),
`outcome` (0/1), `market_price_t0`, `polarity_flipped`, `leak_check`
(checker guess and flag), `audited` (bool), `notes`.

Location: `runs/` for machine-written pipeline output. Any script containing an API key stays
out of `results/` packages.

## Pipeline stages (implementation plan to follow)

1. Floor probe on all candidate models.
2. Pull settled Kalshi events since the floor; drop `KXMVE*`; group into events; assign categories.
3. Fill short categories from scheduled-data sources.
4. Choose rungs (15-85% at t0), randomize polarity, fix t0 and fetch the t0 market price.
5. Write briefs; run the independent leak check; hand audit.
6. Freeze the dataset (hash it) before any model sees it.
7. Run all models, score, analyze per category.

## Known risks

- Short window (about 25 days) limits diversity, especially outside sports.
- Third-party cutoff data is unreliable; the probe is the real control.
- Brief quality varies by source availability; the writer/checker pair reduces but does not
  remove leakage.
- Kalshi settled prices are near 0/1 after resolution, so the t0 price must come from
  candlestick history, not the listed last price.
- Single writer model and single checker model: their own biases could shape briefs.

## Update 2026-09-26 (after floor probe round 1)

- Floor confirmed at 2026-09-01. A graded-ladder probe (monthly CPI prints, to move the floor
  earlier) was considered and declined; the ~25-day window stands.
- Model set is the 18 models reachable through Poe's API (list in the study README). The other
  14 names in the Project doc "Poe Model Names" are not served by the API and are out of scope.
  Evidence: `notes/2026-09-26-floor-probe-round1.md`.
- Caveat carried forward: "I don't know" on two September 2026 CPI questions, 1 ask per model,
  suggests but does not prove that each model's cutoff is before the floor.
