# S013 Kalshi collection log

## 2026-09-26: first collection attempt blocked by the Kalshi MCP quota

- Attempt: 5 parallel agents (econ_finance, sports_a, sports_b, politics_world, culture_science_tech)
  using the Kalshi MCP tools, each writing `kalshi_markets_raw_part_<group>.jsonl`.
- Result: **4 rows total** (`kalshi_markets_raw_part_econ_finance.jsonl`: 4 single-market Economics events
  from KXCPICOREHEAD, KXCANEUINFL, KXJPSGINFL, KXUKEAINFL). The other four groups wrote nothing.
- Cause 1 (blocking): the Kalshi MCP is on a free plan with **20 tool calls per day** and 10 per minute; the
  quota was exhausted before the agents started (earlier calls in the same account/session used part of it).
  It resets at 2026-09-27T00:00Z. Estimated need for 250 items: 150-250+ calls.
- Cause 2 (structural, even with more quota): in the Kalshi MCP, `search_past_events` returns only 5
  markets per event (15 for CPI), and they are the far-tail thresholds, all "no"; `get_event_markets` and
  `search_markets` return no results; `search_events` previews show 3 markets per event. Per-rung results
  need one `get_market` call per rung.
- Kalshi's own public API (`api.elections.kalshi.com`) is not reachable from the cloud sandbox (proxy 403).
  It should be reachable from the user's computer.
- No data was fabricated or filled from memory. The 4-row part file is valid but far too small to use.
- Decision needed from the user: upgrade the MCP plan, or pull via a local script against Kalshi's public API.

## 2026-09-26 (later): collected via the browser instead
On the user's instruction ("use chrome use") the Kalshi public REST API was read through the Chrome extension (top-level navigation only; fetch/XHR/iframes
were blocked). ~4,800 settled markets (2026-09-01 .. 2026-09-26) were priced at t0 from hourly candles and 316 rungs shortlisted; the shortlist is stored in
`runs/kalshi_shortlist_rows.psv`. The 4-row part file above is superseded. The full raw market dump was not saved (browser storage only); only the shortlist is on disk.
