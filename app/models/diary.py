from tortoise import fields, models


class Diary(models.Model):
    diary_id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="diaries")
    diary_date = fields.DateField()
    title = fields.CharField(max_length=255, null=True)
    content = fields.TextField()
    write_method = fields.CharField(max_length=20, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "diaries"
