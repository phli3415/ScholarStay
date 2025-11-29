"""
ScholarStay Backend Application
"""

# Import database module to ensure TORTOISE_ORM is accessible for Aerich
# This ensures that app.database.TORTOISE_ORM can be found by Aerich
from . import database  # noqa: F401

__all__ = ["database"]
