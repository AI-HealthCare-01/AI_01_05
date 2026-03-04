from tortoise import fields, models


class Appointment(models.Model):
    appointment_id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="appointments")
    appointment_date = fields.DateField(null=True)
    hospital_name = fields.CharField(max_length=255, null=True)
    notes = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "appointments"
