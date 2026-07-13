from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> None:
    await db.execute_script("""
        ALTER TABLE "houses" ADD COLUMN "llm_filled_fields" JSONB;
    """)


async def downgrade(db: BaseDBAsyncClient) -> None:
    await db.execute_script("""
        ALTER TABLE "houses" DROP COLUMN "llm_filled_fields";
    """)
