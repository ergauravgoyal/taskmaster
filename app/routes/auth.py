from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import asyncpg
from app.db import connection
from app.deps import current_user
from app.config import settings
from app.models import LoginRequest, ProfileUpdate, RegisterRequest, TokenResponse, UserResponse
from app.security import create_token, decode_token, hash_password, token_hash, token_id, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer = HTTPBearer()

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: RegisterRequest):
    async with connection() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO users(email,password_hash,name) VALUES($1,$2,$3) RETURNING id,email,name,created_at",
                payload.email, hash_password(payload.password), payload.name,
            )
        except asyncpg.UniqueViolationError as exc:
            raise HTTPException(409, "Email is already registered") from exc
    return dict(row)

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    async with connection() as conn:
        row = await conn.fetchrow("SELECT id,password_hash FROM users WHERE email=$1", payload.email)
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    session_id = token_id()
    token = create_token(row["id"], session_id)
    async with connection() as conn:
        await conn.execute(
            "INSERT INTO sessions(user_id,token_id,token_hash,expires_at) VALUES($1,$2,$3,now()+$4 * interval '1 minute')",
            row["id"], session_id, token_hash(token), settings.access_token_minutes,
        )
    return TokenResponse(access_token=token)

@router.get("/me", response_model=UserResponse)
async def me(user=Depends(current_user)):
    return dict(user[1])

@router.patch("/me", response_model=UserResponse)
async def update_me(payload: ProfileUpdate, user=Depends(current_user)):
    user_id = user[0]
    async with connection() as conn:
        row = await conn.fetchrow(
            "UPDATE users SET name=$2, updated_at=now() WHERE id=$1 RETURNING id,email,name,created_at",
            user_id, payload.name,
        )
    return dict(row)

@router.post("/logout", status_code=204)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer), user=Depends(current_user)):
    _, session_id = decode_token(credentials.credentials)
    async with connection() as conn:
        await conn.execute(
            "UPDATE sessions SET revoked_at=now() WHERE user_id=$1 AND token_id=$2",
            user[0], session_id,
        )
