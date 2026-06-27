from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from database import get_db
from models import User, Investigation
from api.deps import get_current_user
from api.auth import create_user_token

router = APIRouter(prefix="/users", tags=["users"])


class TelegramAuthRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    telegram_id: int


@router.post("/auth/telegram", response_model=TokenResponse)
async def auth_telegram(req: TelegramAuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == req.telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=req.telegram_id,
            username=req.username,
            full_name=req.full_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.username = req.username or user.username
        user.full_name = req.full_name or user.full_name
        await db.commit()

    token = create_user_token(telegram_id=user.telegram_id, user_id=user.id)
    return TokenResponse(access_token=token, user_id=user.id, telegram_id=user.telegram_id)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(
        select(func.count()).where(Investigation.user_id == current_user.id)
    )
    total = count_result.scalar() or 0
    return {
        "id": current_user.id,
        "telegram_id": current_user.telegram_id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "investigations_total": total,
        "member_since": current_user.created_at.isoformat(),
    }
