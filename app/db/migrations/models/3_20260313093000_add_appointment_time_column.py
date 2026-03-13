from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `appointments`
        ADD COLUMN IF NOT EXISTS `appointment_time` TIME NULL AFTER `appointment_date`;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `appointments`
        DROP COLUMN IF EXISTS `appointment_time`;
    """


MODELS_STATE = ""
