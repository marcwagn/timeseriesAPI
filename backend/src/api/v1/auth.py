import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from src.core.security import create_access_token
from src.db.schema import AsyncSessionLocal
from src.models.user import Token, UserCreate, UserResponse
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


async def get_auth_service():
    async with AsyncSessionLocal() as session:
        try:
            yield AuthService(session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_create: UserCreate,
    service: AuthService = Depends(get_auth_service),
):
    try:
        user = await service.register_user(user_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
):
    user = await service.authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)
