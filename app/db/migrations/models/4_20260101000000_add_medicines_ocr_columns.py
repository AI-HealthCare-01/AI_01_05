from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `medicines`
            ADD COLUMN `etc_otc_code` VARCHAR(10) NULL,
            ADD COLUMN `chart` LONGTEXT NULL,
            ADD COLUMN `line_front` VARCHAR(100) NULL,
            ADD COLUMN `line_back` VARCHAR(100) NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `medicines`
            DROP COLUMN `etc_otc_code`,
            DROP COLUMN `chart`,
            DROP COLUMN `line_front`,
            DROP COLUMN `line_back`;
    """
