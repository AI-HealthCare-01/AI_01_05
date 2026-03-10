from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `chat_logs` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `message_content` LONGTEXT NOT NULL,
    `response_content` LONGTEXT NOT NULL,
    `is_flagged` BOOL NOT NULL DEFAULT 0,
    `alert_type` VARCHAR(20),
    `warning_level` VARCHAR(20) NOT NULL DEFAULT 'Normal',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_chat_logs_user_id_8d745e` (`user_id`)
) CHARACTER SET utf8mb4;
        ALTER TABLE `chat_logs` ADD COLUMN IF NOT EXISTS `alert_type` VARCHAR(20) NULL;
        ALTER TABLE `chat_logs` ADD COLUMN IF NOT EXISTS `warning_level` VARCHAR(20) NOT NULL DEFAULT 'Normal';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `chat_logs` DROP COLUMN IF EXISTS `warning_level`;
        ALTER TABLE `chat_logs` DROP COLUMN IF EXISTS `alert_type`;"""
