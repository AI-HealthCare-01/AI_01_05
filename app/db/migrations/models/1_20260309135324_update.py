from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `appointments` (
    `appointment_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `appointment_date` DATE,
    `hospital_name` VARCHAR(255),
    `notes` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_appointm_users_bfbb061d` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `diaries` (
    `diary_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `diary_date` DATE NOT NULL,
    `title` VARCHAR(255),
    `content` LONGTEXT NOT NULL,
    `write_method` VARCHAR(20),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `deleted_at` DATETIME(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_diaries_users_3e642be8` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `moods` (
    `mood_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `mood_score` INT,
    `note` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_moods_users_55ce4f45` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `reports` (
    `report_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `start_date` DATE NOT NULL,
    `end_date` DATE NOT NULL,
    `summary` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_reports_users_938662cd` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `moods`;
        DROP TABLE IF EXISTS `appointments`;
        DROP TABLE IF EXISTS `reports`;
        DROP TABLE IF EXISTS `diaries`;"""


MODELS_STATE = (
    "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"
    "ihJI3Aa3PoP4frsKUdj8VcG3/wA59N6x"
)
