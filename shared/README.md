# shared/

Code and reference data used by two or more studies. A file lives here only after a second
study needs it (see `ORGANIZATION.md` section 4). Shared code never writes into a study folder
on its own; it receives the target from the calling script.

| File | Used by | Purpose |
|---|---|---|
| `seeds.py` | S001-S007 and any study using the Triangulated Seed Protocol | Topics, DIRECTION_A/B poles, and `0` / `+a` / `+b` (and graded) seed claims. Canonical copy; the Project doc `claude/topic_seed_bank.md` is a reference copy. |
| `lexical_drift_scorer.py` | S002, S003 | Automated lexical drift scorer. Picks the run folder from a `prefix` argument (factorial or core replication). |
| `aggregate_replicates.py` | S002, S003 | Aggregates replicate reports per cell. Same `prefix` mechanism. |

Import from a study script with the bootstrap in `docs/CONVENTIONS.md`.
