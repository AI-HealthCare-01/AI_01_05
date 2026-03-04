from tortoise import fields, models


class Mood(models.Model):
    mood_id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="moods")
    mood_score = fields.IntField(null=True)
    note = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "moods"
