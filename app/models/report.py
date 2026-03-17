from tortoise import fields, models


class Report(models.Model):
    report_id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="reports")
    start_date = fields.DateField()
    end_date = fields.DateField()
    summary = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    mood_summary = fields.TextField(null=True)
    clinician_note = fields.TextField(null=True)
    class Meta:
        table = "reports"
