# Copyright (c) 2026 Benjamin Marchand
# Licensed under the PolyForm Noncommercial License 1.0.0

import argparse
import asyncio
import logging
import os
import sys

# Ensure root directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.domain.user import User
from back.services.auth_service import AuthService
from back.services.user_manager_factory import UserManagerFactory

# Configure minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# AuthService is instantiated with a UserManager to reuse its password hashing helper.

async def list_users() -> None:
    """
    List all users in the system.
    
    Retrieves and displays all users from the user manager, showing their ID, email,
    role, and active status in a formatted table.
    
    Returns:
        None
    """
    user_manager: UserManagerProtocol = UserManagerFactory.get_user_manager()
    try:
        users = await user_manager.list_all()
        if not users:
            print("No users found.")
            return

        print(f"Found {len(users)} users:")
        print(f"{'ID':<38} | {'Email':<30} | {'Role':<10} | {'Active'}")
        print("-" * 95)
        for user in users:
            print(f"{str(user.id):<38} | {user.email:<30} | {user.role:<10} | {user.is_active}")
    except Exception as e:
        logger.error(f"Failed to list users: {e}")

async def create_user(email: str, password: str, full_name: str, role: str) -> None:
    """
    Create a new user in the system.
    
    Creates a new user with the provided credentials and information. The password is
    hashed before storage. Checks for existing users with the same email and prevents
    duplicate creation.
    
    Parameters:
        email (str): The email address for the new user
        password (str): The plaintext password (will be hashed)
        full_name (str): The full name of the user
        role (str): The role of the user (e.g., 'user', 'admin')
    
    Returns:
        None
    """
    # Get User Manager (reads from config via get_storage_config inside factory)
    user_manager: UserManagerProtocol = UserManagerFactory.get_user_manager()
    
    # Initialize AuthService
    auth_service = AuthService(user_manager=user_manager)
    
    # Check if user exists
    existing_user = await user_manager.get_by_email(email)
    if existing_user:
        logger.error(f"Error: User with email {email} already exists.")
        return

    # Hash password
    hashed_password = auth_service.get_password_hash(password)
    
    new_user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
        is_active=True
    )

    try:
        created_user = await user_manager.create(new_user)
        logger.info(f"Successfully created user: {created_user.email} (ID: {created_user.id})")
        logger.info(f"Role: {created_user.role}")
        logger.info(f"Storage: {user_manager.__class__.__name__}")
    except Exception as e:
        logger.error(f"Failed to create user: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="User Management Script")
    parser.add_argument("--list", action="store_true", help="List existing users")
    parser.add_argument("email", nargs="?", help="User email address (required for creation)")
    parser.add_argument("password", nargs="?", help="User password (required for creation)")
    parser.add_argument("--name", help="User full name", default="New User")
    parser.add_argument("--role", help="User role (user/admin)", default="user")

    args = parser.parse_args()

    if args.list:
        asyncio.run(list_users())
    else:
        if not args.email or not args.password:
            parser.error("the following arguments are required: email, password (unless --list is specified)")
        asyncio.run(create_user(args.email, args.password, args.name, args.role))
