from typing import Annotated

from fastapi import Depends
from tortoise.transactions import in_transaction

from app.dtos.users import UserUpdateRequest
from app.models.character import UserCharacter
from app.models.user_medication import UserMedication
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService
from app.utils.common import normalize_phone_number


class UserManageService:
    def __init__(self):
        self.repo = UserRepository()
        self.auth_service: Annotated[AuthService, Depends(AuthService)]

    async def update_user(self, user: User, data: UserUpdateRequest) -> User:
        if data.phone_number:
            normalized_phone_number = normalize_phone_number(data.phone_number)
            await self.auth_service.check_phone_number_exists(normalized_phone_number)
            data.phone_number = normalized_phone_number
        async with in_transaction():
            await self.repo.update_instance(user=user, data=data.model_dump(exclude_none=True))
            await user.refresh_from_db()
        return user

    async def delete_user(self, user: User) -> None:
        """사용자 계정 및 관련 데이터 삭제.

        삭제 순서: user_medications → user_characters → users
        user_medications.medicine FK가 RESTRICT이므로 명시적 순서 필요.
        """
        async with in_transaction():
            await UserMedication.filter(user_id=user.user_id).delete()
            await UserCharacter.filter(user_id=user.user_id).delete()
            await user.delete()
