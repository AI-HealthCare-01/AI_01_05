"""Add red_alert and reasoning columns to chat_logs table.

Migration for LangGraph ReAct Agent with Pydantic Structured Output.
"""

from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `chat_logs` ADD COLUMN IF NOT EXISTS `red_alert` BOOLEAN DEFAULT FALSE;
        ALTER TABLE `chat_logs` ADD COLUMN IF NOT EXISTS `reasoning` TEXT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `chat_logs` DROP COLUMN IF EXISTS `red_alert`;
        ALTER TABLE `chat_logs` DROP COLUMN IF EXISTS `reasoning`;
    """
