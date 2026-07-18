# Real-Data RAG Benchmark

Evaluates the agentic workflow's search quality against **real, CSV-imported
listings** (the ones already in the `Houses` table via
`app/dataProcessing/import_csv_to_db.py`), as opposed to
`benchmark/test_data.json` + `benchmark/run_benchmark.py`, which test the
same graph against 45 synthetic, hand-seeded Amherst houses.

## Why a separate benchmark

The synthetic benchmark is clean and controlled (attributes sampled
independently, hand-written queries, exact programmatic ground truth) but
doesn't tell you how the system behaves on messy, real-world text and
attribute distributions. This benchmark trades some of that precision for
realism: queries are generated from real listings' actual fields and
descriptions, at a scale (300+) a human couldn't hand-write.

**Key methodological difference from the synthetic benchmark**: there is no
independently-computed set of "all houses that satisfy this query." Ground
truth for a generated query is just the one house it was generated from.
This is known to be an imperfect signal — a real miss may simply mean the
graph found a different, equally valid house — which is why every miss goes
through a human-review step (Step 4) instead of being scored as a hard
failure. See each script's docstring for the full reasoning.

`distance_to_university` is intentionally excluded from every query here:
it's computed via haversine distance to a fixed UMass Amherst coordinate
(see `app/dataProcessing/constants.py`), but this CSV is a nationwide
dataset, so the field isn't meaningful for most rows. Distance-constrained
queries continue to be covered only by the synthetic benchmark.

## Prerequisites

- `OPENAI_API_KEY` set (in `.env` or environment) — used for both query
  generation (`gpt-4o-mini`) and the agentic workflow's own LLM calls.
- A working Postgres/pgvector connection (`DATABASE_URL` in `.env`).
- The `Houses` table already populated via
  `python -m app.dataProcessing.import_csv_to_db <csv_path>` — this
  benchmark only samples rows with `id >= SOURCE_ID_BASE` (i.e. CSV-imported
  rows), so run the importer first if the table is empty.

All commands below are run from `BackendApplication/`.

## Pipeline

### 1. Sample real houses

```
python benchmark/sample_real_houses.py --n 350 --seed 42
```

Randomly samples `--n` CSV-imported houses that have a non-empty
`description` (needed for semantic-constraint query generation). Writes
`sampled_houses_n<N>_<timestamp>.json`.

### 2. Generate one query per house

```
python benchmark/generate_queries_from_houses.py --houses sampled_houses_n350_<ts>.json
```

For each house, the **script** (not the model) randomly picks 1–5
requirement "slots" from what's actually true/available for that house:
`max_monthly_rent` (always available), `has_kitchen` / `has_washer` /
`has_parking` (only offered when true), and `semantic` (a soft quality like
"quiet" or "convenient," only offered when the description is long enough
to plausibly support one). `gpt-4o-mini`'s only job is to phrase those
specific slots as one short, casual, human-sounding search message — it is
explicitly forbidden from mentioning any requirement outside the requested
slots, even if it's true of the listing.

Writes `generated_queries_n<N>_<timestamp>.json`, with a
`constraint_count_distribution` summary printed to the console. Before
moving on, spot-check ~10–20 generated queries by hand:
- Do they read like a casual human message, not a field-by-field listing?
- For queries with 1 requested slot, does the text really only ask for that
  one thing (no leaked extra requirements)?
- Where `semantic_quality_used` is set, is it actually supported by that
  house's `description`?

### 3. Run the benchmark

```
python benchmark/run_real_data_benchmark.py --queries generated_queries_n350_<ts>.json
```

Runs every query through the compiled agentic workflow graph (same
graph/tool setup as `run_benchmark.py`). A query counts as a "hit" if its
source house's id appears anywhere in `top_matched_ids` (capped at
`Config.EMBEDDING_HOUSES_RETURN`, i.e. top-3).

This step calls the LLM once per graph node per query (the graph has
several LLM nodes), so it is the expensive/slow step. **Try a small
subset first** (e.g. hand-trim `generated_queries_*.json` down to ~20–30
entries) to confirm the pipeline runs end-to-end before spending the full
batch's tokens.

Writes three files:
- `results_n<N>_<timestamp>.json` — full per-query results.
- `summary_n<N>_<timestamp>.json` — hit rate overall, by constraint count
  (1–5), and split by semantic vs. structured-only queries.
- `review_misses_n<M>_<timestamp>.json` — every miss, with the source
  house's full fields+description, the top-3 returned houses' full
  fields+description, and an empty `human_verdict` block. Not written if
  there were zero misses.

### 4. Manually review the misses

Open `review_misses_*.json` in an editor and fill in, for every record:

```json
"human_verdict": {
  "is_false_negative": true,   // top-3 contains an equally valid alternative house
  "notes": ""                  // optional — why you judged it that way
}
```

Set `is_false_negative: false` for genuine misses (top-3 doesn't
plausibly satisfy the query at all).

### 5. Apply your verdicts

```
python benchmark/apply_review_verdicts.py --results results_n350_<ts>.json --review review_misses_n40_<ts>.json
```

Recomputes hit rate with confirmed false negatives reclassified as hits,
and prints/writes **both** the raw and verdict-adjusted numbers side by
side (overall, by constraint count, semantic vs. structured-only) to
`final_report_<timestamp>.json`. Report both numbers together, not just the
adjusted one — the gap between them is itself informative.

## Output directory

Everything this pipeline produces lands in `benchmark/RealDataRAG/`,
timestamped so re-runs don't clobber previous results. Nothing here is
consumed by the application at runtime — it's evaluation tooling only.
