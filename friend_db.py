from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fastapi import FastAPI
from tortoise import Tortoise, fields, models
from tortoise.contrib.fastapi import register_tortoise

from app.core import config


class CharacterId(StrEnum):
    CHAMKKAE = "참깨"
    DEULKKAE = "들깨"
    TONGKKAE = "통깨"
    HEUKKKAE = "흑깨"


@dataclass(frozen=True)
class CharacterSeed:
    id: CharacterId
    name: str
    description: str
    image_file: str
    display_order: int


CHARACTER_SEEDS: tuple[CharacterSeed, ...] = (
    CharacterSeed(
        id=CharacterId.CHAMKKAE,
        name="참깨",
        description="장난기 많은 천진난만함으로 웃음을 건네는 친구",
        image_file="chamkkae.jpeg",
        display_order=1,
    ),
    CharacterSeed(
        id=CharacterId.DEULKKAE,
        name="들깨",
        description="걱정을 먼저 알아채고 한없이 보살펴주는 다정한 친구",
        image_file="deulkkae.jpeg",
        display_order=2,
    ),
    CharacterSeed(
        id=CharacterId.TONGKKAE,
        name="통깨",
        description="귀엽고 공감 리액션이 뛰어나 기분을 밝혀주는 친구",
        image_file="tongkkae.jpeg",
        display_order=3,
    ),
    CharacterSeed(
        id=CharacterId.HEUKKKAE,
        name="흑깨",
        description="하나부터 열까지 차근차근 알려주는 친절한 친구",
        image_file="heukkkae.jpeg",
        display_order=4,
    ),
)


class FriendCharacter(models.Model):
    id = fields.CharField(pk=True, max_length=16)
    name = fields.CharField(max_length=32)
    description = fields.CharField(max_length=255)
    image_file = fields.CharField(max_length=120, null=True)
    display_order = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "friend_characters"


class FriendUser(models.Model):
    id = fields.BigIntField(pk=True)
    selected_character = fields.ForeignKeyField(
        "models.FriendCharacter",
        related_name="selected_users",
        null=True,
        on_delete=fields.SET_NULL,
        source_field="selected_character_id",
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "friend_users"


class FriendUserProfile(models.Model):
    user = fields.OneToOneField(
        "models.FriendUser",
        pk=True,
        related_name="profile",
        on_delete=fields.CASCADE,
        source_field="user_id",
    )
    nickname = fields.CharField(max_length=40, null=True)
    profile_image_url = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "friend_user_profiles"


class FriendUserVisitSchedule(models.Model):
    user = fields.OneToOneField(
        "models.FriendUser",
        pk=True,
        related_name="visit_schedule",
        on_delete=fields.CASCADE,
        source_field="user_id",
    )
    next_visit_date = fields.DateField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "friend_user_visit_schedules"


class FriendUserUiPreference(models.Model):
    user = fields.OneToOneField(
        "models.FriendUser",
        pk=True,
        related_name="ui_preference",
        on_delete=fields.CASCADE,
        source_field="user_id",
    )
    top_toggle_highlight = fields.CharField(max_length=20, null=True)
    nameplate_animation_enabled = fields.BooleanField(default=False)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "friend_user_ui_preferences"


class FriendUserMedicationSchedule(models.Model):
    user = fields.OneToOneField(
        "models.FriendUser",
        pk=True,
        related_name="medication_schedule",
        on_delete=fields.CASCADE,
        source_field="user_id",
    )
    morning_time = fields.CharField(max_length=5, default="06:00")
    lunch_time = fields.CharField(max_length=5, default="11:00")
    evening_time = fields.CharField(max_length=5, default="17:00")
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "friend_user_medication_schedules"


class FriendMedicationPlan(models.Model):
    id = fields.CharField(pk=True, max_length=64)
    user = fields.ForeignKeyField(
        "models.FriendUser",
        related_name="medication_plans",
        on_delete=fields.CASCADE,
        source_field="user_id",
    )
    name = fields.CharField(max_length=80)
    times_per_day = fields.IntField()
    dose_per_take = fields.FloatField()
    total_days = fields.IntField()
    start_date = fields.DateField()
    medicine_image_url = fields.CharField(max_length=500, null=True)
    medicine_effect_summary = fields.CharField(max_length=500, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "friend_medication_plans"


class FriendMedicationIntakeLog(models.Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField(
        "models.FriendUser",
        related_name="medication_intake_logs",
        on_delete=fields.CASCADE,
        source_field="user_id",
    )
    medication_plan = fields.ForeignKeyField(
        "models.FriendMedicationPlan",
        related_name="intake_logs",
        on_delete=fields.CASCADE,
        source_field="medication_plan_id",
    )
    intake_date = fields.DateField()
    slot = fields.CharField(max_length=10)
    checked = fields.BooleanField(default=True)
    checked_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "friend_medication_intake_logs"
        unique_together = (("user", "medication_plan", "intake_date", "slot"),)


class FriendMoodSticker(models.Model):
    id = fields.BigIntField(pk=True)
    user = fields.ForeignKeyField(
        "models.FriendUser",
        related_name="mood_stickers",
        on_delete=fields.CASCADE,
        source_field="user_id",
    )
    mood_date = fields.DateField()
    mood_id = fields.CharField(max_length=40)
    mood_label = fields.CharField(max_length=40)
    mood_sticker = fields.CharField(max_length=40)
    saved_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "friend_mood_stickers"


TORTOISE_APP_MODELS = [
    "aerich.models",
    "friend_db",
]


def build_tortoise_orm() -> dict:
    return {
        "connections": {
            "default": {
                "engine": "tortoise.backends.mysql",
                "dialect": "asyncmy",
                "credentials": {
                    "host": config.DB_HOST,
                    "port": config.DB_PORT,
                    "user": config.DB_USER,
                    "password": config.DB_PASSWORD,
                    "database": config.DB_NAME,
                    "connect_timeout": config.DB_CONNECT_TIMEOUT,
                    "maxsize": config.DB_CONNECTION_POOL_MAXSIZE,
                },
            },
        },
        "apps": {
            "models": {
                "models": TORTOISE_APP_MODELS,
            },
        },
        "timezone": "Asia/Seoul",
    }


def initialize_friend_tortoise(app: FastAPI, *, generate_schemas: bool = True) -> None:
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=build_tortoise_orm(), generate_schemas=generate_schemas)


async def bootstrap_friend_data() -> None:
    for seed in CHARACTER_SEEDS:
        await FriendCharacter.update_or_create(
            id=seed.id.value,
            defaults={
                "name": seed.name,
                "description": seed.description,
                "image_file": seed.image_file,
                "display_order": seed.display_order,
            },
        )


async def ensure_friend_user(user_id: int) -> FriendUser:
    user, _ = await FriendUser.get_or_create(id=user_id)
    await FriendUserProfile.get_or_create(user=user)
    await FriendUserVisitSchedule.get_or_create(user=user)
    await FriendUserUiPreference.get_or_create(user=user)
    await FriendUserMedicationSchedule.get_or_create(user=user)
    await user.fetch_related("selected_character")
    return user
