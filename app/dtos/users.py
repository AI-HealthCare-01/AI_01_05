from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.dtos.base import BaseSerializerModel
from app.models.users import Gender
from app.validators.common import optional_after_validator
from app.validators.user_validators import validate_birthday, validate_phone_number


class UserUpdateRequest(BaseModel):
    nickname: Annotated[str | None, Field(None, min_length=1, max_length=10)]
    email: Annotated[
        EmailStr | None,
        Field(None, max_length=40),
    ]
    phone_number: Annotated[
        str | None,
        Field(None, description="Available Format: +8201011112222, 01011112222, 010-1111-2222"),
        optional_after_validator(validate_phone_number),
    ]
    birthday: Annotated[
        date | None,
        Field(None, description="Date Format: YYYY-MM-DD"),
        optional_after_validator(validate_birthday),
    ]
    gender: Annotated[
        Gender | None,
        Field(None, description="'MALE' or 'FEMALE'"),
    ]
    marketing_agreed: bool | None = None
    sms_agreed: bool | None = None


class UserInfoResponse(BaseSerializerModel):
    user_id: int
    nickname: str
    email: str | None = None
    phone_number: str = Field("")
    birthday: date | None = None
    gender: Gender = Field(Gender.UNKNOWN)
    created_at: datetime = Field(default_factory=datetime.now)
    onboarding_completed: bool = False
    marketing_agreed: bool = False
    sms_agreed: bool = False

    @model_validator(mode="before")
    @classmethod
    def _map_from_orm(cls, data: object) -> object:
        if not isinstance(data, dict):
            return {
                "user_id": getattr(data, "user_id", 0),
                "nickname": getattr(data, "nickname", ""),
                "email": getattr(data, "email", None),
                "phone_number": getattr(data, "phone_number", ""),
                "birthday": getattr(data, "birthday", None),
                "gender": getattr(data, "gender", Gender.UNKNOWN),
                "created_at": getattr(data, "created_at", None),
                "onboarding_completed": getattr(data, "onboarding_completed", False),
                "marketing_agreed": getattr(data, "marketing_agreed", False),
                "sms_agreed": getattr(data, "sms_agreed", False),
            }
        return data
