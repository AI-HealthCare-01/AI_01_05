from tortoise import fields, models


class ChatLog(models.Model):
    id = fields.BigIntField(primary_key=True)
    user_id = fields.BigIntField()
    message_content = fields.TextField()
    response_content = fields.TextField()
    is_flagged = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_logs"
