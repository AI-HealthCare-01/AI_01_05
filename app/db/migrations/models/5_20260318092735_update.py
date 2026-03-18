from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `chat_logs` ADD `red_alert` BOOL NOT NULL DEFAULT 0;
        ALTER TABLE `chat_logs` ADD `reasoning` LONGTEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `chat_logs` DROP COLUMN `red_alert`;
        ALTER TABLE `chat_logs` DROP COLUMN `reasoning`;"""


MODELS_STATE = (
    "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"
    "5orfW2wve9JWJjB4y3bX26vz0XqvM3j9H8AVZJg="
)
