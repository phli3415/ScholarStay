"""
Reads a review_misses_*.json file (from run_real_data_benchmark.py) after
you've filled in each record's human_verdict.is_false_negative, and
recomputes hit rate with false negatives reclassified as hits.

Reports BOTH the raw hit rate (source-house-only ground truth) and the
verdict-adjusted hit rate, stratified by constraint count and by
semantic/structured-only, so the gap between them is visible rather than
collapsed into one number -- see run_real_data_benchmark.py's docstring for
why the raw number alone is a noisy signal.

Usage (from BackendApplication/):
    python benchmark/apply_review_verdicts.py \\
        --results benchmark/RealDataRAG/results_n350_<ts>.json \\
        --review benchmark/RealDataRAG/review_misses_n40_<ts>.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
OUT_DIR = BENCH_DIR / "RealDataRAG"


def hit_rate(rows, key="hit_at_k"):
    ok = [r for r in rows if r.get("error") is None]
    if not ok:
        return None
    return sum(1 for r in ok if r[key]) / len(ok)


def stratify(results, key="hit_at_k"):
    by_count = {}
    for c in range(1, 6):
        rows = [r for r in results if r.get("constraint_count") == c]
        if rows:
            by_count[c] = {"n": len(rows), "hit_rate": hit_rate(rows, key)}
    semantic_rows = [r for r in results if r.get("has_semantic")]
    structured_rows = [r for r in results if not r.get("has_semantic")]
    return {
        "overall": hit_rate(results, key),
        "by_constraint_count": by_count,
        "semantic_queries": {"n": len(semantic_rows), "hit_rate": hit_rate(semantic_rows, key)},
        "structured_only_queries": {"n": len(structured_rows), "hit_rate": hit_rate(structured_rows, key)},
    }


def main(args) -> None:
    with open(args.results, encoding="utf-8") as f:
        results = json.load(f)
    with open(args.review, encoding="utf-8") as f:
        review = json.load(f)["review_records"]

    unreviewed = [r for r in review if r["human_verdict"]["is_false_negative"] is None]
    if unreviewed:
        print(f"WARNING: {len(unreviewed)}/{len(review)} review records still have "
              f"human_verdict.is_false_negative = null (not yet reviewed). "
              f"Treating them as true misses for now.", file=sys.stderr)

    false_negative_house_ids = {
        r["source_house_id"] for r in review
        if r["human_verdict"]["is_false_negative"] is True
    }

    for r in results:
        if r.get("error") is not None:
            continue
        r["hit_at_k_adjusted"] = r["hit_at_k"] or (r["source_house_id"] in false_negative_house_ids)

    raw = stratify(results, key="hit_at_k")
    adjusted = stratify(results, key="hit_at_k_adjusted")

    report = {
        "metadata": {
            "results_file": Path(args.results).name,
            "review_file": Path(args.review).name,
            "total_queries": len(results),
            "total_misses_reviewed": len(review),
            "false_negatives_found": len(false_negative_house_ids),
            "true_misses": len(review) - len(false_negative_house_ids),
            "unreviewed_records": len(unreviewed),
        },
        "raw": raw,
        "adjusted": adjusted,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"final_report_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nTotal queries: {report['metadata']['total_queries']}")
    print(f"Misses reviewed: {report['metadata']['total_misses_reviewed']} "
          f"(false negatives: {report['metadata']['false_negatives_found']}, "
          f"true misses: {report['metadata']['true_misses']}, "
          f"unreviewed: {report['metadata']['unreviewed_records']})")
    print(f"\n{'':20}{'raw':<10}{'adjusted'}")
    print(f"{'overall':20}{raw['overall']:.1%}{'':6}{adjusted['overall']:.1%}")
    for c in sorted(raw["by_constraint_count"]):
        r_hr = raw["by_constraint_count"][c]["hit_rate"]
        a_hr = adjusted["by_constraint_count"][c]["hit_rate"]
        n = raw["by_constraint_count"][c]["n"]
        print(f"{'tier ' + str(c) + f' (n={n})':20}{r_hr:.1%}{'':6}{a_hr:.1%}")
    print(f"{'semantic':20}{raw['semantic_queries']['hit_rate']:.1%}{'':6}{adjusted['semantic_queries']['hit_rate']:.1%}")
    print(f"{'structured-only':20}{raw['structured_only_queries']['hit_rate']:.1%}{'':6}{adjusted['structured_only_queries']['hit_rate']:.1%}")
    print(f"\nWrote {out_path}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results", required=True, help="path to results_*.json from run_real_data_benchmark.py")
    p.add_argument("--review", required=True, help="path to the filled-in review_misses_*.json")
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
