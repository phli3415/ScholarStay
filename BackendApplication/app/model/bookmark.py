from tortoise.models import Model
from tortoise import fields


class Bookmark(Model):
    """
    Bookmark Model
    users can add houses to bookmarks
    this is a many-to-many relationship table between users and houses
    """
    id = fields.IntField(pk=True)
    
    # association relationship
    user = fields.ForeignKeyField(
        'models.User',
        related_name='bookmarks',
        description="user who added the house to bookmarks"
    )
    
    house = fields.ForeignKeyField(
        'models.Houses',
        related_name='bookmarked_by',
        description="house that was added to bookmarks"
    )
    
    # timestamp
    created_at = fields.DatetimeField(auto_now_add=True, description="created time")
    
    class Meta:
        table = "bookmarks"
        table_description = "bookmarks table"
        # ensure that the same user cannot add the same house to bookmarks multiple times
        unique_together = (("user", "house"),)
        meta_schema = "ScholarStay"

