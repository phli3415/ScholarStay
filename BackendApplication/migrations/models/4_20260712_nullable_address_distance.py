from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> None:
    await db.execute_script("""
        ALTER TABLE "houses" ALTER COLUMN "province"               DROP NOT NULL;
        ALTER TABLE "houses" ALTER COLUMN "city"                   DROP NOT NULL;
        ALTER TABLE "houses" ALTER COLUMN "street"                 DROP NOT NULL;
        ALTER TABLE "houses" ALTER COLUMN "house_number"           DROP NOT NULL;
        ALTER TABLE "houses" ALTER COLUMN "distance_to_university" DROP NOT NULL;
    """)


async def downgrade(db: BaseDBAsyncClient) -> None:
    await db.execute_script("""
        ALTER TABLE "houses" ALTER COLUMN "distance_to_university" SET NOT NULL;
        ALTER TABLE "houses" ALTER COLUMN "house_number"           SET NOT NULL;
        ALTER TABLE "houses" ALTER COLUMN "street"                 SET NOT NULL;
        ALTER TABLE "houses" ALTER COLUMN "city"                   SET NOT NULL;
        ALTER TABLE "houses" ALTER COLUMN "province"               SET NOT NULL;
    """)
