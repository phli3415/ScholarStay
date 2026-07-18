"""
One-off fix for the real-data RAG benchmark: app/dataProcessing/import_csv_to_db.py
never generates embedding_vector for the houses it imports (unlike
house_service.create_house, which does). Every CSV-imported house therefore
has embedding_vector = NULL, which silently makes it invisible to
find_similar_listings (embedding_vector <=> ... compared against NULL is
NULL, so the distance__lt=1 filter drops the row) -- this was the root cause
of run_real_data_benchmark.py showing a flat 0% hit rate across every
tier/category.

This just calls the existing (previously unused-anywhere)
HouseService.fill_missing_embeddings(), which finds every house with a null
embedding_vector and regenerates it via the normal
generate_listing_document + create_embedding path. Not CSV-specific by
design -- it will also pick up any other house missing an embedding for
whatever reason.

Usage (from BackendApplication/):
    python benchmark/backfill_real_house_embeddings.py
"""
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


async def main() -> None:
    from tortoise import Tortoise
    from app.database import TORTOISE_ORM
    from app.service.house_service import HouseService

    await Tortoise.init(config=TORTOISE_ORM)

    service = HouseService()
    summary = await service.fill_missing_embeddings()

    await Tortoise.close_connections()

    print(f"\nBackfill summary: {summary}")


if __name__ == "__main__":
    asyncio.run(main())
