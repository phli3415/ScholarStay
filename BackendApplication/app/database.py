"""
database configuration and initialization module
use Tortoise ORM to connect to PostgreSQL database, support pgvector extension
"""

import os
from typing import Dict
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Tortoise-ORM Configuration Dictionary
TORTOISE_ORM: Dict = {
    "connections": {
        # PostgreSQL connection URL from environment variables
        "default": os.getenv("DATABASE_URL"),
    },
    "apps": {
        "models": {
            # List of all your models
            "models": [
                "app.model.user",
                "app.model.houses",
                "app.model.bookmark",
                "app.model.chat_history",
                "aerich.models"  # Required for migrations
            ],
            "default_connection": "default",
        },
    },
    # Optional settings
    "use_tz": False,
    "timezone": "UTC",
    "db_pool": {
        "max_size": 40,
        # Fewer idle connections kept open at once = fewer chances one of them
        # goes stale on the DB side between requests during low-traffic demo
        # usage (each stale connection costs a multi-second reconnect on its
        # next use). The pool still grows up to max_size under real load.
        "min_size": 1,
        "idle_timeout": 300
    }
}
