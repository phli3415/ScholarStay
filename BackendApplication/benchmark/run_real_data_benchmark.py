"""
Runs the queries from generate_queries_from_houses.py against the compiled
agentic workflow graph, on real (CSV-imported) houses instead of the
synthetic Amherst set used by run_benchmark.py.

Ground truth for a query is just its own source house (the one it was
generated from) -- there is no independently-computed full matching set the
way test_data.json has one, because doing that here would require re-judging
every candidate house's free-text description against soft/semantic
constraints at scale (the exact thing this benchmark is trying to measure,
so it can't also be the answer key). This makes "hit" here a stricter,
noisier signal than run_benchmark.py's hit@k: a real miss may just mean the
graph found an equally valid alternative house, not that it's wrong. That's
why every miss is written to a human-review file instead of being counted as
a hard failure -- see benchmark/apply_review_verdicts.py.

Usage (from BackendApplication directory):
    python benchmark/run_real_data_benchmark.py --queries benchmark/RealDataRAG/generated_queries_n350_<ts>.json
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

from tortoise import Tortoise
from langchain_core.messages import HumanMessage
from psycopg_pool import AsyncConnectionPool

from app.database import TORTOISE_ORM
from app.utils.config import Config
from app.utils.llms import initialize_llm, initialize_embedding
from app.utils.tools_config import get_tools
from app.llm.agenticWorkflow import ToolConfig, create_graph

BENCH_DIR = Path(__file__).resolve().parent
OUT_DIR = BENCH_DIR / "RealDataRAG"

CONCURRENCY = 5

HOUSE_FIELDS = [
    "id", "province", "city", "street", "house_number", "monthly_rent",
    "has_kitchen", "has_washer", "has_parking", "distance_to_university",
    "description",
]


def house_to_dict(house) -> dict:
    row = {}
    for f in HOUSE_FIELDS:
        v = getattr(house, f)
        if f in ("monthly_rent", "distance_to_university") and v is not None:
            v = float(v)
        row[f] = v
    return row


async def run_one_query(graph, sem: asyncio.Semaphore, q: dict) -> dict:
    async with sem:
        config = {"configurable": {"thread_id": f"realbench-{q['source_house_id']}", "user_id": "real-benchmark-runner"}}
        try:
            result = await graph.ainvoke(
                {"user_input": q["query"], "messages": [HumanMessage(content=q["query"])]},
                config=config,
            )
        except Exception as e:
            return {**q, "error": str(e)}

    top_matched_ids = result.get("top_matched_ids") or []
    sql_house_ids = result.get("sql_house_ids") or []
    rewrite_counter = result.get("rewrite_counter", 0)
    intent_type = result.get("intent_type")
    original_requirement = result.get("original_requirement")
    if hasattr(original_requirement, "model_dump"):
        original_requirement = original_requirement.model_dump(exclude_none=True)

    hit_rank = None
    for i, hid in enumerate(top_matched_ids, start=1):
        if hid == q["source_house_id"]:
            hit_rank = i
            break

    return {
        **q,
        "extracted_requirement": original_requirement,
        "sql_house_ids": sql_house_ids,
        "top_matched_ids": top_matched_ids,
        "hit_at_k": hit_rank is not None,
        "hit_rank": hit_rank,
        "rewrite_counter": rewrite_counter,
        "intent_type": intent_type,
        "error": None,
    }


def summarize(results: list[dict]) -> dict:
    def hit_rate(rows):
        ok = [r for r in rows if r.get("error") is None]
        if not ok:
            return None
        return sum(1 for r in ok if r["hit_at_k"]) / len(ok)

    by_count = {}
    for c in range(1, 6):
        rows = [r for r in results if r.get("constraint_count") == c]
        if rows:
            by_count[c] = {"n": len(rows), "hit_rate": hit_rate(rows)}

    semantic_rows = [r for r in results if r.get("has_semantic")]
    structured_rows = [r for r in results if not r.get("has_semantic")]

    errored = [r for r in results if r.get("error") is not None]

    return {
        "total": len(results),
        "errors": len(errored),
        "overall_hit_rate": hit_rate(results),
        "by_constraint_count": by_count,
        "semantic_queries": {"n": len(semantic_rows), "hit_rate": hit_rate(semantic_rows)},
        "structured_only_queries": {"n": len(structured_rows), "hit_rate": hit_rate(structured_rows)},
    }


async def build_review_file(misses: list[dict], out_path: Path) -> None:
    from app.model.houses import Houses

    need_ids = set()
    for m in misses:
        need_ids.add(m["source_house_id"])
        need_ids.update(m["top_matched_ids"])

    houses = await Houses.filter(id__in=list(need_ids)).all()
    houses_by_id = {h.id: house_to_dict(h) for h in houses}

    review_records = []
    for m in misses:
        review_records.append({
            "source_house_id": m["source_house_id"],
            "generated_query": m["query"],
            "used_structured_slots": m["used_structured_slots"],
            "semantic_qualities_used": m["semantic_qualities_used"],
            "constraint_count": m["constraint_count"],
            "extracted_requirement": m.get("extracted_requirement"),
            "source_house": houses_by_id.get(m["source_house_id"]),
            "top_matched": [houses_by_id.get(hid) for hid in m["top_matched_ids"]],
            "human_verdict": {"is_false_negative": None, "notes": ""},
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"review_records": review_records}, f, indent=2, ensure_ascii=False)


async def main(args) -> None:
    await Tortoise.init(config=TORTOISE_ORM)

    with open(args.queries, encoding="utf-8") as f:
        query_data = json.load(f)
    queries = query_data["queries"]
    if args.limit:
        queries = queries[:args.limit]

    llm_chat = initialize_llm(Config.LLM_TYPE)
    llm_embedding = initialize_embedding(Config.LLM_TYPE)
    tools = get_tools(llm_embedding)
    tool_config = ToolConfig(tools)

    db_url = TORTOISE_ORM["connections"]["default"]
    psycopg_conninfo = db_url.split("?")[0]
    connection_kwargs = {"autocommit": True, "prepare_threshold": 0, "connect_timeout": 5, "sslmode": "require"}
    pool = AsyncConnectionPool(
        conninfo=psycopg_conninfo, max_size=CONCURRENCY + 5, min_size=2,
        kwargs=connection_kwargs, timeout=120, max_idle=120,
        check=AsyncConnectionPool.check_connection, open=False,
    )
    await pool.open()

    graph = await create_graph(pool, llm_chat, llm_embedding, tool_config)
    print(f"Graph ready. Running {len(queries)} real-data benchmark queries (concurrency={CONCURRENCY})...\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [run_one_query(graph, sem, q) for q in queries]
    results = await asyncio.gather(*tasks)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    results_path = OUT_DIR / f"results_n{len(results)}_{ts}.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    summary = summarize(results)
    summary_path = OUT_DIR / f"summary_n{len(results)}_{ts}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    misses = [r for r in results if r.get("error") is None and not r["hit_at_k"]]
    review_path = OUT_DIR / f"review_misses_n{len(misses)}_{ts}.json"
    if misses:
        await build_review_file(misses, review_path)

    await pool.close()
    await Tortoise.close_connections()

    print(f"\nOverall hit rate: {summary['overall_hit_rate']:.1%} (n={summary['total']}, errors={summary['errors']})")
    print(f"By constraint count: {summary['by_constraint_count']}")
    print(f"Semantic queries: n={summary['semantic_queries']['n']}, hit_rate={summary['semantic_queries']['hit_rate']}")
    print(f"Structured-only queries: n={summary['structured_only_queries']['n']}, hit_rate={summary['structured_only_queries']['hit_rate']}")
    print(f"\nWrote {results_path}")
    print(f"Wrote {summary_path}")
    if misses:
        print(f"Wrote {review_path} ({len(misses)} cases needing human review)")
    else:
        print("No misses -- no review file needed.")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--queries", required=True, help="path to a generated_queries_*.json file from generate_queries_from_houses.py")
    p.add_argument("--limit", type=int, default=None, help="only run the first N queries (for fast iteration while debugging)")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
