from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.mood_dto import MoodCreateRequest, MoodListResponse, MoodResponse, MoodUpdateRequest
from app.models.users import User
from app.services.mood_service import MoodService

router = APIRouter(prefix="/moods", tags=["moods"])


@router.post("", response_model=MoodResponse, status_code=status.HTTP_201_CREATED)
async def create_mood(
    body: MoodCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MoodService, Depends(MoodService)],
) -> Response:
    mood = await service.create_mood(user, body.mood_score, body.note)
    return Response(MoodResponse.model_validate(mood).model_dump(), status_code=status.HTTP_201_CREATED)


@router.get("", response_model=MoodListResponse, status_code=status.HTTP_200_OK)
async def get_moods(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MoodService, Depends(MoodService)],
) -> Response:
    moods = await service.get_moods(user)
    return Response({"moods": [MoodResponse.model_validate(m).model_dump() for m in moods]})


@router.patch("/{mood_id}", response_model=MoodResponse, status_code=status.HTTP_200_OK)
async def update_mood(
    mood_id: int,
    body: MoodUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MoodService, Depends(MoodService)],
) -> Response:
    mood = await service.update_mood(user, mood_id, body.mood_score, body.note)
    return Response(MoodResponse.model_validate(mood).model_dump())
