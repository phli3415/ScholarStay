"""
Samples N already-imported real houses (id >= SOURCE_ID_BASE, i.e. rows that
came from app/dataProcessing/import_csv_to_db.py) from the Houses table, for
use as the seed set in generate_queries_from_houses.py.

This is a separate benchmark from benchmark/test_data.json + run_benchmark.py
(which uses 45 synthetic Amherst houses). Here the houses are real, imported
CSV listings; queries are generated FROM each house (see
generate_queries_from_houses.py) rather than hand-written, and "ground truth"
for a generated query is just its own source house -- see that script's
docstring for why, and for the known limitation this implies for loosely-
constrained queries.

Only fields relevant to query generation / SQL constraints / semantic search
are exported (not owner, image_data, etc).

Usage (from BackendApplication/):
    python benchmark/sample_real_houses.py
    python benchmark/sample_real_houses.py --n 400 --seed 7
"""
import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

BENCH_DIR = Path(__file__).resolve().parent
OUT_DIR = BENCH_DIR / "RealDataRAG"

from app.dataProcessing.constants import SOURCE_ID_BASE

FIELDS = [
    "id", "province", "city", "street", "house_number", "monthly_rent",
    "has_kitchen", "has_washer", "has_parking", "is_rented",
    "distance_to_university", "description",
]


async def run(args) -> None:
    from tortoise import Tortoise
    from app.database import TORTOISE_ORM
    from app.model.houses import Houses

    await Tortoise.init(config=TORTOISE_ORM)

    candidates = await Houses.filter(id__gte=SOURCE_ID_BASE).all()
    await Tortoise.close_connections()

    if not candidates:
        print(f"No CSV-imported houses found (id >= {SOURCE_ID_BASE}). "
              f"Run app/dataProcessing/import_csv_to_db.py first.", file=sys.stderr)
        sys.exit(1)

    # description is required: queries are generated partly from free text
    usable = [h for h in candidates if (h.description or "").strip()]
    dropped = len(candidates) - len(usable)

    random.seed(args.seed)
    n = min(args.n, len(usable))
    sampled = random.sample(usable, k=n)

    houses_out = []
    for h in sampled:
        row = {}
        for f in FIELDS:
            v = getattr(h, f)
            if f in ("monthly_rent", "distance_to_university") and v is not None:
                v = float(v)
            row[f] = v
        houses_out.append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"sampled_houses_n{n}_{ts}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "candidates_available": len(candidates),
                "dropped_no_description": dropped,
                "sampled": n,
                "seed": args.seed,
                "generated_at": ts,
            },
            "houses": houses_out,
        }, f, indent=2, ensure_ascii=False)

    print(f"Candidates (id >= {SOURCE_ID_BASE}): {len(candidates)}")
    print(f"Dropped (no description): {dropped}")
    print(f"Sampled: {n}")
    print(f"Wrote {out_path}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=350, help="number of houses to sample (default: 350)")
    p.add_argument("--seed", type=int, default=42, help="random seed (default: 42)")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
