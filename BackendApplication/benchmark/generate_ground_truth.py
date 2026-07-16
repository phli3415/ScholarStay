"""
Independent ground-truth labeler for the raw listing CSVs in
benchmark/TestingDataSet, used to score the CSV -> Houses import pipeline
(app/dataProcessing/parsers.py + app/dataProcessing/llm_extractor.py).

This script is deliberately built from scratch: it does not import, and its
prompt does not paraphrase, any of parsers.py's regex/state tables or
llm_extractor.py's keyword lists / extraction prompt. The point is to get a
second, independently-reasoned opinion on the same fields so that scoring the
pipeline against this ground truth is a real comparison, not the pipeline
checking itself.

Target fields (mirrors the Houses model columns the import pipeline fills):
    province, city, street, house_number, monthly_rent,
    has_kitchen, has_washer, has_parking

Row filter: rows whose price_type isn't "Monthly" are skipped entirely, same
as the import pipeline would skip them.

Every field carries: value, source (column/body/none), a verbatim quote as
evidence, and a confidence level. has_kitchen/has_washer/has_parking are
plain booleans, with a separate is_negation_case flag for rows where the
text explicitly denies the amenity (e.g. "no parking") -- kept as a side
flag rather than a third state, so it doesn't complicate scoring but still
lets negation accuracy be measured separately.

Usage (from BackendApplication/):
    python benchmark/generate_ground_truth.py
    python benchmark/generate_ground_truth.py --csv benchmark/TestingDataSet/apartments_for_rent_classified_1K.csv --limit 200

Writes two files to benchmark/GroundTruth/:
    ground_truth_<csv_stem>_n<limit>_<timestamp>.json   -- full annotated set
    human_review_sample_<csv_stem>_n<limit>_<timestamp>.json -- subset to spot-check
"""

import argparse
import asyncio
import csv
import json
import os
import random
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BENCH_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = BENCH_DIR / "TestingDataSet" / "apartments_for_rent_classified_10K.csv"
OUT_DIR = BENCH_DIR / "GroundTruth"

DEFAULT_LIMIT = 50
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_CONCURRENCY = 6
DEFAULT_REVIEW_FRACTION = 0.18
MAX_ATTEMPTS = 3

_NULL_TOKENS = {"", "null", "none", "n/a", "na", "nan", "--", "-"}


def clean_cell(v) -> Optional[str]:
    """Normalize a raw CSV cell: strip whitespace, treat common null tokens as None."""
    if v is None:
        return None
    s = str(v).strip()
    return None if s.lower() in _NULL_TOKENS else s


def is_monthly(row: dict) -> bool:
    pt = clean_cell(row.get("price_type"))
    return pt is not None and pt.lower() == "monthly"


# ── output schema ────────────────────────────────────────────────────────────

class EvidenceSource(str, Enum):
    COLUMN = "column"   # evidence found in a structured CSV column
    BODY = "body"        # evidence only found in the free-text title/body
    NONE = "none"        # no evidence anywhere


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TextJudgment(BaseModel):
    value: Optional[str] = Field(None, description="the field value, or null if not determinable")
    source: EvidenceSource
    quote: Optional[str] = Field(None, description="verbatim text copied from the input that supports value; null if source is none")
    confidence: Confidence


class RentJudgment(BaseModel):
    value: Optional[float] = Field(None, description="monthly rent as a number, or null")
    source: EvidenceSource
    quote: Optional[str] = None
    confidence: Confidence


class AmenityJudgment(BaseModel):
    value: bool = Field(..., description="true if this specific unit is confirmed to have the amenity, false otherwise")
    source: EvidenceSource
    quote: Optional[str] = None
    confidence: Confidence
    is_negation_case: bool = Field(
        ...,
        description="true only when the text explicitly denies this amenity for this unit (e.g. 'no parking', 'washer NOT included')",
    )


class ListingAudit(BaseModel):
    province: TextJudgment
    city: TextJudgment
    street: TextJudgment
    house_number: TextJudgment
    monthly_rent: RentJudgment
    has_kitchen: AmenityJudgment
    has_washer: AmenityJudgment
    has_parking: AmenityJudgment
    auditor_notes: Optional[str] = Field(None, description="anything unusual about this listing worth a human reviewer's attention")


FIELD_NAMES = [
    "province", "city", "street", "house_number", "monthly_rent",
    "has_kitchen", "has_washer", "has_parking",
]
AMENITY_FIELDS = {"has_kitchen", "has_washer", "has_parking"}


# ── prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an independent data auditor reviewing raw rental-listing records for a research benchmark. You are NOT a data-extraction assistant -- your job is to conservatively verify whether each target field is actually supported by the text you are given, and to say so plainly when it is not.

Ground rules:

1. Never guess. If nothing in the provided text supports a value, use source="none", value=null (or false for the has_* boolean fields), and confidence="low".
2. Every field whose source is not "none" MUST include a "quote" copied verbatim from the provided text (do not paraphrase, translate, or correct typos in the quote).
3. "source" tells us WHERE the evidence came from:
   - "column" if the evidence is one of the lines under STRUCTURED_FIELDS (pre-existing database columns)
   - "body" if the evidence only appears in the FREE_TEXT_LISTING block (unstructured prose written by the listing poster)
   - "none" if there is no evidence anywhere
   A STRUCTURED_FIELDS value that directly answers a field always takes priority over anything in the free text.
4. has_kitchen / has_washer / has_parking are plain booleans (true/false), never "maybe". Set is_negation_case=true ONLY when the text explicitly denies the amenity for this specific unit (e.g. "no parking available", "washer/dryer NOT included"). Note: "unfurnished kitchen" does NOT negate a kitchen -- an unfurnished kitchen is still a kitchen. Do not infer presence from vaguely related words unless they clearly describe an amenity belonging to THIS unit (e.g. a building-wide fitness center or a nearby public laundromat does not imply this unit has in-unit parking or a washer).
5. Synonyms count for the has_* fields -- do not require the literal words "kitchen"/"washer"/"parking". Accept clear synonyms describing the same real-world amenity for this unit, for example: stove, oven, refrigerator, dishwasher, cooking facilities -> kitchen; laundry, washer/dryer, in-unit laundry, laundry hookup -> washer; garage, driveway, off-street parking, carport -> parking. Do not accept vague or unrelated mentions.
6. street / house_number: the ADDRESS-related text may reference more than one street -- sometimes comma-separated, sometimes simply concatenated with a space with no punctuation between them (e.g. a cross-street or a second street tacked directly onto the first). Extract ONLY the first street reference reading left to right, together with a house number if one is directly attached to it. Ignore any state name or ZIP/postal code appearing anywhere in the text -- never treat those as part of the street. If the text clearly names a street but includes no number at all, house_number must be null with confidence="high" -- that is a confident "no number", not "unknown".
7. monthly_rent: use ONLY the PRICE structured field if it is present and numeric. Do not use any dollar figures mentioned only in the free-text body (the body sometimes describes a price RANGE across multiple unit types, which is out of scope here -- if PRICE is missing, try to find a single unambiguous monthly rent figure in the body that clearly applies to this listing, otherwise value=null).
8. province / city: prefer the STATE / CITYNAME structured fields. Only fall back to the free-text body when the structured field is missing or empty.
9. Any structured field may be empty for a given listing -- when that happens, look for the same information in FREE_TEXT_LISTING before concluding source="none".

Return your judgment as strict JSON matching the provided schema only. Do not add commentary outside the schema fields."""


def build_user_prompt(row: dict) -> str:
    structured_lines = [
        f"STATE: {clean_cell(row.get('state')) or '(empty)'}",
        f"CITYNAME: {clean_cell(row.get('cityname')) or '(empty)'}",
        f"ADDRESS: {clean_cell(row.get('address')) or '(empty)'}",
        f"PRICE: {clean_cell(row.get('price')) or '(empty)'}",
        f"AMENITIES: {clean_cell(row.get('amenities')) or '(empty)'}",
    ]
    title = clean_cell(row.get("title")) or ""
    body = clean_cell(row.get("body")) or ""
    free_text = (title + "\n" + body).strip() or "(empty)"
    return (
        "STRUCTURED_FIELDS:\n" + "\n".join(structured_lines) +
        "\n\nFREE_TEXT_LISTING:\n" + free_text
    )


# ── labeling ──────────────────────────────────────────────────────────────────

async def label_row(client, sem: asyncio.Semaphore, model: str, row: dict, row_index: int) -> dict:
    base = {
        "csv_id": row_index + 1145140000,  # matches SOURCE_ID_BASE + row_index in app/dataProcessing/constants.py, i.e. the DB house id the import pipeline would assign this row
        "price_type_raw": row.get("price_type"),
    }
    prompt = build_user_prompt(row)
    async with sem:
        last_err = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                completion = await client.beta.chat.completions.parse(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    response_format=ListingAudit,
                    temperature=0,
                )
                parsed = completion.choices[0].message.parsed
                if parsed is None:
                    raise ValueError("model returned no parsed output (refusal or empty)")
                return {**base, "fields": json.loads(parsed.model_dump_json()), "error": None}
            except Exception as e:
                last_err = str(e)
                if attempt < MAX_ATTEMPTS - 1:
                    await asyncio.sleep(1.5 * (attempt + 1))
        return {**base, "fields": None, "error": last_err}


# ── review sampling ───────────────────────────────────────────────────────────

def build_review_reasons(record: dict) -> list[str]:
    reasons = []
    if record["error"] is not None:
        reasons.append("label_error")
        return reasons
    fields = record["fields"]
    if any(fields[f]["confidence"] == "low" for f in FIELD_NAMES):
        reasons.append("low_confidence")
    if any(fields[f].get("is_negation_case") for f in AMENITY_FIELDS):
        reasons.append("negation_case")
    return reasons


def human_verdict_skeleton() -> dict:
    return {f: {"correct": None, "notes": ""} for f in FIELD_NAMES}


# ── main ──────────────────────────────────────────────────────────────────────

async def run(args) -> None:
    load_dotenv()
    from openai import AsyncOpenAI  # imported after load_dotenv so OPENAI_API_KEY is set

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set (checked environment and .env). Aborting.", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        # accept paths relative to either the current working directory or this script's dir
        cwd_candidate = Path.cwd() / args.csv
        csv_path = cwd_candidate if cwd_candidate.exists() else (BENCH_DIR / args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = []
        for row_index, row in enumerate(reader, start=1):
            if row_index > args.limit:
                break
            rows.append((row_index, row))

    to_label = [(idx, row) for idx, row in rows if is_monthly(row)]
    skipped_non_monthly = len(rows) - len(to_label)

    print(f"Read {len(rows)} rows from {csv_path.name} (limit={args.limit}).")
    print(f"Skipping {skipped_non_monthly} non-monthly rows. Labeling {len(to_label)} rows with {args.model}...")

    client = AsyncOpenAI()
    sem = asyncio.Semaphore(args.concurrency)
    tasks = [label_row(client, sem, args.model, row, idx) for idx, row in to_label]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda r: r["csv_id"])

    errors = [r for r in results if r["error"] is not None]
    ok_ids = [r["csv_id"] for r in results if r["error"] is None]

    random.seed(args.seed)
    sample_size = max(1, round(len(ok_ids) * args.review_fraction)) if ok_ids else 0
    random_sample_ids = set(random.sample(ok_ids, k=min(sample_size, len(ok_ids)))) if ok_ids else set()

    review_records = []
    for r in results:
        reasons = build_review_reasons(r)
        if r["csv_id"] in random_sample_ids:
            reasons.append("random_sample")
        if not reasons:
            continue
        entry = {
            "csv_id": r["csv_id"],
            "review_reasons": reasons,
            "fields": r["fields"],
            "error": r["error"],
            "human_verdict": human_verdict_skeleton() if r["fields"] is not None else None,
        }
        review_records.append(entry)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = csv_path.stem
    main_path = OUT_DIR / f"ground_truth_{stem}_n{args.limit}_{ts}.json"
    review_path = OUT_DIR / f"human_review_sample_{stem}_n{args.limit}_{ts}.json"

    metadata = {
        "source_csv": str(csv_path.relative_to(BENCH_DIR)) if BENCH_DIR in csv_path.parents else str(csv_path),
        "row_limit_requested": args.limit,
        "rows_read": len(rows),
        "skipped_non_monthly": skipped_non_monthly,
        "labeled": len(results),
        "label_errors": len(errors),
        "model": args.model,
        "generated_at": ts,
        "review_fraction": args.review_fraction,
        "review_seed": args.seed,
        "review_sample_count": len(random_sample_ids),
        "review_total_count": len(review_records),
    }

    with open(main_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "records": results}, f, indent=2, ensure_ascii=False)

    with open(review_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "review_records": review_records}, f, indent=2, ensure_ascii=False)

    reason_counts = {"random_sample": 0, "low_confidence": 0, "negation_case": 0, "label_error": 0}
    for entry in review_records:
        for reason in entry["review_reasons"]:
            reason_counts[reason] += 1

    print(f"\nWrote {len(results)} labeled records -> {main_path}")
    print(f"Wrote {len(review_records)} review records -> {review_path}")
    print(f"  reasons (a record can have more than one): {reason_counts}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", default=str(DEFAULT_CSV), help="path to the source CSV (default: TestingDataSet/apartments_for_rent_classified_10K.csv)")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="read only the first N rows of the CSV (default: 50)")
    p.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model for labeling (default: gpt-4o-mini)")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="max concurrent LLM calls")
    p.add_argument("--review-fraction", type=float, default=DEFAULT_REVIEW_FRACTION, help="fraction of labeled rows to randomly pull into the human-review sample (default: 0.18)")
    p.add_argument("--seed", type=int, default=42, help="random seed for the review sample (default: 42)")
    return p.parse_args()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run(parse_args()))
