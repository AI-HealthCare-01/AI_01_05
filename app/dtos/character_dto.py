from datetime import datetime

from pydantic import BaseModel


class CharacterItem(BaseModel):
    character_id: int
    name: str
    description: str
    image_url: str
    personality: str | None = None


class CharacterListResponse(BaseModel):
    characters: list[CharacterItem]


class CharacterSelectRequest(BaseModel):
    character_id: int


class CharacterSelectResponse(BaseModel):
    character_id: int
    name: str
    selected_at: datetime
