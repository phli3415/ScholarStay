import re
import math
from typing import Optional

from .constants import (UMASS_COORDS, _EMPTY_STRINGS,
                        KITCHEN_KEYWORDS, WASHER_KEYWORDS, PARKING_KEYWORDS,
                        _STATE_ABBREVS, _STATE_NAMES_TO_ABBREV)


def _clean(v) -> Optional[str]:
    """Normalise a raw CSV cell to str or None."""
    if v is None:
        return None
    s = str(v).strip()
    return None if s.lower() in _EMPTY_STRINGS else s


def _haversine(lat: float, lon: float) -> float:
    """Return distance in km between (lat, lon) and UMass Amherst."""
    R = 6371.0
    lat1, lon1 = math.radians(UMASS_COORDS[0]), math.radians(UMASS_COORDS[1])
    lat2, lon2 = math.radians(lat), math.radians(lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# Matches pure house numbers: "123", "123A", "123-125" (NOT ordinals like "13th")
_HOUSE_NUMBER_RE = re.compile(r'^\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?\b', re.IGNORECASE)

# Ordinals that look like house numbers but are street names: 13th, 2nd, 3rd, 1st
_ORDINAL_RE = re.compile(r'^\d+(st|nd|rd|th)\b', re.IGNORECASE)

# Keyword-prefixed unit labels: "Unit 4B", "Apt 2", "#7"
_KEYWORD_NUM_RE = re.compile(r'^(?:unit|apt|apartment|suite|ste|#)\s*[\w-]+', re.IGNORECASE)

# Trailing unit designator to strip from street end
_TRAILING_UNIT_RE = re.compile(
    r',?\s+(?:apartment|apt|unit|suite|ste|#)\s*[\w-]+\s*$', re.IGNORECASE
)

# Secondary address embedded in street: "717-723 Sutter St" inside "Georgia St 717-723 Sutter St"
_SECONDARY_ADDRESS_RE = re.compile(
    r'\s+\d+[\w-]*\s+\w+\s+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|'
    r'Dr|Drive|Ln|Lane|Ct|Court|Pl|Place|Way|Ter|Terrace|Pkwy|Parkway|'
    r'Hwy|Highway|Loop|Cir|Circle|Trl|Trail|Run)\b',
    re.IGNORECASE
)

# Build a sorted list of full state names (longest first to avoid partial matches)
_STATE_NAMES_SORTED = sorted(_STATE_NAMES_TO_ABBREV.keys(), key=len, reverse=True)

_ZIP_RE = re.compile(r'\b\d{5}(?:-\d{4})?\b')


def _dedupe_address_parts(s: str) -> str:
    """
    Split on commas, remove duplicate segments, then rejoin.
    Preserves first occurrence of each unique segment.

    ZIP-segment dropping is disabled: the CSV `address` column never
    contains a ZIP, and the LLM extraction prompt now tells the model to
    omit ZIP too (see llm_extractor.py). Re-enable the `_ZIP_RE.fullmatch`
    check below if that assumption stops holding.
    """
    parts = [p.strip() for p in s.split(',')]
    seen: set[str] = set()
    result = []
    for part in parts:
        if not part:
            continue
        # if _ZIP_RE.fullmatch(part):   # drop pure ZIP segments (disabled)
        #     continue
        key = part.lower()
        if key in seen:               # drop duplicates
            continue
        seen.add(key)
        result.append(part)
    return ' '.join(result)


def _strip_state_suffix(s: str, known_state: Optional[str]) -> tuple[str, Optional[str]]:
    """
    Remove a trailing state indicator from s.
    Returns (stripped_string, detected_abbreviation).
    Priority: "Washington DC" compound → known_state → 2-letter abbrev → full name.
    """
    # Special compound: "Washington DC" or "Washington, DC"
    m = re.search(r',?\s+Washington,?\s+DC\s*$', s, re.IGNORECASE)
    if m:
        return s[:m.start()].strip(), "DC"

    # Known state passed by caller
    if known_state:
        m = re.search(rf',?\s+{re.escape(known_state)}\s*$', s, re.IGNORECASE)
        if m:
            abbrev = _STATE_NAMES_TO_ABBREV.get(known_state.title(), known_state.upper())
            return s[:m.start()].strip(), abbrev

    # 2-letter abbreviation at end
    m = re.search(r',?\s+([A-Z]{2})\s*$', s)
    if m and m.group(1) in _STATE_ABBREVS:
        return s[:m.start()].strip(), m.group(1)

    # Full state name at end (longest match first)
    for name in _STATE_NAMES_SORTED:
        m = re.search(rf',?\s+{re.escape(name)}\s*$', s, re.IGNORECASE)
        if m:
            return s[:m.start()].strip(), _STATE_NAMES_TO_ABBREV[name]

    return s, None


def _parse_address(
    raw: str, known_state: Optional[str] = None
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Split a raw address into (house_number, street, detected_state).
    detected_state is the 2-letter abbreviation found at the end of the address,
    or None if not found.
    """
    if not raw:
        return None, None, None

    s = raw.strip()

    # Step 1: deduplicate comma segments, then strip state.
    # ZIP stripping is disabled here: the CSV `address` column never has a
    # ZIP, and the LLM extraction prompt now excludes ZIP too (see
    # llm_extractor.py). Re-enable `_ZIP_RE.sub` below if that stops holding.
    # s = _ZIP_RE.sub('', s)                # strip ZIPs before dedupe
    s = _dedupe_address_parts(s)          # dedupe + join with space (no commas)
    s = re.sub(r'\s+', ' ', s).strip()  # collapse extra whitespace
    if not s:
        return None, None, None
    s, detected_state = _strip_state_suffix(s, known_state)
    if not s:
        return None, None, detected_state

    # Step 2: handle building-name prefix (e.g. "Somerset West 18205 NW Bronson Rd")
    # Require number to be followed by a letter so ZIP codes at end are not matched
    if not re.match(r'^[\d#]', s) and not _KEYWORD_NUM_RE.match(s):
        mid = re.search(r'\b(\d+)\s+[A-Za-z]', s)
        if mid:
            s = s[mid.start():]

    # Step 3: extract house number from start
    house_number: Optional[str] = None
    street: Optional[str] = None

    kw_m = _KEYWORD_NUM_RE.match(s)
    if kw_m:
        # "Unit 4B ..." style — but these are unit numbers, not street house numbers;
        # treat the whole string as street (no house number)
        street = s
        house_number = None
    else:
        num_m = _HOUSE_NUMBER_RE.match(s)
        if num_m:
            candidate = num_m.group(0)
            if _ORDINAL_RE.match(candidate):
                # "13th", "2nd" etc. — ordinal = part of street name
                house_number = None
                street = s
            else:
                house_number = candidate
                street = s[num_m.end():].strip().lstrip(",").strip()
        else:
            street = s

    # Step 4: strip trailing unit designator from street ("Apartment 1f", "#2206n")
    if street:
        street = _TRAILING_UNIT_RE.sub("", street).strip()

    # Step 5: truncate at embedded secondary address ("Georgia St 717-723 Sutter St")
    if street and house_number:
        m = _SECONDARY_ADDRESS_RE.search(street)
        if m:
            street = street[:m.start()].strip()

    if house_number:
        house_number = house_number.strip(",").strip()
    if street:
        street = street.strip(",").strip()

    return house_number or None, street or None, detected_state


def _parse_amenities(raw: Optional[str]) -> tuple[bool, bool, bool]:
    """Return (has_kitchen, has_washer, has_parking) by keyword matching."""
    if not raw:
        return False, False, False
    text = raw.lower()
    return (
        any(kw in text for kw in KITCHEN_KEYWORDS),
        any(kw in text for kw in WASHER_KEYWORDS),
        any(kw in text for kw in PARKING_KEYWORDS),
    )
