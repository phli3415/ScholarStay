"""
Generates benchmark/test_data.json for the ScholarStay agentic workflow.

Produces:
  - 45 synthetic Amherst-area houses with rent/distance/amenities sampled
    independently of each other (fixed random seed, reproducible), so
    benchmark queries that combine constraints aren't confounded by
    correlated attributes (e.g. "cheap houses are always far").
  - 36 hand-written natural-language queries across 4 constraint-count
    tiers (1/2/3/4-5 constraints), each with a `constraints` dict describing
    the intended filter and a programmatically-computed
    `ground_truth_bench_ids` (which houses actually satisfy those
    constraints in this fixed house list, per `bench_id`).

Some tier-4 queries are deliberately tight/infeasible (0 ground-truth
matches) to exercise the workflow's relax-and-retry loop.

Run with: python generate_test_data.py  (writes test_data.json next to this file)
"""
import json
import random
from pathlib import Path

random.seed(42)

STREETS = [
    "North Pleasant St", "South Pleasant St", "Fearing St", "Amity St",
    "Triangle St", "South East St", "Main St", "Belchertown Rd",
    "Lincoln Ave", "North Prospect St", "Bay Rd", "Sunset Ave",
    "East Pleasant St", "Northampton Rd", "Meadow St", "Butternut Dr",
    "Gray St", "Dickinson St", "Hallock St", "Cowls Rd",
    "Pomeroy Ln", "West St", "Snell St", "Farmington Rd",
]

RENT_BUCKETS = [500, 600, 650, 700, 750, 800, 850, 900, 950, 1000,
                1050, 1100, 1200, 1300, 1400, 1500, 1650, 1800, 2000, 2200, 2400, 2600]

DISTANCE_BUCKETS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5,
                     1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 9.5]

DESCRIPTIONS = [
    "Bright and quiet, recently updated.",
    "Great natural light, walkable neighborhood.",
    "Simple and functional, good for a single student.",
    "Spacious layout with plenty of storage.",
    "Newly renovated with modern finishes.",
    "Classic New England charm, well maintained.",
    "Quiet street, friendly landlord, flexible lease.",
    "Close to bus line, easy commute either way.",
    "Shared common areas, active house community.",
    "Private entrance, good for those who value quiet.",
]


def make_house():
    return {
        "province": "MA",
        "city": "Amherst",
        "street": random.choice(STREETS),
        "house_number": str(random.randint(1, 950)),
        "monthly_rent": random.choice(RENT_BUCKETS),
        "distance_to_university": random.choice(DISTANCE_BUCKETS),
        "has_kitchen": random.random() < 0.55,
        "has_washer": random.random() < 0.5,
        "has_parking": random.random() < 0.45,
        "description": random.choice(DESCRIPTIONS),
    }


def generate_houses(n=45):
    houses = [make_house() for _ in range(n)]

    # de-dupe identical (street, house_number) pairs
    seen = set()
    for h in houses:
        key = (h["street"], h["house_number"])
        while key in seen:
            h["house_number"] = str(int(h["house_number"]) + 1)
            key = (h["street"], h["house_number"])
        seen.add(key)

    for i, h in enumerate(houses, start=1):
        h["bench_id"] = i
    return houses


QUERIES = [
    # ---- Tier 1: single constraint ----
    {"id": "t1_01", "tier": 1, "text": "Do you have anything under $700 a month?",
     "constraints": {"max_monthly_rent": 700}},
    {"id": "t1_02", "tier": 1, "text": "I need something within half a kilometer of campus.",
     "constraints": {"max_distance_to_university": 0.5}},
    {"id": "t1_03", "tier": 1, "text": "Looking for a place with a kitchen, that's basically my only requirement.",
     "constraints": {"has_kitchen": True}},
    {"id": "t1_04", "tier": 1, "text": "Is there anything with an in-unit washer?",
     "constraints": {"has_washer": True}},
    {"id": "t1_05", "tier": 1, "text": "I really just need parking, everything else is flexible.",
     "constraints": {"has_parking": True}},
    {"id": "t1_06", "tier": 1, "text": "My budget caps out at $1000 a month.",
     "constraints": {"max_monthly_rent": 1000}},
    {"id": "t1_07", "tier": 1, "text": "I want to be within a mile of UMass, roughly 1.6km.",
     "constraints": {"max_distance_to_university": 1.6}},
    {"id": "t1_08", "tier": 1, "text": "Anything under $2000 works for me.",
     "constraints": {"max_monthly_rent": 2000}},
    {"id": "t1_09", "tier": 1, "text": "I'd like a place close enough to walk, say under a kilometer.",
     "constraints": {"max_distance_to_university": 1.0}},

    # ---- Tier 2: two constraints ----
    {"id": "t2_01", "tier": 2, "text": "I want something under $1000 with a kitchen.",
     "constraints": {"max_monthly_rent": 1000, "has_kitchen": True}},
    {"id": "t2_02", "tier": 2, "text": "Need parking and it has to be under $1500 a month.",
     "constraints": {"has_parking": True, "max_monthly_rent": 1500}},
    {"id": "t2_03", "tier": 2, "text": "Looking for a place with a washer, within 2km of campus.",
     "constraints": {"has_washer": True, "max_distance_to_university": 2.0}},
    {"id": "t2_04", "tier": 2, "text": "Budget is $1200, and I'd like to be within 1km of school.",
     "constraints": {"max_monthly_rent": 1200, "max_distance_to_university": 1.0}},
    {"id": "t2_05", "tier": 2, "text": "I want a kitchen and I don't want to be more than 3km away.",
     "constraints": {"has_kitchen": True, "max_distance_to_university": 3.0}},
    {"id": "t2_06", "tier": 2, "text": "Something with parking under $900, if that exists.",
     "constraints": {"has_parking": True, "max_monthly_rent": 900}},
    {"id": "t2_07", "tier": 2, "text": "I need a washer and it should be under $1800.",
     "constraints": {"has_washer": True, "max_monthly_rent": 1800}},
    {"id": "t2_08", "tier": 2, "text": "Close to campus, like within 0.5km, and it needs a kitchen.",
     "constraints": {"max_distance_to_university": 0.5, "has_kitchen": True}},
    {"id": "t2_09", "tier": 2, "text": "Under $800 and has parking would be ideal.",
     "constraints": {"max_monthly_rent": 800, "has_parking": True}},

    # ---- Tier 3: three constraints ----
    {"id": "t3_01", "tier": 3, "text": "I need a kitchen, a washer, and it has to be under $1300.",
     "constraints": {"has_kitchen": True, "has_washer": True, "max_monthly_rent": 1300}},
    {"id": "t3_02", "tier": 3, "text": "Budget $1500, within 2km, and I need parking.",
     "constraints": {"max_monthly_rent": 1500, "max_distance_to_university": 2.0, "has_parking": True}},
    {"id": "t3_03", "tier": 3, "text": "Looking for something with a kitchen and washer, within 3km of campus.",
     "constraints": {"has_kitchen": True, "has_washer": True, "max_distance_to_university": 3.0}},
    {"id": "t3_04", "tier": 3, "text": "Under $1000, needs parking, and within 2.5km.",
     "constraints": {"max_monthly_rent": 1000, "has_parking": True, "max_distance_to_university": 2.5}},
    {"id": "t3_05", "tier": 3, "text": "I want a kitchen, under $2000, and close, say within 1km.",
     "constraints": {"has_kitchen": True, "max_monthly_rent": 2000, "max_distance_to_university": 1.0}},
    {"id": "t3_06", "tier": 3, "text": "Washer and parking both required, and budget's around $1600.",
     "constraints": {"has_washer": True, "has_parking": True, "max_monthly_rent": 1600}},
    {"id": "t3_07", "tier": 3, "text": "Kitchen and parking needed, has to be under a kilometer from campus.",
     "constraints": {"has_kitchen": True, "has_parking": True, "max_distance_to_university": 1.0}},
    {"id": "t3_08", "tier": 3, "text": "Under $900, with a kitchen, and needs to have a washer too.",
     "constraints": {"max_monthly_rent": 900, "has_kitchen": True, "has_washer": True}},
    {"id": "t3_09", "tier": 3, "text": "Looking for parking, a washer, and something under $2200.",
     "constraints": {"has_parking": True, "has_washer": True, "max_monthly_rent": 2200}},

    # ---- Tier 4+: four or five constraints (some deliberately infeasible to exercise the relax loop) ----
    {"id": "t4_01", "tier": 4, "text": "I need a kitchen, washer, and parking, under $1000, within 2km.",
     "constraints": {"has_kitchen": True, "has_washer": True, "has_parking": True,
                      "max_monthly_rent": 1000, "max_distance_to_university": 2.0}},
    {"id": "t4_02", "tier": 4, "text": "Budget $1500, within 1km, needs a kitchen and washer.",
     "constraints": {"max_monthly_rent": 1500, "max_distance_to_university": 1.0,
                      "has_kitchen": True, "has_washer": True}},
    {"id": "t4_03", "tier": 4, "text": "Kitchen, washer, parking all required, and it must be under $800.",
     "constraints": {"has_kitchen": True, "has_washer": True, "has_parking": True,
                      "max_monthly_rent": 800}},
    {"id": "t4_04", "tier": 4, "text": "Within 0.5km of campus, under $1000, with a kitchen and a washer.",
     "constraints": {"max_distance_to_university": 0.5, "max_monthly_rent": 1000,
                      "has_kitchen": True, "has_washer": True}},
    {"id": "t4_05", "tier": 4, "text": "I need everything: kitchen, washer, parking, under $1200, and within 2km.",
     "constraints": {"has_kitchen": True, "has_washer": True, "has_parking": True,
                      "max_monthly_rent": 1200, "max_distance_to_university": 2.0}},
    {"id": "t4_06", "tier": 4, "text": "Under $600, has a kitchen, a washer, and parking, and within 2km of campus.",
     "constraints": {"max_monthly_rent": 600, "has_kitchen": True, "has_washer": True,
                      "has_parking": True, "max_distance_to_university": 2.0}},
    {"id": "t4_07", "tier": 4, "text": "Kitchen, washer, parking, budget $2000, within 3km.",
     "constraints": {"has_kitchen": True, "has_washer": True, "has_parking": True,
                      "max_monthly_rent": 2000, "max_distance_to_university": 3.0}},
    {"id": "t4_08", "tier": 4, "text": "I want a kitchen, washer, and parking, under $1000, and within 0.3km — basically on campus.",
     "constraints": {"has_kitchen": True, "has_washer": True, "has_parking": True,
                      "max_monthly_rent": 1000, "max_distance_to_university": 0.3}},
    {"id": "t4_09", "tier": 4, "text": "Need parking, a washer, and a kitchen, under $700, within 0.4km of campus.",
     "constraints": {"has_parking": True, "has_washer": True, "max_monthly_rent": 700,
                      "max_distance_to_university": 0.4, "has_kitchen": True}},
]


def compute_ground_truth(queries, houses):
    for q in queries:
        c = q["constraints"]
        matches = []
        for h in houses:
            if "max_monthly_rent" in c and h["monthly_rent"] > c["max_monthly_rent"]:
                continue
            if "max_distance_to_university" in c and h["distance_to_university"] > c["max_distance_to_university"]:
                continue
            if "has_kitchen" in c and h["has_kitchen"] != c["has_kitchen"]:
                continue
            if "has_washer" in c and h["has_washer"] != c["has_washer"]:
                continue
            if "has_parking" in c and h["has_parking"] != c["has_parking"]:
                continue
            matches.append(h["bench_id"])
        q["ground_truth_bench_ids"] = matches
        q["ground_truth_count"] = len(matches)
    return queries


def main():
    houses = generate_houses()
    queries = compute_ground_truth(QUERIES, houses)

    data = {
        "description": (
            "Benchmark dataset for the ScholarStay agentic workflow. `houses` is a fixed, "
            "independently-distributed set of 45 synthetic Amherst listings (rent/distance/"
            "amenities are not correlated with each other, by construction). `queries` is a "
            "hand-written set of natural-language housing requests at 4 constraint-count "
            "tiers, each with a `constraints` dict describing the intended filter and a "
            "programmatically-computed `ground_truth_bench_ids` (which houses, by `bench_id`, "
            "actually satisfy those constraints in this fixed house list). Some tier-4 queries "
            "are deliberately tight/near-infeasible to exercise the relax-and-retry loop."
        ),
        "houses": houses,
        "queries": queries,
    }

    out_path = Path(__file__).parent / "test_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"wrote {out_path}")
    print(f"houses: {len(houses)}")
    print(f"queries: {len(queries)}")
    for t in (1, 2, 3, 4):
        tq = [q for q in queries if q["tier"] == t]
        gtc = [q["ground_truth_count"] for q in tq]
        print(f"tier {t}: {len(tq)} queries, ground_truth_count range {min(gtc)}-{max(gtc)}, "
              f"num with 0 matches: {sum(1 for c in gtc if c == 0)}")


if __name__ == "__main__":
    main()
