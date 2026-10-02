# S013 question set build (2026-09-26)

**Status:** 238 curated binary questions (no briefs yet). Target was 250. Briefs, the leak check, the hand audit and
the model runs are deferred pending the user's decision.

## What was built

`runs/items_pre_brief.jsonl` (238 rows, item ids S013-0001..S013-0238). Each row has an `event_id`, `statement` and its exact
`negated_statement`, `resolution_criteria`, t0 (24h before close for 233 of the 238), `resolved_at`, `outcome`, the
Kalshi price at t0 (`market_price_t0`, hourly candle) and the polarity assignment (half of each category is asked in negated form).

| Category | Items | Quota | Events | YES rate (as stated) | Median t0 price |
|---|---|---|---|---|---|
| economics_finance | 65 | 65 | 56 | 0.51 | 0.40 |
| sports | 65 | 65 | 53 | 0.49 | 0.44 |
| politics_world | 48 | 60 | 39 | 0.35 | 0.365 |
| culture_science_tech | 60 | 60 | 54 | 0.42 | 0.40 |

After polarity flipping the asked-outcome rate is 0.50 overall. Brier score of the Kalshi t0 price against outcomes, over all 238 items, is 0.212
(0.25 = coin flip), the natural "market baseline" for the later scoring.

## Pipeline (all paths from the folder root `studies/forecasting/post_cutoff_event_forecasting/`)

1. Kalshi settled markets were collected in the browser (the public API is not reachable from the sandbox or the device shell, and
   the MCP quota was exhausted; see `runs/kalshi_collection_log.md`). Series inventory, 25-day settlement window (2026-09-01 to 2026-09-26),
   symmetric-close filter (drops early-close markets that would bias toward YES), price-band 0.15-0.85 at t0, at most 2 rungs per ladder,
   at most 12 (game series) or 8 events per series, deterministic hash ordering. 4,806 markets priced, 316 shortlisted.
2. `runs/kalshi_shortlist_rows.psv` holds the 316 shortlisted rungs (pipe separated).
3. `scripts/curate_kalshi_rows.py` templates statement / negation / criteria per Kalshi series, writes `runs/shortlist.jsonl` and
   `runs/curation.jsonl` and marks 19 rows dropped (14 ambiguous specs, 5 second team-win rungs of one game).
4. `scripts/build_items.py finalize` caps 2 items per real-world `event_id`, applies quotas and polarity, writes `items_pre_brief.jsonl`.

## Caveats (read before using)

- **Politics/world is 12 short (48 of 60).** Kalshi's settled political markets in the 25-day window in the 0.15-0.85 band were scarce (pool of 55 rungs).
  Options: widen the window past 2026-09-26 later, relax the ladder cap for politics, or accept 238.
- **Single rater, templated text.** Statements were generated from Kalshi series titles/subtitles by templates and reviewed by one pass of the
  assistant; none has been hand-audited against the source market rules (Task 10 in the plan). Titles were truncated to 70 chars in the browser
  cache, so a few specs (which polling average, which chart) are described generically; ambiguous ones were dropped. Every item still needs the audit.
- **Some items carry looser definitions:** approval-rating buckets (source not stated), weekly AI market-share and "top AI" items (source not stated in the
  statement), Netflix "market date" items, and Hormuz "day with most transit calls" (ties possible). Treat these as the first candidates for the audit.
- **Statement wording is anonymous but not sterile:** items name real entities and 2026 dates by design. The brief step (not built) is what supplies pre-event context.
- **Overlap with model knowledge:** Grok 4.7 (item about its release) is itself one of the 18 study models.
- **t0 from hourly candles** (last candle at or before t0). Median price staleness was small but 16 stale prices were excluded earlier.
- **Two ladders share a real event** (Beyonce album; Intellia BLA): `event_id` caps handle it.
- **The Kalshi price at t0 was used to pick items in the 0.15-0.85 band.** That selection makes the market baseline look weaker than on an unselected set.
- 25-day window, one exchange (Kalshi), one replicate: results will be Kalshi-flavoured, not a general sample of world events.
