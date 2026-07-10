"""
Runs the 36 queries in benchmark/test_data.json against the compiled agentic
workflow graph and scores retrieval quality against the programmatic ground
truth, stratified by constraint-count tier.

Metric: hit@k against `sql_house_ids` -> `top_matched_ids` (the actual RAG
output, capped at Config.EMBEDDING_HOUSES_RETURN), not exact-set equality —
see benchmark/test_data.json's description for why. Also records
`rewrite_counter` per query, since a query that only succeeds after the
relax-and-retry loop kicked in is a different outcome than an exact-match
success, not a failure.

Usage: run from the BackendApplication directory so relative config paths
(prompts/, output/) resolve correctly:
    python benchmark/run_benchmark.py
"""
import asyncio
import json
import sys
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
TEST_DATA_PATH = BENCH_DIR / "test_data.json"
MAPPING_PATH = BENCH_DIR / "bench_id_to_db_id.json"
RESULTS_PATH = BENCH_DIR / "results.json"

CONCURRENCY = 5


async def run_one_query(graph, sem, query, ground_truth_db_ids):
    async with sem:
        config = {"configurable": {"thread_id": f"bench-{query['id']}", "user_id": "benchmark-runner"}}
        try:
            result = await graph.ainvoke(
                {"user_input": query["text"], "messages": [HumanMessage(content=query["text"])]},
                config=config,
            )
        except Exception as e:
            return {
                "id": query["id"], "tier": query["tier"], "text": query["text"],
                "error": str(e),
            }

    top_matched_ids = result.get("top_matched_ids") or []
    sql_house_ids = result.get("sql_house_ids") or []
    rewrite_counter = result.get("rewrite_counter", 0)
    intent_type = result.get("intent_type")
    original_requirement = result.get("original_requirement")
    if hasattr(original_requirement, "model_dump"):
        original_requirement = original_requirement.model_dump(exclude_none=True)

    hit_rank = None
    for i, hid in enumerate(top_matched_ids, start=1):
        if hid in ground_truth_db_ids:
            hit_rank = i
            break

    sql_hits = len(set(sql_house_ids) & set(ground_truth_db_ids))
    sql_recall = (sql_hits / len(ground_truth_db_ids)) if ground_truth_db_ids else None

    return {
        "id": query["id"],
        "tier": query["tier"],
        "text": query["text"],
        "intended_constraints": query["constraints"],
        "extracted_requirement": original_requirement,
        "ground_truth_count": len(ground_truth_db_ids),
        "sql_house_ids": sql_house_ids,
        "sql_recall": sql_recall,
        "top_matched_ids": top_matched_ids,
        "hit_at_k": hit_rank is not None,
        "hit_rank": hit_rank,
        "rewrite_counter": rewrite_counter,
        "intent_type": intent_type,
    }


async def main():
    await Tortoise.init(config=TORTOISE_ORM)

    with open(TEST_DATA_PATH, encoding="utf-8") as f:
        test_data = json.load(f)
    with open(MAPPING_PATH, encoding="utf-8") as f:
        bench_to_db = {int(k): v for k, v in json.load(f).items()}

    queries = test_data["queries"]

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
    print(f"Graph ready. Running {len(queries)} benchmark queries (concurrency={CONCURRENCY})...\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = []
    for q in queries:
        ground_truth_db_ids = [bench_to_db[bid] for bid in q["ground_truth_bench_ids"]]
        tasks.append(run_one_query(graph, sem, q, ground_truth_db_ids))

    results = await asyncio.gather(*tasks)

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Wrote per-query results to {RESULTS_PATH}\n")

    # ---- summary by tier ----
    print(f"{'tier':<6}{'n':<5}{'hit@k':<10}{'avg_rank':<12}{'avg_relax':<12}{'errors'}")
    for tier in (1, 2, 3, 4):
        tier_results = [r for r in results if r["tier"] == tier]
        errored = [r for r in tier_results if "error" in r]
        ok = [r for r in tier_results if "error" not in r]
        hits = [r for r in ok if r["hit_at_k"]]
        hit_rate = len(hits) / len(ok) if ok else 0.0
        avg_rank = sum(r["hit_rank"] for r in hits) / len(hits) if hits else float("nan")
        avg_relax = sum(r["rewrite_counter"] for r in ok) / len(ok) if ok else float("nan")
        print(f"{tier:<6}{len(tier_results):<5}{hit_rate:<10.0%}{avg_rank:<12.2f}{avg_relax:<12.2f}{len(errored)}")

    await pool.close()
    await Tortoise.close_connections()


asyncio.run(main())
