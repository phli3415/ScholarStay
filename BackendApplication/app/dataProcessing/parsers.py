import re
import math
from typing import Optional

from .constants import UMASS_COORDS, _EMPTY_STRINGS, KITCHEN_KEYWORDS, WASHER_KEYWORDS, PARKING_KEYWORDS


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


# Matches: "123", "123A", "123-125", "Unit 4B", "Apt 2", "#7"
_HOUSE_NUMBER_RE = re.compile(
    r"""^
    (?:
        (?:unit|apt|apartment|suite|ste|\#)\s*[\w-]+  # Unit 4B / Apt 2 / \#7
        |
        \d+[\w-]*                                     # 123 / 123A / 123-125
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _parse_address(raw: str) -> tuple[Optional[str], Optional[str]]:
    """
    Split a raw address string into (house_number, street).
    Returns (None, None) if raw is empty/null.
    """
    if not raw:
        return None, None
    raw = raw.strip()
    m = _HOUSE_NUMBER_RE.match(raw)
    if m:
        house_number = m.group(0).strip()
        street = raw[m.end():].strip().lstrip(",").strip()
        return house_number or None, street or None
    return None, raw or None


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
