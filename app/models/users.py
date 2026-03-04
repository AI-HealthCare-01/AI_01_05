from enum import StrEnum

from tortoise import fields, models


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    UNKNOWN = "UNKNOWN"


class User(models.Model):
    user_id = fields.BigIntField(primary_key=True)
    nickname = fields.CharField(max_length=10)
    email = fields.CharField(max_length=40, null=True)
    gender = fields.CharEnumField(enum_type=Gender, default=Gender.UNKNOWN)
    birthday = fields.DateField(null=True)
    phone_number = fields.CharField(max_length=11, unique=True)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    kakao_id = fields.CharField(max_length=255, unique=True, index=True)
    terms_agreed = fields.BooleanField(default=False)
    privacy_agreed = fields.BooleanField(default=False)
    sensitive_agreed = fields.BooleanField(default=False)
    marketing_agreed = fields.BooleanField(default=False)

    class Meta:
        table = "users"
