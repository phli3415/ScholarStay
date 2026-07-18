"""
Generates one natural-language search query per sampled real house (see
sample_real_houses.py), for round-trip retrieval testing of the agentic
workflow against real (not synthetic) listings.

Methodology (discussed and agreed on before writing this):
  - The script -- not the LLM -- decides WHICH requirement slots go into a
    given query (1-5, randomly sampled from what's actually true/available
    for that house), so difficulty tiers are controlled and reproducible,
    not left to the model's whim.
  - Slots come from two pools: structured (max_monthly_rent, has_kitchen,
    has_washer, has_parking -- only offered when the house actually has the
    amenity) and semantic (a soft quality like "quiet" or "convenient" that
    must be genuinely supported by the house's free-text description, not
    invented). A query may mix both kinds.
  - The LLM's only job is to phrase the selected slots as ONE short, casual,
    human-sounding search message -- explicitly NOT clinical field-listing
    language -- to avoid generating queries that are unnaturally easy for a
    same-family model to parse back into structured constraints later.
  - "Ground truth" for a generated query is its own source house. This is
    known to be an imperfect signal for loosely-constrained queries (another
    real house could equally satisfy a 1-constraint query), which is why
    run_real_data_benchmark.py's misses go through a separate human-review
    pass rather than being scored as hard failures.

Usage (from BackendApplication/):
    python benchmark/generate_queries_from_houses.py --houses benchmark/RealDataRAG/sampled_houses_n350_<ts>.json
"""
import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BENCH_DIR = Path(__file__).resolve().parent
OUT_DIR = BENCH_DIR / "RealDataRAG"

MODEL = "gpt-4o-mini"
DEFAULT_CONCURRENCY = 6
MAX_ATTEMPTS = 3
GENERATION_TEMPERATURE = 0.9  # want varied, human-like phrasing, not deterministic

SEMANTIC_HINTS = [
    "quiet", "convenient location", "spacious", "bright / well-lit",
    "well-maintained / good condition", "cozy", "walkable area",
    "family-friendly", "good for a single person", "close-knit / friendly building",
]


class ConstraintSlot(str, Enum):
    RENT = "max_monthly_rent"
    KITCHEN = "has_kitchen"
    WASHER = "has_washer"
    PARKING = "has_parking"
    SEMANTIC = "semantic"


class GeneratedQuery(BaseModel):
    query: str = Field(..., description="one short, casual, natural-sounding housing search message, as a real person would type it")
    used_constraint_types: list[str] = Field(
        ..., description="which requested slots actually made it into the query verbatim in spirit; drop 'semantic' from this list (and from the query) if the description doesn't genuinely support any nameable quality"
    )
    semantic_quality_used: Optional[str] = Field(
        None, description="if a semantic slot was used, name the specific quality (e.g. 'quiet') the query expresses; null otherwise"
    )


SYSTEM_PROMPT = """You are helping build a search-retrieval test set. You are NOT a query-understanding assistant -- your job is the reverse: given the full facts about one specific rental listing, imagine a real prospective renter who is casually describing what they want, without knowing this listing exists yet, in a way that this listing happens to satisfy.

Rules:
1. You will be told exactly which requirement slots to weave into the message. Use all of them, and ONLY them. You are ONLY given facts for the requested slots below -- there is nothing else to draw on, so there is no other requirement you could truthfully add even if you wanted to.
2. NO FILLER: do not pad the message with generic descriptive phrases that aren't one of the requested slots -- no "nice area," "good amenities," "friendly community," "great location" etc. unless "semantic" is a requested slot AND the phrase is the specific quality you named in semantic_quality_used. A message with only 1 requested slot should read like it's asking for exactly 1 thing, not several wrapped in pleasantries.
3. Write ONE short, casual message (like a text or chat message to a rental search bot) -- not a polished sentence, not a structured field-by-field listing of requirements. Vary phrasing, tone, and sentence structure between calls; do not default to a formulaic template.
4. Never use precise field-name language ("monthly_rent", "has_parking") -- describe things the way a real person would ("under $1200", "somewhere with parking").
5. For a "max_monthly_rent" slot, pick a round number that is AT OR ABOVE the listing's actual rent (so the listing genuinely satisfies the constraint you write) -- do not just restate the exact rent.
6. For a "semantic" slot: only use it if the DESCRIPTION text genuinely, specifically supports a nameable quality (see the hint list). If the description is too generic/short to genuinely support any of them, do NOT invent one -- drop the semantic slot entirely, set semantic_quality_used to null, and leave "semantic" out of used_constraint_types.
7. used_constraint_types and semantic_quality_used MUST agree: if you set semantic_quality_used to a non-null value, "semantic" MUST appear in used_constraint_types; if semantic_quality_used is null, "semantic" MUST NOT appear in used_constraint_types.
8. Do not mention the address, exact rent figure, or anything that would make it obvious you're describing this specific listing verbatim -- write it the way someone would search BEFORE finding a place, not describing one they already found."""


def build_user_prompt(house: dict, requested_slots: list[str]) -> str:
    """
    Only include facts for the requested slots. This is deliberate: an
    earlier version showed the model the full listing "for reference only"
    and told it not to leak unrequested facts, but gpt-4o-mini did so anyway
    (e.g. mentioning "has a kitchen" in a rent-only query). Not showing the
    field at all is a more reliable way to keep it out of the generated
    query than asking the model to withhold information it can see.
    """
    lines = ["LISTING FACTS (for your reference only, do not quote directly):"]
    if ConstraintSlot.RENT.value in requested_slots:
        lines.append(f"  monthly_rent: {house['monthly_rent']}")
    if ConstraintSlot.KITCHEN.value in requested_slots:
        lines.append(f"  has_kitchen: {house['has_kitchen']}")
    if ConstraintSlot.WASHER.value in requested_slots:
        lines.append(f"  has_washer: {house['has_washer']}")
    if ConstraintSlot.PARKING.value in requested_slots:
        lines.append(f"  has_parking: {house['has_parking']}")
    if ConstraintSlot.SEMANTIC.value in requested_slots:
        lines.append(f"  description: {house.get('description') or '(none)'}")

    lines += [
        "",
        f"REQUESTED SLOTS to weave into the message (this is the complete list -- you have no facts about anything else): {requested_slots}",
    ]
    if ConstraintSlot.SEMANTIC.value in requested_slots:
        lines.append(
            f"\nCandidate semantic qualities (only use one if genuinely supported by the description above): {', '.join(SEMANTIC_HINTS)}"
        )
    return "\n".join(lines)


def pick_slots(house: dict, rng: random.Random) -> list[str]:
    pool = [ConstraintSlot.RENT.value]
    if house["has_kitchen"]:
        pool.append(ConstraintSlot.KITCHEN.value)
    if house["has_washer"]:
        pool.append(ConstraintSlot.WASHER.value)
    if house["has_parking"]:
        pool.append(ConstraintSlot.PARKING.value)
    if len((house.get("description") or "").strip()) >= 20:
        pool.append(ConstraintSlot.SEMANTIC.value)

    target = rng.randint(1, min(5, len(pool)))
    return rng.sample(pool, k=target)


async def generate_one(client, sem: asyncio.Semaphore, house: dict, requested_slots: list[str]) -> dict:
    base = {
        "source_house_id": house["id"],
        "requested_slots": requested_slots,
    }
    prompt = build_user_prompt(house, requested_slots)
    async with sem:
        last_err = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                completion = await client.beta.chat.completions.parse(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    response_format=GeneratedQuery,
                    temperature=GENERATION_TEMPERATURE,
                )
                parsed = completion.choices[0].message.parsed
                if parsed is None:
                    raise ValueError("model returned no parsed output (refusal or empty)")
                return {**base, "result": json.loads(parsed.model_dump_json()), "error": None}
            except Exception as e:
                last_err = str(e)
                if attempt < MAX_ATTEMPTS - 1:
                    await asyncio.sleep(1.5 * (attempt + 1))
        return {**base, "result": None, "error": last_err}


async def run(args) -> None:
    load_dotenv()
    from openai import AsyncOpenAI

    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set (checked environment and .env). Aborting.", file=sys.stderr)
        sys.exit(1)

    houses_path = Path(args.houses)
    with open(houses_path, encoding="utf-8") as f:
        data = json.load(f)
    houses = data["houses"]

    rng = random.Random(args.seed)
    requested = [(h, pick_slots(h, rng)) for h in houses]

    print(f"Generating {len(requested)} queries with {MODEL} (concurrency={args.concurrency})...")

    client = AsyncOpenAI()
    sem = asyncio.Semaphore(args.concurrency)
    tasks = [generate_one(client, sem, h, slots) for h, slots in requested]
    results = await asyncio.gather(*tasks)

    errors = [r for r in results if r["error"] is not None]
    ok = [r for r in results if r["error"] is None]

    queries_out = []
    for r in ok:
        res = r["result"]
        requested_set = set(r["requested_slots"])
        used_set = set(res["used_constraint_types"])
        semantic_quality = res["semantic_quality_used"]

        # Don't trust the model's self-reported bookkeeping as-is (it was observed
        # to sometimes set semantic_quality_used without listing "semantic" in
        # used_constraint_types). Reconcile from semantic_quality_used, which is
        # the more reliable signal, then drop anything not actually requested
        # (defensive -- should be moot now that the prompt forbids it, but don't
        # silently let constraint_count be inflated if it slips through anyway).
        if semantic_quality:
            used_set.add(ConstraintSlot.SEMANTIC.value)
        else:
            used_set.discard(ConstraintSlot.SEMANTIC.value)
        used_set &= requested_set

        used_list = sorted(used_set)
        queries_out.append({
            "source_house_id": r["source_house_id"],
            "requested_slots": r["requested_slots"],
            "query": res["query"],
            "used_constraint_types": used_list,
            "constraint_count": len(used_list),
            "semantic_quality_used": semantic_quality if ConstraintSlot.SEMANTIC.value in used_list else None,
            "has_semantic": ConstraintSlot.SEMANTIC.value in used_list,
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"generated_queries_n{len(queries_out)}_{ts}.json"

    tier_counts = {}
    for q in queries_out:
        tier_counts[q["constraint_count"]] = tier_counts.get(q["constraint_count"], 0) + 1
    semantic_count = sum(1 for q in queries_out if q["has_semantic"])

    metadata = {
        "source_houses_file": str(houses_path.name),
        "model": MODEL,
        "temperature": GENERATION_TEMPERATURE,
        "seed": args.seed,
        "requested": len(requested),
        "generated": len(queries_out),
        "generation_errors": len(errors),
        "constraint_count_distribution": tier_counts,
        "queries_with_semantic_slot": semantic_count,
        "generated_at": ts,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "queries": queries_out, "errors": errors}, f, indent=2, ensure_ascii=False)

    print(f"\nGenerated: {len(queries_out)}, errors: {len(errors)}")
    print(f"Constraint-count distribution: {tier_counts}")
    print(f"Queries using a semantic slot: {semantic_count}")
    print(f"Wrote {out_path}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--houses", required=True, help="path to a sampled_houses_*.json file from sample_real_houses.py")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--seed", type=int, default=42, help="random seed for slot selection (default: 42)")
    return p.parse_args()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run(parse_args()))
