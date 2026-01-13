from fastapi import APIRouter, Depends, HTTPException
from fastapi_injector import Injected

from back.auth_dependencies import get_current_active_user
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.api.auth import ChangePasswordRequest, UserResponse
from back.models.domain.preferences import UserPreferences
from back.models.domain.user import User
from back.services.auth_service import AuthService
from back.utils.logger import log_debug, log_error
from back.utils.password_validator import validate_password_strength

router = APIRouter(tags=["user"])

@router.post(
    "/change-password",
    summary="Change Password",
    description="Change the current user's password.",
    responses={
        200: {"description": "Password updated successfully"},
        400: {"description": "Incorrect current password"}
    }
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Injected(AuthService),
    user_manager: UserManagerProtocol = Injected(UserManagerProtocol)
):
    # Verify current password
    if not auth_service.verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # Validate new password strength
    is_valid, errors = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=", ".join(errors))
    
    # Hash new password and update user
    hashed_password: str = auth_service.get_password_hash(request.new_password)
    updated_user: User = current_user.model_copy(update={"hashed_password": hashed_password})
    
    await user_manager.update(updated_user)
    return {"message": "Password updated successfully"}

@router.get(
    "/me", 
    response_model=UserResponse,
    summary="Get Current User",
    description="Retrieve the profile of the currently authenticated user.",
    responses={
        200: {
            "description": "User Profile",
            "content": {"application/json": {"example": {"email": "me@example.com", "full_name": "Myself", "role": "user", "is_active": True}}}
        }
    }
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    return current_user

@router.get(
    "/preference", 
    response_model=UserPreferences,
    summary="Get User Preferences",
    description="Retrieve the current user's preferences.",
    responses={
        200: {
            "description": "Current Preferences",
            "content": {"application/json": {"example": {"language": "English", "theme": "dark"}}}
        }
    }
)
async def get_preferences(
    current_user: User = Depends(get_current_active_user)
) -> UserPreferences:
    """
    ### Get User Preferences
    **Description:** Retrieve the current user's preferences.
    **Returns:**
    - `UserPreferences`: The current user preferences.

    **Response:**
    ```json
    {
        "language": "English",
        "theme": "dark"
    }
    ```
    """
    log_debug("Endpoint call: GET /user/preference")
    return current_user.preferences

@router.put(
    "/preference", 
    response_model=UserPreferences,
    summary="Update User Preferences",
    description="Update the current user's preferences.",
    responses={
        200: {
            "description": "Updated Preferences",
            "content": {"application/json": {"example": {"language": "French", "theme": "light"}}}
        }
    }
)
async def update_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_active_user),
    user_manager: UserManagerProtocol = Injected(UserManagerProtocol)
) -> UserPreferences:
    """
    ### Update User Preferences
    **Description:** Update the current user's preferences.
    **Parameters:**
    - `preferences` (UserPreferences): The new preferences to save.
    **Returns:**
    - `UserPreferences`: The updated user preferences.

    **Request Body:**
    ```json
    {
        "language": "French",
        "theme": "light"
    }
    ```

    **Response:**
    ```json
    {
        "language": "French",
        "theme": "light"
    }
    ```
    """
    log_debug("Endpoint call: PUT /user/preference", preferences=preferences.model_dump())
    
    # Update user preferences using Pydantic's model_copy
    updated_user: User = current_user.model_copy(update={"preferences": preferences})
    
    try:
        await user_manager.update(updated_user)
        return preferences
    except Exception as e:
        log_error(f"Failed to update preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")
