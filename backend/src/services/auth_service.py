import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password, verify_password
from src.db.models.user import User
from src.models.user import UserCreate

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def register_user(self, user_create: UserCreate) -> User:
        existing = await self._session.scalar(
            select(User).where(
                (User.username == user_create.username)
                | (User.email == user_create.email)
            )
        )
        if existing is not None:
            raise ValueError("Username or email already registered")

        user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hash_password(user_create.password),
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        logger.info("Registered new user: %s", user.username)
        return user

    async def authenticate_user(self, username: str, password: str) -> User | None:
        user = await self._session.scalar(
            select(User).where(User.username == username)
        )
        if user is None or not verify_password(password, user.hashed_password):
            return None
        return user
