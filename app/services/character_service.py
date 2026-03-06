from fastapi import HTTPException, status

from app.models.character import UserCharacter
from app.models.users import User

# 4개 고정 캐릭터 — DB 조회 없이 상수로 관리
CHARACTERS: list[dict] = [
    {
        "character_id": 1,
        "name": "참깨",
        "description": "걱정을 먼저 알아채고 한없이 보살펴주는 친구",
        "image_url": "/static/characters/chamkkae.png",
        "personality": "다정함",
    },
    {
        "character_id": 2,
        "name": "들깨",
        "description": "하나부터 열까지 차근차근 알려주는 친구",
        "image_url": "/static/characters/deulkkae.png",
        "personality": "친절함",
    },
    {
        "character_id": 3,
        "name": "흑깨",
        "description": "밝고 긍정적이면서 웃음을 건네는 친구",
        "image_url": "/static/characters/heukkkae.png",
        "personality": "긍정적",
    },
    {
        "character_id": 4,
        "name": "통깨",
        "description": "귀엽고 공감 리액션으로 기분을 밝혀주는 친구",
        "image_url": "/static/characters/tongkkae.png",
        "personality": "공감형",
    },
]

_CHARACTER_MAP: dict[int, dict] = {c["character_id"]: c for c in CHARACTERS}


class CharacterService:
    def get_characters(self) -> list[dict]:
        return CHARACTERS

    def _get_character_or_404(self, character_id: int) -> dict:
        char = _CHARACTER_MAP.get(character_id)
        if not char:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 캐릭터입니다.")
        return char

    async def select_character(self, user: User, character_id: int) -> dict:
        char = self._get_character_or_404(character_id)
        existing = await UserCharacter.get_or_none(user_id=user.user_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 캐릭터를 선택했습니다.")
        uc = await UserCharacter.create(user_id=user.user_id, character_id=character_id)
        await User.filter(user_id=user.user_id).update(onboarding_completed=True)
        return {"character_id": character_id, "name": char["name"], "selected_at": uc.selected_at}

    async def get_my_character(self, user: User) -> dict:
        uc = await UserCharacter.get_or_none(user_id=user.user_id)
        if not uc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="선택된 캐릭터가 없습니다.")
        char = _CHARACTER_MAP.get(uc.character_id)
        name = char["name"] if char else ""
        return {"character_id": uc.character_id, "name": name, "selected_at": uc.selected_at}

    async def change_character(self, user: User, character_id: int) -> dict:
        char = self._get_character_or_404(character_id)
        uc = await UserCharacter.get_or_none(user_id=user.user_id)
        if not uc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="먼저 캐릭터를 선택해주세요.")
        await UserCharacter.filter(user_id=user.user_id).update(character_id=character_id)
        uc = await UserCharacter.get(user_id=user.user_id)
        return {"character_id": character_id, "name": char["name"], "selected_at": uc.selected_at}
