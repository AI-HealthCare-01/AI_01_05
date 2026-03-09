from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `medication_prescriptions` (
    `prescription_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `drug_name` VARCHAR(100) NOT NULL,
    `dosage` VARCHAR(50) NOT NULL,
    `frequency` VARCHAR(50) NOT NULL,
    `start_date` DATE NOT NULL,
    `end_date` DATE,
    `hospital_name` VARCHAR(255),
    `notes` LONGTEXT,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_medicati_users_e45c8580` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `medication_logs` (
    `log_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `log_date` DATE NOT NULL,
    `taken_at` DATETIME(6),
    `is_taken` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `prescription_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_medication__prescri_e2cae6` (`prescription_id`, `log_date`),
    CONSTRAINT `fk_medicati_medicati_ae5f8cc3` FOREIGN KEY (`prescription_id`) REFERENCES `medication_prescriptions` (`prescription_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_medicati_users_9ad8ed1d` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `user_characters` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `character_id` INT NOT NULL,
    `selected_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_user_cha_users_bb28de2b` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        ALTER TABLE `users` ADD `onboarding_completed` BOOL NOT NULL DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP COLUMN `onboarding_completed`;
        DROP TABLE IF EXISTS `medication_logs`;
        DROP TABLE IF EXISTS `user_characters`;
        DROP TABLE IF EXISTS `medication_prescriptions`;"""


MODELS_STATE = (
    "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"
    "a2kyO7Rt7ry//ks2nR"
)
