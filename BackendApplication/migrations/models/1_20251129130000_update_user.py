from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "password";
        ALTER TABLE "users" ADD "firebase_uid" VARCHAR(255) NOT NULL UNIQUE;
        CREATE UNIQUE INDEX "uid_users_firebas_4f2f39" ON "users" ("firebase_uid");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "password" VARCHAR(255) NOT NULL;
        ALTER TABLE "users" DROP COLUMN "firebase_uid";
    """
