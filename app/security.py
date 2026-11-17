from datetime import datetime, timedelta, timezone
import hashlib
import uuid
import jwt
from pwdlib import PasswordHash
from app.config import settings

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_token(user_id: int, token_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "jti": token_id, "exp": expires}, settings.jwt_secret, algorithm="HS256")

def decode_token(token: str) -> tuple[int, str]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    return int(payload["sub"]), str(payload["jti"])

def token_id() -> str:
    return str(uuid.uuid4())

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
