from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "firebase_uid" VARCHAR(255) NOT NULL UNIQUE;
        ALTER TABLE "users" DROP COLUMN "password";
        ALTER TABLE "houses" ADD "image_data" BYTEA;
        CREATE UNIQUE INDEX "uid_users_firebas_6d1613" ON "users" ("firebase_uid");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_users_firebas_6d1613";
        ALTER TABLE "users" ADD "password" VARCHAR(255) NOT NULL;
        ALTER TABLE "users" DROP COLUMN "firebase_uid";
        ALTER TABLE "houses" DROP COLUMN "image_data";"""
