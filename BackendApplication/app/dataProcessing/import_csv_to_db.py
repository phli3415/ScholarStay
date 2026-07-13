"""
CSV → Houses DB import pipeline.
Usage (from BackendApplication/):
    python -m app.dataProcessing.import_csv_to_db <path_to_csv>
"""

import sys
import asyncio
from decimal import Decimal, InvalidOperation
from typing import Optional

from .constants import CSV_IMPORT_BOT_UID, MIN_NULL_THRESHOLD, SOURCE_ID_BASE
from .parsers import _clean, _haversine, _parse_address, _parse_amenities
from .llm_extractor import llm_extract, LLMExtractedFields


# ── ROW PROCESSOR ────────────────────────────────────────────────────────────

async def process_row(row: dict) -> Optional[tuple[dict, list[str]]]:
    """
    Parse one CSV row into (Houses kwargs, llm_filled_fields).
    Returns None if the row should be skipped.
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
    house_number, street = _parse_address(address_raw) if address_raw else (None, None)

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
        need_fields += ["street", "house_number"]
    if city is None:
        need_fields.append("city")
    if province is None:
        need_fields.append("province")

    # 6. LLM fallback (only when body is available)
    llm_filled: list[str] = []
    if need_fields and body:
        extracted: LLMExtractedFields = await llm_extract(body, need_fields)

        if "has_kitchen" in need_fields:
            has_kitchen = extracted.has_kitchen
            has_washer  = extracted.has_washer
            has_parking = extracted.has_parking
            for field, val in [("has_kitchen", has_kitchen), ("has_washer", has_washer), ("has_parking", has_parking)]:
                if val:
                    llm_filled.append(field)

        if "street" in need_fields:
            house_number = extracted.house_number
            street       = extracted.street
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

async def main(csv_path: str) -> None:
    import csv
    from tortoise import Tortoise
    from app.database import TORTOISE_ORM
    from app.model.user import User
    from app.model.houses import Houses

    await Tortoise.init(config=TORTOISE_ORM)

    # Ensure import bot user exists
    owner, _ = await User.get_or_create(
        firebase_uid=CSV_IMPORT_BOT_UID,
        defaults={"username": "csv-import-bot", "gmail": "bot@scholarstay.internal"},
    )

    total = imported = skipped_price = skipped_quality = llm_rows = 0

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row_index, row in enumerate(reader, start=1):
            total += 1
            result = await process_row(row)
            if result is None:
                if _clean(row.get("price_type")) != "Monthly":
                    skipped_price += 1
                else:
                    skipped_quality += 1
                continue

            kwargs, llm_filled = result
            house_id = SOURCE_ID_BASE + row_index
            _, created = await Houses.get_or_create(
                id=house_id,
                defaults=dict(
                    owner=owner,
                    llm_filled_fields=llm_filled if llm_filled else None,
                    **kwargs,
                ),
            )
            if created:
                imported += 1
                if llm_filled:
                    llm_rows += 1
            else:
                skipped_quality += 1  # duplicate run

    await Tortoise.close_connections()

    print(f"\n── Import summary ──────────────────────────────")
    print(f"  Total rows read   : {total}")
    print(f"  Imported          : {imported}")
    print(f"  Skipped (non-monthly / bad price): {skipped_price}")
    print(f"  Skipped (quality gate): {skipped_quality}")
    print(f"  Rows with LLM fill: {llm_rows}")
    print(f"────────────────────────────────────────────────")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.dataProcessing.import_csv_to_db <path_to_csv>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
