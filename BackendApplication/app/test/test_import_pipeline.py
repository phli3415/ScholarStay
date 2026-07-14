"""
Unit tests for the CSV import pipeline.
Run from BackendApplication/:
    pytest app/test/test_import_pipeline.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from app.dataProcessing.parsers import _clean, _parse_address, _parse_amenities
from app.dataProcessing.llm_extractor import LLMExtractedFields
from app.dataProcessing.import_csv_to_db import process_row


# ── _clean ────────────────────────────────────────────────────────────────────

class TestClean:
    def test_none_returns_none(self):
        assert _clean(None) is None

    def test_empty_string(self):
        assert _clean("") is None

    def test_nan_variants(self):
        for val in ["nan", "NaN", "NAN", "null", "NULL", "none", "None",
                    "n/a", "N/A", "n/a.", "--", "-", "not available", "na"]:
            assert _clean(val) is None, f"expected None for {val!r}"

    def test_whitespace_stripped(self):
        assert _clean("  hello  ") == "hello"

    def test_valid_string(self):
        assert _clean("Washington") == "Washington"

    def test_numeric_string(self):
        assert _clean("12345") == "12345"


# ── _parse_address ────────────────────────────────────────────────────────────

class TestParseAddress:

    # ── basic cases ──

    def test_empty(self):
        assert _parse_address("") == (None, None, None)

    def test_none_equivalent(self):
        assert _parse_address("  ") == (None, None, None)

    def test_simple_number_street(self):
        hn, st, state = _parse_address("123 Main St")
        assert hn == "123"
        assert st == "Main St"
        assert state is None

    def test_number_with_letter_suffix(self):
        hn, st, state = _parse_address("123A Elm Street")
        assert hn == "123A"
        assert st == "Elm Street"

    # ── problem 1: ordinal street names ──

    def test_ordinal_13th_not_house_number(self):
        hn, st, state = _parse_address("13th St NW Monroe St NW Washington DC")
        assert hn is None
        assert "13th" in st
        assert state == "DC"

    def test_ordinal_2nd(self):
        hn, st, _ = _parse_address("2nd Ave Brooklyn")
        assert hn is None
        assert "2nd" in st

    def test_ordinal_1st(self):
        hn, st, _ = _parse_address("1st Street NE")
        assert hn is None

    # ── problem 2: range house numbers ──

    def test_range_house_number(self):
        hn, st, _ = _parse_address("122-126 East Genesee St")
        assert hn == "122-126"
        assert st == "East Genesee St"

    # ── problem 3: building name prefix ──

    def test_building_name_prefix(self):
        hn, st, _ = _parse_address("Somerset West 18205 NW Bronson Rd")
        assert hn == "18205"
        assert "Bronson" in st

    def test_building_name_no_number(self):
        # no number found → house_number None, full string as street
        hn, st, _ = _parse_address("The Elms Apartments")
        assert hn is None
        assert st is not None

    # ── problem 4: trailing unit designators ──

    def test_trailing_hash_unit(self):
        hn, st, _ = _parse_address("5500 Friendship Boulevard #2206n")
        assert hn == "5500"
        assert "#" not in st
        assert "2206" not in st

    def test_trailing_apartment_word(self):
        hn, st, _ = _parse_address("2106 Saint Paul St Apartment 1f")
        assert hn == "2106"
        assert "Apartment" not in st
        assert "1f" not in st

    def test_trailing_apt_abbreviation(self):
        hn, st, _ = _parse_address("800 N Michigan Ave Apt 3B")
        assert hn == "800"
        assert "Apt" not in st
        assert "3B" not in st

    # ── state detection ──

    def test_state_abbrev_stripped(self):
        _, _, state = _parse_address("100 Main St Springfield IL")
        assert state == "IL"

    def test_washington_dc_special(self):
        hn, st, state = _parse_address("1600 Pennsylvania Ave Washington DC")
        assert state == "DC"
        assert "Washington" not in st
        assert "DC" not in st

    def test_known_state_passed(self):
        _, _, state = _parse_address("100 Main St", known_state="NY")
        # no state suffix in address, known_state not stripped → None
        assert state is None

    def test_known_state_strips_if_present(self):
        _, st, state = _parse_address("100 Main St New York", known_state="New York")
        assert state == "NY"
        assert "New York" not in (st or "")

    def test_full_state_name_stripped(self):
        _, _, state = _parse_address("500 Oak Ave California")
        assert state == "CA"

    def test_multiple_addresses_keeps_first(self):
        hn, st, _ = _parse_address("545 Georgia St 717-723 Sutter St")
        assert hn == "545"
        assert st == "Georgia St"
        assert "717" not in st
        assert "Sutter" not in st


# ── _parse_amenities ──────────────────────────────────────────────────────────

class TestParseAmenities:

    def test_none_input(self):
        assert _parse_amenities(None) == (False, False, False)

    def test_empty_string(self):
        assert _parse_amenities("") == (False, False, False)

    def test_kitchen_keywords(self):
        for kw in ["kitchen", "stove", "refrigerator", "fridge", "dishwasher"]:
            k, _, _ = _parse_amenities(f"unit has a {kw}")
            assert k is True, f"expected kitchen=True for keyword {kw!r}"

    def test_washer_keywords(self):
        for kw in ["washer", "laundry", "washer/dryer", "w/d", "washing machine"]:
            _, w, _ = _parse_amenities(f"includes {kw} in unit")
            assert w is True, f"expected washer=True for keyword {kw!r}"

    def test_parking_keywords(self):
        for kw in ["parking", "garage", "carport", "driveway"]:
            _, _, p = _parse_amenities(f"comes with {kw}")
            assert p is True, f"expected parking=True for keyword {kw!r}"

    def test_all_true(self):
        raw = "Full kitchen, in-unit washer/dryer, parking included"
        assert _parse_amenities(raw) == (True, True, True)

    def test_case_insensitive(self):
        k, w, p = _parse_amenities("KITCHEN WASHER PARKING")
        assert (k, w, p) == (True, True, True)

    def test_no_matches(self):
        assert _parse_amenities("cozy studio with hardwood floors") == (False, False, False)


# ── process_row ───────────────────────────────────────────────────────────────

class TestProcessRow:

    def _base_row(self, **overrides):
        row = {
            "price_type": "Monthly",
            "price": "1200",
            "body": "Nice apartment near campus.",
            "cityname": "Amherst",
            "state": "MA",
            "amenities": "kitchen, parking",
            "address": "123 Main St",
            "latitude": "42.3906",
            "longitude": "-72.5261",
        }
        row.update(overrides)
        return row

    @pytest.mark.asyncio
    async def test_non_monthly_skipped(self):
        row = self._base_row(price_type="Weekly")
        assert await process_row(row) is None

    @pytest.mark.asyncio
    async def test_invalid_price_skipped(self):
        row = self._base_row(price="None")
        assert await process_row(row) is None

    @pytest.mark.asyncio
    async def test_zero_price_skipped(self):
        row = self._base_row(price="0")
        assert await process_row(row) is None

    @pytest.mark.asyncio
    async def test_happy_path_no_llm(self):
        row = self._base_row()
        result = await process_row(row)
        assert result is not None
        kwargs, llm_filled = result
        assert kwargs["monthly_rent"] == Decimal("1200")
        assert kwargs["city"] == "Amherst"
        assert kwargs["province"] == "MA"
        assert kwargs["house_number"] == "123"
        assert kwargs["street"] == "Main St"
        assert kwargs["has_kitchen"] is True
        assert kwargs["has_parking"] is True
        assert llm_filled == []

    @pytest.mark.asyncio
    async def test_quality_gate_skips_too_many_nulls(self):
        # city=None, province=None, street=None (null address), distance=None (no lat/lon)
        row = self._base_row(
            cityname="null", state="null",
            address="null", latitude="null", longitude="null",
        )
        assert await process_row(row) is None

    @pytest.mark.asyncio
    async def test_llm_called_for_missing_address(self):
        row = self._base_row(address="null")
        mock_result = LLMExtractedFields(
            has_kitchen=True, has_washer=False, has_parking=True,
            raw_address="456 Elm St",
            city=None, province=None,
        )
        with patch("app.dataProcessing.import_csv_to_db.llm_extract",
                   new=AsyncMock(return_value=mock_result)):
            result = await process_row(row)
        assert result is not None
        kwargs, llm_filled = result
        assert kwargs["street"] == "Elm St"
        assert kwargs["house_number"] == "456"
        assert "street" in llm_filled

    @pytest.mark.asyncio
    async def test_llm_called_for_missing_amenities(self):
        row = self._base_row(amenities="null")
        mock_result = LLMExtractedFields(
            has_kitchen=True, has_washer=True, has_parking=False,
            raw_address=None, city=None, province=None,
        )
        with patch("app.dataProcessing.import_csv_to_db.llm_extract",
                   new=AsyncMock(return_value=mock_result)):
            result = await process_row(row)
        assert result is not None
        kwargs, llm_filled = result
        assert kwargs["has_kitchen"] is True
        assert kwargs["has_washer"] is True
        assert "has_kitchen" in llm_filled
        assert "has_washer" in llm_filled

    @pytest.mark.asyncio
    async def test_no_llm_when_body_is_null(self):
        # amenities all false + address null, but body is null → no LLM call
        row = self._base_row(amenities="null", address="null", body="null")
        with patch("app.dataProcessing.import_csv_to_db.llm_extract",
                   new=AsyncMock()) as mock_llm:
            await process_row(row)
        mock_llm.assert_not_called()
