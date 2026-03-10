from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
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
CREATE TABLE IF NOT EXISTS `users` (
    `user_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `nickname` VARCHAR(10) NOT NULL,
    `email` VARCHAR(40),
    `gender` VARCHAR(7) NOT NULL COMMENT 'MALE: MALE\nFEMALE: FEMALE\nUNKNOWN: UNKNOWN' DEFAULT 'UNKNOWN',
    `birthday` DATE,
    `phone_number` VARCHAR(11) NOT NULL UNIQUE,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `is_admin` BOOL NOT NULL DEFAULT 0,
    `last_login` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `kakao_id` VARCHAR(255) NOT NULL UNIQUE,
    `terms_agreed` BOOL NOT NULL DEFAULT 0,
    `privacy_agreed` BOOL NOT NULL DEFAULT 0,
    `sensitive_agreed` BOOL NOT NULL DEFAULT 0,
    `marketing_agreed` BOOL NOT NULL DEFAULT 0,
    `onboarding_completed` BOOL NOT NULL DEFAULT 0,
    KEY `idx_users_kakao_i_7551dc` (`kakao_id`)
) CHARACTER SET utf8mb4;
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
CREATE TABLE IF NOT EXISTS `moods` (
    `mood_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `log_date` DATE NOT NULL,
    `time_slot` VARCHAR(10) NOT NULL,
    `mood_level` INT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_moods_user_id_f9a143` (`user_id`, `log_date`, `time_slot`),
    CONSTRAINT `fk_moods_users_55ce4f45` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
    KEY `idx_moods_user_id_0b3a8d` (`user_id`, `log_date`)
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
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `user_characters` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `character_id` INT NOT NULL,
    `selected_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_user_cha_users_bb28de2b` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
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
        """


MODELS_STATE = (
    "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"
    "WP"
)
