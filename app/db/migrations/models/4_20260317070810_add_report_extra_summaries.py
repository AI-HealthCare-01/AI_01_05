from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `reports` ADD `clinician_note` LONGTEXT;
        ALTER TABLE `reports` ADD `mood_summary` LONGTEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `reports` DROP COLUMN `clinician_note`;
        ALTER TABLE `reports` DROP COLUMN `mood_summary`;"""


MODELS_STATE = (
    "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"
    "NIoZ"
)
