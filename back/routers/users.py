from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi_injector import Injected

from back.auth_dependencies import get_current_admin_user
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.api.auth import UserResponse, UserUpdate
from back.models.domain.user import User
from back.utils.logger import log_error

router = APIRouter(tags=["users"])


@router.get(
    "/", 
    response_model=List[UserResponse],
    summary="List all users",
    description="Retrieve a list of all registered users. Requires ADMIN privileges.",
    responses={
        200: {
            "description": "List of users",
            "content": {"application/json": {"example": [{"email": "user@example.com", "role": "user", "is_active": True}]}}
        },
        403: {"description": "Not authorized"}
    }
)
async def read_users(
    skip: int = 0, 
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    user_manager: UserManagerProtocol = Injected(UserManagerProtocol)
):
    users = await user_manager.list_all()
    # Simple pagination since list_all returns everything (for JSON/SQLite lite usage)
    return users[skip : skip + limit]

@router.put(
    "/{user_id}", 
    response_model=UserResponse,
    summary="Update a user",
    description="Update user details (email, name, role, status). Requires ADMIN privileges.",
    responses={
        200: {"description": "User updated"},
        404: {"description": "User not found"},
        403: {"description": "Not authorized"}
    }
)
async def update_user(
    user_id: UUID, 
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    user_manager: UserManagerProtocol = Injected(UserManagerProtocol)
):
    existing_user = await user_manager.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_update.email is not None and user_update.email != existing_user.email:
        users: List[User] = await user_manager.list_all()
        for user in users:
            user_item: User = user
            if user_item.email == user_update.email and user_item.id != existing_user.id:
                raise HTTPException(status_code=400, detail="Email already in use")
        existing_user.email = user_update.email
    if user_update.full_name is not None:
        existing_user.full_name = user_update.full_name
    if user_update.role is not None: # Admin can update role
        existing_user.role = user_update.role
    if user_update.is_active is not None: # Admin can update status
        existing_user.is_active = user_update.is_active
    if user_update.avatar_url is not None:
        existing_user.avatar_url = user_update.avatar_url
    
    # Password update by admin? Maybe separate logic. For now kept simple.

    updated_user = await user_manager.update(existing_user)
    return updated_user


@router.delete(
    "/{user_id}", 
    response_model=bool,
    summary="Delete a user",
    description="Permanently delete a user account. Requires ADMIN privileges.",
    responses={
        200: {"description": "User deleted"},
        404: {"description": "User not found"},
        403: {"description": "Not authorized"}
    }
)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin_user),
    user_manager: UserManagerProtocol = Injected(UserManagerProtocol)
):
    success = await user_manager.delete(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return True
