from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `medication_logs` DROP FOREIGN KEY `fk_medicati_medicati_ae5f8cc3`;
        ALTER TABLE `medication_logs` DROP INDEX `uid_medication__prescri_e2cae6`;
        ALTER TABLE `medication_logs` MODIFY COLUMN `prescription_id` BIGINT;
        ALTER TABLE `medication_logs` ADD `user_medication_id` BIGINT;
        ALTER TABLE `medication_logs` ADD `time_slot` VARCHAR(20);
        ALTER TABLE `medication_logs` ADD CONSTRAINT `fk_medicati_medicati_ae5f8cc3` FOREIGN KEY (`prescription_id`) REFERENCES `medication_prescriptions` (`prescription_id`) ON DELETE CASCADE;
        ALTER TABLE `medication_logs` ADD CONSTRAINT `fk_medicati_user_med_6d69ad6c` FOREIGN KEY (`user_medication_id`) REFERENCES `user_medications` (`medication_id`) ON DELETE CASCADE;
        ALTER TABLE `medication_logs` ADD UNIQUE INDEX `uid_medication__user_me_7959e9` (`user_medication_id`, `log_date`, `time_slot`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `medication_logs` DROP INDEX `uid_medication__user_me_7959e9`;
        ALTER TABLE `medication_logs` DROP FOREIGN KEY `fk_medicati_user_med_6d69ad6c`;
        ALTER TABLE `medication_logs` DROP COLUMN `user_medication_id`;
        ALTER TABLE `medication_logs` DROP COLUMN `time_slot`;
        ALTER TABLE `medication_logs` DROP FOREIGN KEY `fk_medicati_medicati_ae5f8cc3`;
        ALTER TABLE `medication_logs` MODIFY COLUMN `prescription_id` BIGINT NOT NULL;
        ALTER TABLE `medication_logs` ADD UNIQUE INDEX `uid_medication__prescri_e2cae6` (`prescription_id`, `log_date`);
        ALTER TABLE `medication_logs` ADD CONSTRAINT `fk_medicati_medicati_ae5f8cc3` FOREIGN KEY (`prescription_id`) REFERENCES `medication_prescriptions` (`prescription_id`) ON DELETE CASCADE;"""


MODELS_STATE = (
    "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"
)
