from tortoise.models import Model
from tortoise import fields


class ChatHistory(Model):
    """
    Agent Chat History Model
    each user can have multiple chat sessions
    each chat session contains multiple message records
    """
    id = fields.IntField(pk=True)
    
    # association relationship: the chat session belongs to a user
    user = fields.ForeignKeyField(
        'models.User',
        related_name='chat_sessions',
        description="user who has the chat session"
    )
    
    # chat session information
    session_id = fields.CharField(
        max_length=100,
        unique=True,
        description="unique identifier of the chat session"
    )
    title = fields.CharField(
        max_length=200,
        null=True,
        description="title of the chat session(can be automatically generated from the first sentence)"
    )
    
    # message content(stored as JSON format)
    # 格式: [{"role": "user/assistant", "content": "...", "timestamp": "..."}, ...]
    messages = fields.JSONField(
        default=list,
        description="list of chat messages(JSON format)"
    )
    
    # metadata(stored extra session information, such as filtering conditions, compared house IDs, etc.)
    metadata = fields.JSONField(
        default=dict,
        description="metadata(JSON format)"
    )
    
    # timestamp
    created_at = fields.DatetimeField(auto_now_add=True, description="created time")
    updated_at = fields.DatetimeField(auto_now=True, description="updated time")
    
    class Meta:
        table = "chat_histories"
        table_description = "Agent chat history table"
        meta_schema = "ScholarStay"

        indexes = [
            ("user",),  # index for user
            ("created_at",),  # index for created time
        ]

