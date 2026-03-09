from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `moods`
            ADD COLUMN `log_date` DATE NULL,
            ADD COLUMN `time_slot` VARCHAR(10) NULL,
            ADD COLUMN `mood_level` INT NULL;

        UPDATE `moods`
        SET
            `log_date` = COALESCE(`log_date`, DATE(`created_at`)),
            `time_slot` = COALESCE(
                `time_slot`,
                CASE
                    WHEN HOUR(`created_at`) < 11 THEN 'MORNING'
                    WHEN HOUR(`created_at`) < 15 THEN 'LUNCH'
                    WHEN HOUR(`created_at`) < 20 THEN 'EVENING'
                    ELSE 'BEDTIME'
                END
            ),
            `mood_level` = COALESCE(`mood_level`, `mood_score`, 4);

        DELETE m1
        FROM `moods` m1
        JOIN `moods` m2
          ON m1.`user_id` = m2.`user_id`
         AND m1.`log_date` = m2.`log_date`
         AND m1.`time_slot` = m2.`time_slot`
         AND m1.`mood_id` < m2.`mood_id`;

        ALTER TABLE `moods`
            MODIFY COLUMN `log_date` DATE NOT NULL,
            MODIFY COLUMN `time_slot` VARCHAR(10) NOT NULL,
            MODIFY COLUMN `mood_level` INT NOT NULL;

        ALTER TABLE `moods`
            DROP COLUMN `mood_score`,
            DROP COLUMN `note`;

        ALTER TABLE `moods`
            ADD UNIQUE KEY `uidx_moods_user_date_slot` (`user_id`, `log_date`, `time_slot`);

        CREATE INDEX `idx_moods_user_date` ON `moods` (`user_id`, `log_date`);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX `idx_moods_user_date` ON `moods`;

        ALTER TABLE `moods`
            DROP INDEX `uidx_moods_user_date_slot`;

        ALTER TABLE `moods`
            ADD COLUMN `mood_score` INT NULL,
            ADD COLUMN `note` LONGTEXT NULL;

        UPDATE `moods`
        SET `mood_score` = `mood_level`;

        ALTER TABLE `moods`
            DROP COLUMN `mood_level`,
            DROP COLUMN `time_slot`,
            DROP COLUMN `log_date`;
    """

