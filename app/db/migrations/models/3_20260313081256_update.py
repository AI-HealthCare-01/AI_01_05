from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `appointments` ADD `appointment_time` TIME(6);
        ALTER TABLE `medicines` DROP COLUMN `line_back`;
        ALTER TABLE `medicines` DROP COLUMN `etc_otc_code`;
        ALTER TABLE `medicines` DROP COLUMN `line_front`;
        ALTER TABLE `medicines` DROP COLUMN `chart`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `medicines` ADD `line_back` VARCHAR(100);
        ALTER TABLE `medicines` ADD `etc_otc_code` VARCHAR(10);
        ALTER TABLE `medicines` ADD `line_front` VARCHAR(100);
        ALTER TABLE `medicines` ADD `chart` LONGTEXT;
        ALTER TABLE `appointments` DROP COLUMN `appointment_time`;"""


MODELS_STATE = (
    "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"
    "vKGAZvyep6OzqfbPc6g9f/AUNip8Y="
)
