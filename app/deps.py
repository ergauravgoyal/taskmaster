from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from app.db import dependency_connection
from app.security import decode_token

bearer = HTTPBearer()

async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    conn=Depends(dependency_connection),
) -> tuple[int, object]:
    try:
        user_id, token_id = decode_token(credentials.credentials)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    user = await conn.fetchrow(
        """
        SELECT u.id, u.email, u.name, u.created_at
        FROM users u JOIN sessions s ON s.user_id=u.id
        WHERE u.id=$1 AND s.token_id=$2 AND s.revoked_at IS NULL AND s.expires_at > now()
        """,
        user_id, token_id,
    )
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user_id, user

async def require_project_member(project_id: int, user=Depends(current_user)):
    user_id, profile = user
    async with connection() as conn:
        member = await conn.fetchval(
            "SELECT 1 FROM project_members WHERE project_id=$1 AND user_id=$2",
            project_id, user_id,
        )
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Project membership required")
    return user_id, profile
