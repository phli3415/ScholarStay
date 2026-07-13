UMASS_COORDS = (42.413939, -72.528618)   # UMass Amherst lat/lon

CSV_IMPORT_BOT_UID = "csv-import-bot"

_EMPTY_STRINGS = {"", "nan", "none", "n/a", "null", "na", "not available", "n/a.", "--", "-"}

KITCHEN_KEYWORDS = {
    "kitchen", "kitchenette", "full kitchen", "eat-in kitchen",
    "eat in kitchen", "galley kitchen", "open kitchen",
    "cooking", "stove", "oven", "range", "microwave",
    "refrigerator", "fridge", "dishwasher",
}

WASHER_KEYWORDS = {
    "washer", "washer/dryer", "washer and dryer", "washer & dryer",
    "laundry", "in-unit laundry", "in unit laundry",
    "on-site laundry", "on site laundry", "laundry facility",
    "laundry room", "laundry hookup", "laundry hook-up",
    "washing machine", "dryer", "w/d", "w/d hookup",
}

PARKING_KEYWORDS = {
    "parking", "parking space", "parking spot", "parking included",
    "off-street parking", "off street parking", "on-street parking",
    "assigned parking", "covered parking", "underground parking",
    "garage", "attached garage", "detached garage", "carport",
    "driveway", "private driveway",
}

# skip row if null count among {city, province, street, distance_to_university} >= this
MIN_NULL_THRESHOLD = 2

# Deterministic id base for CSV-imported rows: base + csv_row_index (1-based)
# Max safe row count = 2147483647 - SOURCE_ID_BASE = ~1002343647
SOURCE_ID_BASE = 1145140000
