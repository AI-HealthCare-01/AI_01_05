from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `chat_logs` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `message_content` LONGTEXT NOT NULL,
    `response_content` LONGTEXT NOT NULL,
    `is_flagged` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `chat_logs`;"""


MODELS_STATE = (
    "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"
)
