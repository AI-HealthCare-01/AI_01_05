from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `medicines` (
    `item_seq` VARCHAR(20) NOT NULL PRIMARY KEY,
    `item_name` VARCHAR(255) NOT NULL,
    `search_keyword` VARCHAR(255),
    `entp_name` VARCHAR(100),
    `print_front` VARCHAR(100),
    `print_back` VARCHAR(100),
    `drug_shape` VARCHAR(50),
    `color_class` VARCHAR(50),
    `efcy_qesitm` LONGTEXT,
    `use_method_qesitm` LONGTEXT,
    `item_image` VARCHAR(500),
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_medicines_search__17c423` (`search_keyword`),
    KEY `idx_medicines_print_f_e11098` (`print_front`),
    KEY `idx_medicines_print_b_52a41f` (`print_back`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `user_medications` (
    `medication_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `dose_per_intake` DECIMAL(5,2) NOT NULL,
    `daily_frequency` SMALLINT NOT NULL,
    `total_days` INT NOT NULL,
    `start_date` DATE NOT NULL,
    `meal_time_pref` VARCHAR(20),
    `time_slots` JSON NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `medicine_id` VARCHAR(20) NOT NULL,
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_user_med_medicine_c4f13dcc` FOREIGN KEY (`medicine_id`) REFERENCES `medicines` (`item_seq`) ON DELETE RESTRICT,
    CONSTRAINT `fk_user_med_users_b35bc9c4` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
    KEY `idx_user_medica_user_id_e52e18` (`user_id`, `status`),
    KEY `idx_user_medica_start_d_3ab451` (`start_date`)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `user_medications`;
        DROP TABLE IF EXISTS `medicines`;"""


MODELS_STATE = (
    "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"
)
