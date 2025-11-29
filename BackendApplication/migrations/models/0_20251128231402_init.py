from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "gmail" VARCHAR(255) NOT NULL UNIQUE,
    "username" VARCHAR(100) NOT NULL,
    "password" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "users"."gmail" IS 'gmail address of the user, unique identifier';
COMMENT ON COLUMN "users"."username" IS 'username of the user';
COMMENT ON COLUMN "users"."password" IS 'password';
COMMENT ON COLUMN "users"."created_at" IS 'created time';
COMMENT ON COLUMN "users"."updated_at" IS 'updated time';
COMMENT ON TABLE "users" IS 'users table';
CREATE TABLE IF NOT EXISTS "houses" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "province" VARCHAR(100) NOT NULL,
    "city" VARCHAR(100) NOT NULL,
    "street" VARCHAR(200) NOT NULL,
    "house_number" VARCHAR(50) NOT NULL,
    "monthly_rent" DECIMAL(10,2) NOT NULL,
    "has_kitchen" BOOL NOT NULL  DEFAULT False,
    "has_washer" BOOL NOT NULL  DEFAULT False,
    "has_parking" BOOL NOT NULL  DEFAULT False,
    "is_rented" BOOL NOT NULL  DEFAULT False,
    "distance_to_university" DECIMAL(8,2) NOT NULL,
    "embedding_vector" TEXT,
    "description" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "owner_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_houses_provinc_5efd87" ON "houses" ("province", "city");
CREATE INDEX IF NOT EXISTS "idx_houses_monthly_657ee1" ON "houses" ("monthly_rent");
CREATE INDEX IF NOT EXISTS "idx_houses_is_rent_b026a9" ON "houses" ("is_rented");
COMMENT ON COLUMN "houses"."province" IS 'province';
COMMENT ON COLUMN "houses"."city" IS 'city';
COMMENT ON COLUMN "houses"."street" IS 'street';
COMMENT ON COLUMN "houses"."house_number" IS 'house number';
COMMENT ON COLUMN "houses"."monthly_rent" IS 'monthly rent';
COMMENT ON COLUMN "houses"."has_kitchen" IS 'has kitchen';
COMMENT ON COLUMN "houses"."has_washer" IS 'has washer';
COMMENT ON COLUMN "houses"."has_parking" IS 'has parking';
COMMENT ON COLUMN "houses"."is_rented" IS 'is rented';
COMMENT ON COLUMN "houses"."distance_to_university" IS 'distance to university';
COMMENT ON COLUMN "houses"."embedding_vector" IS 'vector representation of the house description(JSON format or base64 encoded)';
COMMENT ON COLUMN "houses"."description" IS 'house description text, used to generate the vector';
COMMENT ON COLUMN "houses"."created_at" IS 'created time';
COMMENT ON COLUMN "houses"."updated_at" IS 'updated time';
COMMENT ON COLUMN "houses"."owner_id" IS 'owner of the house';
COMMENT ON TABLE "houses" IS 'houses table';
CREATE TABLE IF NOT EXISTS "bookmarks" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "house_id" INT NOT NULL REFERENCES "houses" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_bookmarks_user_id_ddd8c9" UNIQUE ("user_id", "house_id")
);
COMMENT ON COLUMN "bookmarks"."created_at" IS 'created time';
COMMENT ON COLUMN "bookmarks"."house_id" IS 'house that was added to bookmarks';
COMMENT ON COLUMN "bookmarks"."user_id" IS 'user who added the house to bookmarks';
COMMENT ON TABLE "bookmarks" IS 'bookmarks table';
CREATE TABLE IF NOT EXISTS "chat_histories" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "session_id" VARCHAR(100) NOT NULL UNIQUE,
    "title" VARCHAR(200),
    "messages" JSONB NOT NULL,
    "metadata" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_chat_histor_user_id_62e455" ON "chat_histories" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_chat_histor_created_dff2cc" ON "chat_histories" ("created_at");
COMMENT ON COLUMN "chat_histories"."session_id" IS 'unique identifier of the chat session';
COMMENT ON COLUMN "chat_histories"."title" IS 'title of the chat session(can be automatically generated from the first sentence)';
COMMENT ON COLUMN "chat_histories"."messages" IS 'list of chat messages(JSON format)';
COMMENT ON COLUMN "chat_histories"."metadata" IS 'metadata(JSON format)';
COMMENT ON COLUMN "chat_histories"."created_at" IS 'created time';
COMMENT ON COLUMN "chat_histories"."updated_at" IS 'updated time';
COMMENT ON COLUMN "chat_histories"."user_id" IS 'user who has the chat session';
COMMENT ON TABLE "chat_histories" IS 'Agent chat history table';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
