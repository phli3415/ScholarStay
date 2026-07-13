from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> None:
    await db.execute_script("""
        ALTER TABLE "users" ALTER COLUMN "firebase_uid" TYPE VARCHAR(255) USING "firebase_uid"::VARCHAR(255);
        ALTER TABLE "users" ALTER COLUMN "username" TYPE VARCHAR(100) USING "username"::VARCHAR(100);
        ALTER TABLE "users" ALTER COLUMN "gmail" TYPE VARCHAR(255) USING "gmail"::VARCHAR(255);
        ALTER TABLE "houses" ADD "landlord_phone_number" VARCHAR(20);
        ALTER TABLE "houses" ALTER COLUMN "house_number" TYPE VARCHAR(50) USING "house_number"::VARCHAR(50);
        ALTER TABLE "houses" ALTER COLUMN "city" TYPE VARCHAR(100) USING "city"::VARCHAR(100);
        ALTER TABLE "houses" ALTER COLUMN "owner_id" TYPE INT USING "owner_id"::INT;
        ALTER TABLE "houses" ALTER COLUMN "province" TYPE VARCHAR(100) USING "province"::VARCHAR(100);
        ALTER TABLE "houses" ALTER COLUMN "street" TYPE VARCHAR(200) USING "street"::VARCHAR(200);
        ALTER TABLE "bookmarks" ALTER COLUMN "house_id" TYPE INT USING "house_id"::INT;
        ALTER TABLE "bookmarks" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "chat_histories" ALTER COLUMN "title" TYPE VARCHAR(200) USING "title"::VARCHAR(200);
        ALTER TABLE "chat_histories" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "chat_histories" ALTER COLUMN "session_id" TYPE VARCHAR(100) USING "session_id"::VARCHAR(100);
    """)


async def downgrade(db: BaseDBAsyncClient) -> None:
    await db.execute_script("""
        ALTER TABLE "users" ALTER COLUMN "firebase_uid" TYPE VARCHAR(255) USING "firebase_uid"::VARCHAR(255);
        ALTER TABLE "users" ALTER COLUMN "username" TYPE VARCHAR(100) USING "username"::VARCHAR(100);
        ALTER TABLE "users" ALTER COLUMN "gmail" TYPE VARCHAR(255) USING "gmail"::VARCHAR(255);
        ALTER TABLE "houses" DROP COLUMN "landlord_phone_number";
        ALTER TABLE "houses" ALTER COLUMN "house_number" TYPE VARCHAR(50) USING "house_number"::VARCHAR(50);
        ALTER TABLE "houses" ALTER COLUMN "city" TYPE VARCHAR(100) USING "city"::VARCHAR(100);
        ALTER TABLE "houses" ALTER COLUMN "owner_id" TYPE INT USING "owner_id"::INT;
        ALTER TABLE "houses" ALTER COLUMN "province" TYPE VARCHAR(100) USING "province"::VARCHAR(100);
        ALTER TABLE "houses" ALTER COLUMN "street" TYPE VARCHAR(200) USING "street"::VARCHAR(200);
        ALTER TABLE "bookmarks" ALTER COLUMN "house_id" TYPE INT USING "house_id"::INT;
        ALTER TABLE "bookmarks" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "chat_histories" ALTER COLUMN "title" TYPE VARCHAR(200) USING "title"::VARCHAR(200);
        ALTER TABLE "chat_histories" ALTER COLUMN "user_id" TYPE INT USING "user_id"::INT;
        ALTER TABLE "chat_histories" ALTER COLUMN "session_id" TYPE VARCHAR(100) USING "session_id"::VARCHAR(100);
    """)
