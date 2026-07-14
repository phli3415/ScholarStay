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

# US state abbreviations (includes DC)
_STATE_ABBREVS = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
}

# Full state name → abbreviation; "Washington DC" is a special compound entry
_STATE_NAMES_TO_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC", "Washington DC": "DC",
}

# Combined set for any general membership check
_US_STATES = _STATE_ABBREVS | set(_STATE_NAMES_TO_ABBREV.keys())
