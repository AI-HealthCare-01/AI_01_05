from fastapi import APIRouter, Query
from datetime import date

# router 하나만 사용
router = APIRouter(
    prefix="/moods",
    tags=["moods"]
)

# 임시 DB (나중에 진짜 DB로 변경)
fake_moods = []


# ✅ 기분 저장
@router.post("")
def create_mood(data: dict):
    fake_moods.append(data)
    return {
        "message": "success",
        "data": data
    }


# ✅ 날짜별 조회 (달력용)
@router.get("")
def get_moods(date: date | None = Query(None)):

    # 날짜 없으면 전체
    if date is None:
        return {"message": "success","data": fake_moods}

    # 날짜 맞는 것만 반환
    result = [
        mood for mood in fake_moods
        if mood["date"] == str(date)
    ]

    return {
        "message": "success",
        "data": result
    }