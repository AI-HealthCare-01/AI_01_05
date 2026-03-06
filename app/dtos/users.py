from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

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


class UserInfoResponse(BaseSerializerModel):
    user_id: int
    nickname: str
    email: str | None = None
    phone_number: str
    birthday: date | None = None
    gender: Gender
    created_at: datetime
    onboarding_completed: bool = False

    @classmethod
    def model_validate(cls, obj, **kwargs):  # type: ignore[override]
        return cls(
            id=getattr(obj, "user_id", None),
            name=getattr(obj, "nickname", ""),
            email=getattr(obj, "email", None),
            phone_number=getattr(obj, "phone_number", ""),
            birthday=getattr(obj, "birthday", None),
            gender=getattr(obj, "gender", None),
            created_at=getattr(obj, "created_at", None),
            onboarding_completed=getattr(obj, "onboarding_completed", False),
        )
