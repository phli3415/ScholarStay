"""
Generates one natural-language search query per sampled real house (see
sample_real_houses.py), for round-trip retrieval testing of the agentic
workflow against real (not synthetic) listings.

Methodology (v2 -- revised after v1 produced only 0-1 constraint queries that
were too loose to distinguish "system found a different, equally valid house"
from "system actually failed"):
  - No more random subsampling of requirement slots. The model is shown
    EVERY structured fact that is actually true for the house (monthly_rent
    always; has_kitchen/has_washer/has_parking only when true) plus the full
    description, and is told to weave ALL of it into one query. How many
    "requirements" a query ends up with is therefore a property of how much
    is genuinely true/known about that house, not a number the script picked
    in advance.
  - Semantic (soft) qualities from the description are no longer capped at
    one. If the description separately supports more than one distinct,
    nameable quality (e.g. "quiet, close to shops" supports both "quiet" AND
    "convenient location"), each counts as its own requirement. Restating
    the same idea in different words does not.
  - The LLM's only job is to phrase everything true as ONE short, casual,
    human-sounding search message -- explicitly NOT clinical field-listing
    language -- while staying specific enough that not hundreds of other
    listings would equally satisfy it.
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
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

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


class GeneratedQuery(BaseModel):
    query: str = Field(..., description="one short, casual, natural-sounding housing search message, as a real person would type it")
    used_structured_slots: list[str] = Field(
        ..., description="which of the true structured facts you were given actually made it into the message"
    )
    semantic_qualities_used: list[str] = Field(
        ..., description="every distinct, genuinely-supported quality from the hint list that you wove into the message; empty list if the description doesn't specifically support any"
    )


SYSTEM_PROMPT = """You are helping build a search-retrieval test set. You are NOT a query-understanding assistant -- your job is the reverse: given every true fact about one specific rental listing, imagine a real prospective renter who is casually describing what they want, without knowing this listing exists yet, in a way that this listing happens to satisfy.

Rules:
1. You are given ALL structured facts that are true for this listing (monthly_rent, plus whichever of has_kitchen/has_washer/has_parking are true -- amenities that are false are simply not shown to you, since there's nothing to ask for). Weave ALL of the true structured facts into the message. Do not omit one to keep the message short -- a real message can casually list several wants in a row.
2. Read the DESCRIPTION and identify EVERY distinct, nameable quality from the hint list that it genuinely, specifically supports -- not just one. Two qualities count separately only if the description gives separable evidence for each (e.g. "quiet street, close to shops" supports both "quiet" AND "convenient location"). Do NOT count the same idea restated in different words as two qualities, and do NOT invent a quality the description doesn't clearly support. If nothing is clearly supported, semantic_qualities_used is an empty list -- do not pad it.
3. Weave in every quality you identified in step 2, alongside the structured facts from step 1, into ONE message.
4. SPECIFICITY TARGET: the whole point of this message is that it should describe a fairly narrow slice of the rental market -- specific enough that only a small number of real listings nationwide would plausibly satisfy everything in it, not so vague that hundreds of unrelated listings would equally match. Using everything you were given (per rules 1-3) is how you achieve this -- don't strip things out for the sake of brevity.
5. Write ONE short, casual message (like a text or chat message to a rental search bot) -- not a polished sentence, not a structured field-by-field listing of requirements. Vary phrasing, tone, and sentence structure between calls; do not default to a formulaic template, even when listing several wants.
6. Never use precise field-name language ("monthly_rent", "has_parking") -- describe things the way a real person would ("under $1200", "somewhere with parking").
7. For monthly_rent, pick a round number that is AT OR ABOVE the listing's actual rent (so the listing genuinely satisfies the constraint you write) -- do not just restate the exact rent.
8. Do not mention the address, exact rent figure, or anything that would make it obvious you're describing this specific listing verbatim -- write it the way someone would search BEFORE finding a place, not describing one they already found."""


def build_user_prompt(house: dict) -> str:
    lines = ["LISTING FACTS (for your reference only, do not quote directly):",
             f"  monthly_rent: {house['monthly_rent']}"]
    if house["has_kitchen"]:
        lines.append(f"  has_kitchen: true")
    if house["has_washer"]:
        lines.append(f"  has_washer: true")
    if house["has_parking"]:
        lines.append(f"  has_parking: true")
    lines.append(f"  description: {house.get('description') or '(none)'}")
    lines.append(f"\nCandidate semantic qualities (use every one genuinely, specifically supported by the description above -- see rule 2): {', '.join(SEMANTIC_HINTS)}")
    return "\n".join(lines)


def true_structured_slots(house: dict) -> set[str]:
    slots = {ConstraintSlot.RENT.value}
    if house["has_kitchen"]:
        slots.add(ConstraintSlot.KITCHEN.value)
    if house["has_washer"]:
        slots.add(ConstraintSlot.WASHER.value)
    if house["has_parking"]:
        slots.add(ConstraintSlot.PARKING.value)
    return slots


async def generate_one(client, sem: asyncio.Semaphore, house: dict) -> dict:
    base = {"source_house_id": house["id"]}
    prompt = build_user_prompt(house)
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

    print(f"Generating {len(houses)} queries with {MODEL} (concurrency={args.concurrency})...")

    client = AsyncOpenAI()
    sem = asyncio.Semaphore(args.concurrency)
    tasks = [generate_one(client, sem, h) for h in houses]
    results = await asyncio.gather(*tasks)

    houses_by_id = {h["id"]: h for h in houses}
    errors = [r for r in results if r["error"] is not None]
    ok = [r for r in results if r["error"] is None]

    queries_out = []
    for r in ok:
        res = r["result"]
        house = houses_by_id[r["source_house_id"]]
        available = true_structured_slots(house)

        # Defensive: only count structured slots that were actually true for
        # this house, regardless of what the model claims -- guards against
        # the model reporting a slot it wasn't given.
        used_structured = sorted(set(res["used_structured_slots"]) & available)
        semantic_qualities = list(dict.fromkeys(res["semantic_qualities_used"]))  # dedupe, keep order

        queries_out.append({
            "source_house_id": r["source_house_id"],
            "query": res["query"],
            "used_structured_slots": used_structured,
            "semantic_qualities_used": semantic_qualities,
            "constraint_count": len(used_structured) + len(semantic_qualities),
            "has_semantic": len(semantic_qualities) > 0,
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
        "requested": len(houses),
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
    print(f"Queries using at least one semantic quality: {semantic_count}")
    print(f"Wrote {out_path}")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--houses", required=True, help="path to a sampled_houses_*.json file from sample_real_houses.py")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    return p.parse_args()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run(parse_args()))
