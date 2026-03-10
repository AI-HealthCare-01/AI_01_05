from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        SET @col_exists := (
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = 'onboarding_completed'
        );

        SET @ddl := IF(
            @col_exists = 0,
            'ALTER TABLE `users` ADD COLUMN `onboarding_completed` BOOL NOT NULL DEFAULT 0',
            'SELECT 1'
        );

        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        SET @col_exists := (
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = 'onboarding_completed'
        );

        SET @ddl := IF(
            @col_exists > 0,
            'ALTER TABLE `users` DROP COLUMN `onboarding_completed`',
            'SELECT 1'
        );

        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    """

