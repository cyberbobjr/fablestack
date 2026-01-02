from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_injector import Injected

from back.config import config
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.api.auth import (ForgotPasswordRequest, MagicLoginRequest,
                                  ResetPasswordRequest, Token, UserCreate,
                                  UserResponse)
from back.models.domain.user import User
from back.services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES, AuthService
from back.services.email_service import EmailService
from back.utils.password_validator import validate_password_strength

router = APIRouter(tags=["auth"])
# config = load_config() # Removed
PUBLIC_URL = config.get_app_config().get("public_url", "http://localhost:5173")

# Dependencies
# Dependencies removed - using Injected directly

@router.post(
    "/forgot-password",
    summary="Request Password Reset",
    description="Initiates the password reset flow. Sends an email with a reset token if the email exists.",
    responses={
        200: {"description": "Email sent (if account exists)"}
    }
)
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: AuthService = Injected(AuthService),
    email_service: EmailService = Injected(EmailService)
):
    # Always return 200 even if email doesn't exist to prevent enumeration
    # But for this functionality we need to check existence to generate token
    user = await auth_service.user_manager.get_by_email(request.email)
    if user:
        token = auth_service.create_password_reset_token(request.email)
        link = f"{PUBLIC_URL}/reset-password?token={token}"
        await email_service.send_password_reset_email(request.email, link)
    
    return {"message": "If the email exists, a reset link has been sent."}

@router.post(
    "/reset-password",
    summary="Reset Password",
    description="Resets the user's password using a valid reset token.",
    responses={
        200: {"description": "Password successfully reset"},
        400: {"description": "Invalid or expired token"}
    }
)
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthService = Injected(AuthService)
):
    # Validate password strength
    is_valid, errors = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=", ".join(errors))
    
    email = auth_service.verify_token(request.token, "password_reset")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    user = await auth_service.user_manager.get_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
        
    hashed_password: str = auth_service.get_password_hash(request.new_password)
    
    # Update user object using Pydantic's model_copy
    updated_user: User = user.model_copy(update={"hashed_password": hashed_password})
    
    await auth_service.user_manager.update(updated_user)
    
    return {"message": "Password has been reset successfully"}

@router.post(
    "/magic-login-request",
    summary="Request Magic Link",
    description="Requests a magic login link to be sent by email.",
    responses={
        200: {"description": "Magic link sent"}
    }
)
async def request_magic_link(
    request: MagicLoginRequest,
    auth_service: AuthService = Injected(AuthService),
    email_service: EmailService = Injected(EmailService)
):
    user = await auth_service.user_manager.get_by_email(request.email)
    if user:
        token = auth_service.create_magic_link_token(request.email)
        link = f"{PUBLIC_URL}/magic-login?token={token}"
        await email_service.send_magic_login_email(request.email, link)
        
    return {"message": "If the email exists, a magic link has been sent."}

@router.post(
    "/magic-login-verify",
    response_model=Token,
    summary="Verify Magic Link",
    description="Exchanges a magic link token for a long-lived access token.",
    responses={
        200: {"description": "Login successful"},
        400: {"description": "Invalid token"}
    }
)
async def verify_magic_link(
    token: str = Body(..., embed=True),
    auth_service: AuthService = Injected(AuthService)
):
    email = auth_service.verify_token(token, "magic_login")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    user = await auth_service.user_manager.get_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post(
    "/token", 
    response_model=Token,
    summary="Login",
    description="Authenticates a user using multipart/form-data (username/password) and returns a JWT access token.",
    responses={
        200: {
            "description": "Successful Login",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        401: {"description": "Incorrect username or password"}
    }
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Injected(AuthService)
):
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post(
    "/register", 
    response_model=UserResponse,
    summary="Register a new user",
    description="Creates a new user account with the provided email, password, and full name.",
    responses={
        200: {
            "description": "User successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "email": "frodo@shire.com",
                        "full_name": "Frodo Baggins",
                        "avatar_url": None,
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "role": "user",
                        "is_active": True,
                        "created_at": "2023-01-01T12:00:00"
                    }
                }
            }
        },
        400: {"description": "Email already registered"}
    }
)
async def register_user(
    user_create: UserCreate,
    user_manager: UserManagerProtocol = Injected(UserManagerProtocol),
    auth_service: AuthService = Injected(AuthService)
):
    # Validate password strength
    is_valid, errors = validate_password_strength(user_create.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=", ".join(errors))
    
    hashed_password = auth_service.get_password_hash(user_create.password)
    
    new_user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        avatar_url=user_create.avatar_url,
        role="user" 
    )
    
    try:
        created_user = await user_manager.create(new_user)
        return created_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
