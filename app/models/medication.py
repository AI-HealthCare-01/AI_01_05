from tortoise import fields, models


class MedicationPrescription(models.Model):
    prescription_id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="prescriptions", on_delete=fields.CASCADE)
    drug_name = fields.CharField(max_length=100)
    dosage = fields.CharField(max_length=50)
    frequency = fields.CharField(max_length=50)
    start_date = fields.DateField()
    end_date = fields.DateField(null=True)
    hospital_name = fields.CharField(max_length=255, null=True)
    notes = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medication_prescriptions"


class MedicationLog(models.Model):
    log_id = fields.BigIntField(primary_key=True)
    prescription = fields.ForeignKeyField(
        "models.MedicationPrescription", related_name="logs", on_delete=fields.CASCADE
    )
    user = fields.ForeignKeyField("models.User", related_name="medication_logs", on_delete=fields.CASCADE)
    log_date = fields.DateField()
    taken_at = fields.DatetimeField(null=True)
    is_taken = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medication_logs"
        unique_together = (("prescription_id", "log_date"),)
