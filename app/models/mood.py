from tortoise import fields, models


class Mood(models.Model):
    mood_id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="moods")
    log_date = fields.DateField()
    time_slot = fields.CharField(max_length=10)
    mood_level = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "moods"
        unique_together = (("user", "log_date", "time_slot"),)
        indexes = (("user", "log_date"),)
