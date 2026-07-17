"""
Scores the CSV -> Houses import pipeline against a ground-truth file produced
by generate_ground_truth.py.

For every ground-truth record, looks up the Houses row with the same id
(csv_id = SOURCE_ID_BASE + csv_row_index, matching how import_csv_to_db.py
assigns ids -- see app/dataProcessing/constants.py) and compares the 8
target fields (province, city, street, house_number, monthly_rent,
has_kitchen, has_washer, has_parking).

Two metrics:
  - recall: fraction of ground-truth rows that were actually found in the
    houses table at all (rows the import pipeline skipped, e.g. via its
    MIN_NULL_THRESHOLD quality gate, count against recall).
  - accuracy: among matched rows, per-field and overall agreement between
    the DB value and the ground-truth value. A text/numeric field is
    excluded from accuracy scoring when the ground truth itself has no
    evidence (fields[field]["source"] == "none") -- there is nothing to
    check it against. The has_kitchen/has_washer/has_parking booleans are
    always scored, since "false" is a well-defined value (both the ground
    truth and the DB schema use false as the no-evidence default).

Known limitation: text-field comparison is exact (case/whitespace
insensitive) with no state-name/abbreviation normalization, so e.g. a
ground-truth "Massachusetts" vs a DB "MA" will show up as a mismatch even
though a human would call that correct. Inspect the mismatches list for
false positives like this before trusting the accuracy number too literally.

Usage (from BackendApplication/):
    python benchmark/score_against_db.py
    python benchmark/score_against_db.py --ground-truth benchmark/GroundTruth/ground_truth_apartments_for_rent_classified_10K_n50_20260716T073440Z.json
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

BENCH_DIR = Path(__file__).resolve().parent
GT_DIR = BENCH_DIR / "GroundTruth"

FIELD_NAMES = [
    "province", "city", "street", "house_number", "monthly_rent",
    "has_kitchen", "has_washer", "has_parking",
]
BOOL_FIELDS = {"has_kitchen", "has_washer", "has_parking"}
NUMERIC_FIELDS = {"monthly_rent"}
TEXT_FIELDS = {"province", "city", "street", "house_number"}


def norm_text(v):
    if v is None:
        return None
    s = str(v).strip()
    return s.lower() if s else None


def texts_match(gt_value, db_value) -> bool:
    return norm_text(gt_value) == norm_text(db_value)


def numbers_match(gt_value, db_value, tol: float = 0.01) -> bool:
    if gt_value is None or db_value is None:
        return gt_value is None and db_value is None
    return abs(float(gt_value) - float(db_value)) <= tol


def find_latest_ground_truth_file() -> Path:
    candidates = sorted(GT_DIR.glob("ground_truth_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print(f"No ground_truth_*.json files found in {GT_DIR}", file=sys.stderr)
        sys.exit(1)
    return candidates[0]


def compare_record(gt_record: dict, house) -> list[dict]:
    """Returns a list of mismatch dicts (empty if every scored field agrees)."""
    mismatches = []
    fields = gt_record["fields"]
    for field in FIELD_NAMES:
        gt_field = fields[field]
        gt_value = gt_field["value"]
        db_value = getattr(house, field)

        if field in BOOL_FIELDS:
            match = bool(gt_value) == bool(db_value)
        else:
            if gt_field["source"] == "none":
                continue  # no ground-truth evidence to check this field against
            if field in NUMERIC_FIELDS:
                match = numbers_match(gt_value, db_value)
            else:
                match = texts_match(gt_value, db_value)

        if not match:
            mismatches.append({
                "csv_id": gt_record["csv_id"],
                "field": field,
                "gt_value": gt_value,
                "gt_source": gt_field["source"],
                "gt_confidence": gt_field["confidence"],
                "gt_quote": gt_field.get("quote"),
                "db_value": db_value if not hasattr(db_value, "__float__") else float(db_value),
            })
    return mismatches


async def run(args) -> None:
    from tortoise import Tortoise
    from app.database import TORTOISE_ORM
    from app.model.houses import Houses

    gt_path = Path(args.ground_truth) if args.ground_truth else find_latest_ground_truth_file()
    if not gt_path.exists():
        print(f"Ground truth file not found: {gt_path}", file=sys.stderr)
        sys.exit(1)

    with open(gt_path, encoding="utf-8") as f:
        gt_data = json.load(f)

    all_records = gt_data["records"]
    label_errors = [r for r in all_records if r["error"] is not None]
    scorable_records = [r for r in all_records if r["error"] is None]

    print(f"Loaded {len(all_records)} ground-truth records from {gt_path.name} "
          f"({len(label_errors)} label errors excluded).")

    await Tortoise.init(config=TORTOISE_ORM)

    ids = [r["csv_id"] for r in scorable_records]
    houses = await Houses.filter(id__in=ids).all()
    houses_by_id = {h.id: h for h in houses}

    missing_records = []
    mismatches = []
    field_scored = {f: 0 for f in FIELD_NAMES}
    field_correct = {f: 0 for f in FIELD_NAMES}

    for r in scorable_records:
        house = houses_by_id.get(r["csv_id"])
        if house is None:
            missing_records.append(r["csv_id"])
            continue

        fields = r["fields"]
        for field in FIELD_NAMES:
            gt_field = fields[field]
            if field not in BOOL_FIELDS and gt_field["source"] == "none":
                continue
            field_scored[field] += 1

        record_mismatches = compare_record(r, house)
        mismatched_fields = {m["field"] for m in record_mismatches}
        for field in FIELD_NAMES:
            if field in mismatched_fields:
                continue
            gt_field = fields[field]
            if field not in BOOL_FIELDS and gt_field["source"] == "none":
                continue
            field_correct[field] += 1

        mismatches.extend(record_mismatches)

    await Tortoise.close_connections()

    matched_count = len(scorable_records) - len(missing_records)
    recall = matched_count / len(scorable_records) if scorable_records else 0.0

    total_scored = sum(field_scored.values())
    total_correct = sum(field_correct.values())
    overall_accuracy = total_correct / total_scored if total_scored else 0.0

    field_accuracy = {
        f: {
            "scored": field_scored[f],
            "correct": field_correct[f],
            "accuracy": (field_correct[f] / field_scored[f]) if field_scored[f] else None,
        }
        for f in FIELD_NAMES
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "metadata": {
            "ground_truth_file": gt_path.name,
            "scored_at": ts,
            "total_gt_records": len(all_records),
            "label_errors_excluded": len(label_errors),
            "scorable_records": len(scorable_records),
            "matched_in_db": matched_count,
            "missing_from_db": len(missing_records),
            "recall": recall,
            "overall_accuracy": overall_accuracy,
        },
        "field_accuracy": field_accuracy,
        "mismatches": mismatches,
        "missing_records": missing_records,
    }

    report_path = GT_DIR / f"score_report_{gt_path.stem}_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nRecall (found in houses table): {matched_count}/{len(scorable_records)} = {recall:.1%}")
    print(f"\n{'field':<16}{'scored':<9}{'correct':<9}{'accuracy'}")
    for f in FIELD_NAMES:
        fa = field_accuracy[f]
        acc_str = f"{fa['accuracy']:.1%}" if fa["accuracy"] is not None else "n/a"
        print(f"{f:<16}{fa['scored']:<9}{fa['correct']:<9}{acc_str}")
    print(f"{'OVERALL':<16}{total_scored:<9}{total_correct:<9}{overall_accuracy:.1%}")
    print(f"\n{len(mismatches)} field-level mismatches, {len(missing_records)} rows missing from DB.")
    print(f"Full report written to {report_path}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ground-truth", default=None, help="path to a ground_truth_*.json file (default: most recently modified one in benchmark/GroundTruth/)")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
