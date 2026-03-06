from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.character_dto import (
    CharacterListResponse,
    CharacterSelectRequest,
    CharacterSelectResponse,
)
from app.models.users import User
from app.services.character_service import CharacterService

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("", response_model=CharacterListResponse, status_code=status.HTTP_200_OK)
async def get_characters(
    _user: Annotated[User, Depends(get_request_user)],
    service: Annotated[CharacterService, Depends(CharacterService)],
) -> Response:
    return Response({"characters": service.get_characters()})


@router.post("/me", response_model=CharacterSelectResponse, status_code=status.HTTP_201_CREATED)
async def select_character(
    body: CharacterSelectRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[CharacterService, Depends(CharacterService)],
) -> Response:
    result = await service.select_character(user, body.character_id)
    return Response(result, status_code=status.HTTP_201_CREATED)


@router.get("/me", response_model=CharacterSelectResponse, status_code=status.HTTP_200_OK)
async def get_my_character(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[CharacterService, Depends(CharacterService)],
) -> Response:
    result = await service.get_my_character(user)
    return Response(result)


@router.patch("/me", response_model=CharacterSelectResponse, status_code=status.HTTP_200_OK)
async def change_character(
    body: CharacterSelectRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[CharacterService, Depends(CharacterService)],
) -> Response:
    result = await service.change_character(user, body.character_id)
    return Response(result)
