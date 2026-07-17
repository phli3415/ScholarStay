"""
CSV → Houses DB import pipeline.
Usage (from BackendApplication/):
    python -m app.dataProcessing.import_csv_to_db <path_to_csv> [--no-llm-fallback] [--start-row N]
"""

import asyncio
import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("import_csv.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from .constants import CSV_IMPORT_BOT_UID, MIN_NULL_THRESHOLD, SOURCE_ID_BASE
from .parsers import _clean, _haversine, _parse_address, _parse_amenities
from .llm_extractor import llm_extract, LLMExtractedFields

# Retries for a DB write that fails because the connection died underneath us
# (e.g. a serverless Postgres compute suspending, or a transient local
# network/DNS blip). Each retry closes and re-inits the Tortoise connection
# pool before trying again, waiting longer between each attempt (2s, 4s,
# 8s, 16s, 32s) so a longer outage has a chance to clear.
MAX_DB_RETRIES = 6
DB_RECONNECT_BASE_DELAY_SECONDS = 2


# ── ROW PROCESSOR ────────────────────────────────────────────────────────────

async def process_row(row: dict, use_llm_fallback: bool = True) -> Optional[tuple[dict, list[str]]]:
    """
    Parse one CSV row into (Houses kwargs, llm_filled_fields).
    Returns None if the row should be skipped.
    If use_llm_fallback is False, fields the LLM would have filled are left
    at their defaults (None/False) instead.
    """
    # 1. Only keep monthly listings with a valid price
    if _clean(row.get("price_type")) != "Monthly":
        return None
    try:
        price = Decimal(str(row.get("price", "")).strip())
        if price <= 0:
            return None
    except InvalidOperation:
        return None

    # 2. Direct mappings
    body     = _clean(row.get("body"))
    city     = _clean(row.get("cityname"))
    province = _clean(row.get("state"))
    amenities_raw = _clean(row.get("amenities"))
    address_raw   = _clean(row.get("address"))

    # 3. Parse amenities and address from raw CSV
    has_kitchen, has_washer, has_parking = _parse_amenities(amenities_raw)
    house_number, street, detected_state = (
        _parse_address(address_raw, province) if address_raw else (None, None, None)
    )
    # Fill province from address if CSV column was null
    if province is None and detected_state:
        province = detected_state

    # 4. Distance via haversine
    try:
        lat = float(row.get("latitude", ""))
        lon = float(row.get("longitude", ""))
        distance = round(_haversine(lat, lon), 2)
    except (ValueError, TypeError):
        distance = None

    # 5. Decide what LLM needs to fill
    need_fields: list[str] = []
    if not has_kitchen and not has_washer and not has_parking:
        need_fields += ["has_kitchen", "has_washer", "has_parking"]
    if address_raw is None:
        need_fields.append("raw_address")
    if city is None:
        need_fields.append("city")
    if province is None:
        need_fields.append("province")

    # 6. LLM fallback (only when body is available)
    llm_filled: list[str] = []
    if use_llm_fallback and need_fields and body:
        extracted: LLMExtractedFields = await llm_extract(body, need_fields)

        if "has_kitchen" in need_fields:
            has_kitchen = extracted.has_kitchen
            has_washer  = extracted.has_washer
            has_parking = extracted.has_parking
            for field, val in [("has_kitchen", has_kitchen), ("has_washer", has_washer), ("has_parking", has_parking)]:
                if val:
                    llm_filled.append(field)

        if "raw_address" in need_fields and extracted.raw_address:
            house_number, street, addr_state = _parse_address(extracted.raw_address, province)
            if province is None and addr_state:
                province = addr_state
            if house_number: llm_filled.append("house_number")
            if street:       llm_filled.append("street")

        if "city" in need_fields and extracted.city:
            city = extracted.city
            llm_filled.append("city")

        if "province" in need_fields and extracted.province:
            province = extracted.province
            llm_filled.append("province")

    # 7. Quality gate: skip rows with too many null key fields
    null_count = sum(v is None for v in [city, province, street, distance])
    if null_count >= MIN_NULL_THRESHOLD:
        return None

    kwargs = dict(
        monthly_rent          = price,
        description           = body,
        city                  = city,
        province              = province,
        street                = street,
        house_number          = house_number,
        has_kitchen           = has_kitchen,
        has_washer            = has_washer,
        has_parking           = has_parking,
        distance_to_university= Decimal(str(distance)) if distance is not None else None,
    )
    return kwargs, llm_filled


# ── MAIN ─────────────────────────────────────────────────────────────────────

async def main(csv_path: str, use_llm_fallback: bool = True, start_row: int = 1) -> None:
    import csv
    import asyncpg
    from tortoise import Tortoise
    from app.database import TORTOISE_ORM
    from app.model.user import User
    from app.model.houses import Houses

    connection_errors = (
        asyncpg.exceptions.ConnectionDoesNotExistError,
        asyncpg.exceptions.InterfaceError,
        ConnectionError,
        OSError,
    )

    async def reconnect(delay: float) -> None:
        logger.warning("DB connection lost, reconnecting in %.0fs...", delay)
        await Tortoise.close_connections()
        await asyncio.sleep(delay)
        await Tortoise.init(config=TORTOISE_ORM)

    await Tortoise.init(config=TORTOISE_ORM)

    # Ensure import bot user exists
    owner, _ = await User.get_or_create(
        firebase_uid=CSV_IMPORT_BOT_UID,
        defaults={"username": "csv-import-bot", "gmail": "bot@scholarstay.internal"},
    )

    total = imported = skipped_price = skipped_quality = skipped_before_start = skipped_error = llm_rows = 0

    # errors="replace": a handful of rows in these datasets have stray
    # Windows-1252 bytes (e.g. curly quotes) leaked into an otherwise-UTF-8
    # file; swap the bad byte for U+FFFD instead of crashing the whole import.
    with open(csv_path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row_index, row in enumerate(reader, start=1):
            total += 1
            if row_index < start_row:
                skipped_before_start += 1
                continue
            try:
                result = await process_row(row, use_llm_fallback=use_llm_fallback)
                if result is None:
                    if _clean(row.get("price_type")) != "Monthly":
                        skipped_price += 1
                    else:
                        skipped_quality += 1
                    continue

                kwargs, llm_filled = result
                house_id = SOURCE_ID_BASE + row_index

                for attempt in range(1, MAX_DB_RETRIES + 1):
                    try:
                        _, created = await Houses.get_or_create(
                            id=house_id,
                            defaults=dict(
                                owner=owner,
                                llm_filled_fields=llm_filled if llm_filled else None,
                                **kwargs,
                            ),
                        )
                        break
                    except connection_errors:
                        if attempt == MAX_DB_RETRIES:
                            raise
                        await reconnect(DB_RECONNECT_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))

                if created:
                    imported += 1
                    if llm_filled:
                        llm_rows += 1
                else:
                    skipped_quality += 1  # duplicate run
            except Exception:
                logger.exception("Row %d failed, skipping", row_index)
                skipped_error += 1
                continue

    await Tortoise.close_connections()

    print(f"\n── Import summary ──────────────────────────────")
    print(f"  Total rows read   : {total}")
    print(f"  Imported          : {imported}")
    print(f"  Skipped (before --start-row): {skipped_before_start}")
    print(f"  Skipped (non-monthly / bad price): {skipped_price}")
    print(f"  Skipped (quality gate): {skipped_quality}")
    print(f"  Skipped (unexpected error): {skipped_error}")
    print(f"  Rows with LLM fill: {llm_rows}")
    print(f"────────────────────────────────────────────────")


if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser(
        description="CSV → Houses DB import pipeline."
    )
    arg_parser.add_argument("csv_path", help="path to the CSV file to import")
    arg_parser.add_argument(
        "--no-llm-fallback",
        action="store_true",
        help="skip the LLM fallback call; fields it would have filled are left empty",
    )
    arg_parser.add_argument(
        "--start-row",
        type=int,
        default=1,
        help="1-indexed CSV row to start processing from; earlier rows are "
             "skipped entirely (no parsing, no LLM calls). Useful for "
             "resuming a large import after a crash.",
    )
    args = arg_parser.parse_args()
    asyncio.run(main(
        args.csv_path,
        use_llm_fallback=not args.no_llm_fallback,
        start_row=args.start_row,
    ))
