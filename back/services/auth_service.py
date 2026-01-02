import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from back.config import config
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.domain.user import User

# Config
auth_config = config.get_auth_config()
SECRET_KEY = auth_config.get("secret_key", "CHANGEME_SECRET_KEY_12345")
ALGORITHM = auth_config.get("algorithm", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = auth_config.get("expire_minutes", 30)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


from injector import inject


class AuthService:
    @inject
    def __init__(self, user_manager: UserManagerProtocol):
        self.user_manager = user_manager

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.user_manager.get_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_password_reset_token(self, email: str) -> str:
        """Generate a short-lived token for password reset."""
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode = {"sub": email, "exp": expires, "scope": "password_reset"}
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def create_magic_link_token(self, email: str) -> str:
        """Generate a short-lived token for magic login."""
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)
        to_encode = {"sub": email, "exp": expires, "scope": "magic_login"}
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str, expected_scope: str) -> Optional[str]:
        """Verify token and return the email (subject) if valid.
        
        Uses constant-time comparison for scope to prevent timing attacks.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            scope: str = payload.get("scope")
            # Use constant-time comparison to prevent timing attacks
            if email is None or not secrets.compare_digest(scope or "", expected_scope):
                return None
            return email
        except JWTError:
            return None

# Helper for dependency injection (requires initialized global service)
# This will be set up in dependencies.py
