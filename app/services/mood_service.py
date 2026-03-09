from fastapi import HTTPException, status

from app.models.mood import Mood
from app.models.users import User


class MoodService:
    async def create_mood(self, user: User, mood_score: int, note: str | None) -> Mood:
        return await Mood.create(user_id=user.user_id, mood_score=mood_score, note=note)

    async def get_moods(self, user: User) -> list[Mood]:
        return await Mood.filter(user_id=user.user_id).order_by("-created_at")

    async def update_mood(self, user: User, mood_id: int, mood_score: int | None, note: str | None) -> Mood:
        mood = await Mood.get_or_none(mood_id=mood_id, user_id=user.user_id)
        if not mood:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="기분 기록을 찾을 수 없습니다.")
        update: dict = {}
        if mood_score is not None:
            update["mood_score"] = mood_score
        if note is not None:
            update["note"] = note
        if update:
            await Mood.filter(mood_id=mood_id).update(**update)
            await mood.refresh_from_db()
        return mood
