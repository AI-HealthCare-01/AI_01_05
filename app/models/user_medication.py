from tortoise import fields, models


class UserMedication(models.Model):
    medication_id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="user_medications", on_delete=fields.CASCADE)
    medicine = fields.ForeignKeyField(
        "models.Medicine",
        related_name="user_medications",
        on_delete=fields.RESTRICT,
        to_field="item_seq",
    )
    dose_per_intake = fields.DecimalField(max_digits=5, decimal_places=2)
    daily_frequency = fields.SmallIntField()
    total_days = fields.IntField()
    start_date = fields.DateField()
    meal_time_pref = fields.CharField(max_length=20, null=True)
    time_slots = fields.JSONField()
    status = fields.CharField(max_length=20, default="ACTIVE")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_medications"
        indexes = [("user_id", "status"), ("start_date",)]
