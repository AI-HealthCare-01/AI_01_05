from datetime import time

from tortoise import fields, models


class UserSettings(models.Model):
    setting_id = fields.BigIntField(primary_key=True)
    user = fields.OneToOneField("models.User", related_name="settings", on_delete=fields.CASCADE)
    morning_time = fields.TimeField(default=time(6, 0))
    lunch_time = fields.TimeField(default=time(11, 0))
    evening_time = fields.TimeField(default=time(17, 0))
    bedtime_time = fields.TimeField(default=time(21, 0))
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_settings"
