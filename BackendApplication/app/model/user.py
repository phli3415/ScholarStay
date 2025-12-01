from tortoise.models import Model
from tortoise import fields


class User(Model):
    """
    User Model
    each user has a unique gmail and username. Authentication is handled by Firebase.
    """
    id = fields.IntField(pk=True)
    firebase_uid = fields.CharField(max_length=255, unique=True, description="Firebase Unique ID")
    gmail = fields.CharField(max_length=255, unique=True, description="gmail address of the user, unique identifier")
    username = fields.CharField(max_length=100, description="username of the user")
    
    # timestamp
    created_at = fields.DatetimeField(auto_now_add=True, description="created time")
    updated_at = fields.DatetimeField(auto_now=True, description="updated time")
    
    class Meta:
        table = "users"
        table_description = "users table"
        meta_schema = "ScholarStay"
