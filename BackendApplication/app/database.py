"""
database configuration and initialization module
use Tortoise ORM to connect to PostgreSQL database, support pgvector extension
"""

from tortoise import Tortoise
# from app.model import TORTOISE_ORM_MODELS
import os
import dotenv
dotenv.load_dotenv()
from fastapi import FastAPI
from typing import Dict

app=FastAPI()   

# Tortoise-ORM 配置
TORTOISE_ORM: Dict = {
    "connections": {
        # PostgreSQL
        "default": os.getenv("DATABASE_URL"),

    },
    "apps": {
        "models": {
            "models": [
                "app.model.user",
                "app.model.houses",
                "app.model.bookmark",
                "app.model.chat_history",
                "aerich.models"
            ],  # models and Aerich
            "default_connection": "default",
        },
    },
    # connection pool     
    "use_tz": False,  # whether to use timezone
    "timezone": "UTC",  # default timezone
    "db_pool": {
        "max_size": 10,  # maximum connection pool size
        "min_size": 1,  # minimum connection pool size
        "idle_timeout": 30  # idle connection timeout (seconds)
    }
}

from tortoise.contrib.fastapi import register_tortoise

register_tortoise(app, 
                  config=TORTOISE_ORM, 
                  generate_schemas=True, #generate schemas in development environment
                  add_exception_handlers=True)#add exception handlers

