from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `medicines` ADD `etc_otc_code` VARCHAR(10);
        ALTER TABLE `medicines` ADD `line_front` VARCHAR(100);
        ALTER TABLE `medicines` ADD `line_back` VARCHAR(100);
        ALTER TABLE `medicines` ADD `chart` LONGTEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `medicines` DROP COLUMN `etc_otc_code`;
        ALTER TABLE `medicines` DROP COLUMN `line_front`;
        ALTER TABLE `medicines` DROP COLUMN `line_back`;
        ALTER TABLE `medicines` DROP COLUMN `chart`;"""


MODELS_STATE = (
    "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"
)
