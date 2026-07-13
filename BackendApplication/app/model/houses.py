from tortoise.models import Model
from tortoise import fields


class Houses(Model):
    """
    Houses Model
    contains the address information, rental price, and facility information of the house
    contains the pgvector vector field for RAG retrieval
    """
    id = fields.IntField(pk=True)
    
    # address information
    province = fields.CharField(max_length=100, null=True, description="province")
    city = fields.CharField(max_length=100, null=True, description="city")
    street = fields.CharField(max_length=200, null=True, description="street")
    house_number = fields.CharField(max_length=50, null=True, description="house number")

    # price information
    monthly_rent = fields.DecimalField(max_digits=10, decimal_places=2, description="monthly rent")

    # facility information(boolean values)
    has_kitchen = fields.BooleanField(default=False, description="has kitchen")
    has_washer = fields.BooleanField(default=False, description="has washer")
    has_parking = fields.BooleanField(default=False, description="has parking")

    # status information
    is_rented = fields.BooleanField(default=False, description="is rented")

    # distance information
    distance_to_university = fields.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        description="distance to university"
    )
    
    # image data
    image_data = fields.BinaryField(null=True, description="house image data")
    landlord_phone_number = fields.CharField(max_length=20, description="landlord's phone number", null=True)
    
    # RAG vector field - using pgvector to store the vector representation of the house description
    # note: actually, you need to install pgvector extension and create the vector column through SQL
    # here we use TextField to store the vector, you can add the vector column through migration later
    embedding_vector = fields.TextField(null=True, description="vector representation of the house description(JSON format or base64 encoded)")
    description = fields.TextField(null=True, description="house description text, used to generate the vector")

    # import provenance: list of field names that were filled by LLM during CSV import
    # e.g. ["has_kitchen", "has_washer", "street"] — null means all fields came from raw CSV data
    llm_filled_fields = fields.JSONField(null=True, description="fields extracted by LLM during import; null = no LLM used")
    
    # association relationship: the house is created by the user
    owner = fields.ForeignKeyField(
        'models.User',
        related_name='houses',
        description="owner of the house"
    )
    
    # timestamp
    created_at = fields.DatetimeField(auto_now_add=True, description="created time")
    updated_at = fields.DatetimeField(auto_now=True, description="updated time")
    
    class Meta:
        table = "houses"
        table_description = "houses table"
        meta_schema = "ScholarStay"

        indexes = [
            ("province", "city"),  # compound index for province, city
            ("monthly_rent",),     # index for monthly rent
            ("is_rented",),        # index for rented status
        ]

