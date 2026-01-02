import os
import shutil
from logging import basicConfig
from pathlib import Path
from uuid import uuid4

import logfire
import pytest
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)
TEST_DATA_DIR = os.path.join(BASE_DIR, 'gamedata')
PROD_DATA_DIR = os.path.join(BASE_DIR, '..', 'gamedata')

# Set the environment variable for the application to use the test data directory
os.environ["DATA_DIR"] = TEST_DATA_DIR

# -----------------------------------------------------------------------------
# CRITICAL: Ensure minimal test data exists BEFORE any imports that might
# initialize managers (like StatsManager) at module level.
# -----------------------------------------------------------------------------
os.makedirs(TEST_DATA_DIR, exist_ok=True)
for filename in ['equipment.yaml', 'skills.yaml', 'races_and_cultures.yaml', 'stats.yaml']:
    src = os.path.join(PROD_DATA_DIR, filename)
    dst = os.path.join(TEST_DATA_DIR, filename)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy2(src, dst)
# -----------------------------------------------------------------------------

# Load environment variables (including LOGFIRE_API_KEY)
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

# Map LOGFIRE_API_KEY to LOGFIRE_TOKEN if needed
if os.getenv("LOGFIRE_API_KEY") and not os.getenv("LOGFIRE_TOKEN"):
    os.environ["LOGFIRE_TOKEN"] = os.getenv("LOGFIRE_API_KEY")

# Verify token is available
if not os.getenv("LOGFIRE_TOKEN"):
    print(f"WARNING: LOGFIRE_TOKEN not set after loading from {project_root / '.env'} - logs will not be sent to Logfire cloud")
else:
    print(f"INFO: Logfire configured with token (first 10 chars): {os.getenv('LOGFIRE_TOKEN')[:10]}...")

# Configure Logfire immediately to catch all agent creations
def scrubbing_callback(m: logfire.ScrubMatch):
    return m.value

logfire.configure(
    send_to_logfire=os.getenv("LOGFIRE_TOKEN") is not None,
    environment='test',
    scrubbing=logfire.ScrubbingOptions(callback=scrubbing_callback)
)
logfire.instrument_pydantic_ai()

# Force Logfire handler on root logger
import logging

root_logger = logging.getLogger()
logfire_handler = logfire.LogfireLoggingHandler()
root_logger.addHandler(logfire_handler)
root_logger.setLevel(logging.DEBUG)

# Patch back.config.Config._setup_logging to NOT remove our handler
from back.config import Config

original_setup_logging = Config._setup_logging

def patched_setup_logging(self):
    # Run original setup
    original_setup_logging(self)
    # Re-add Logfire handler if it was removed
    root = logging.getLogger()
    if logfire_handler not in root.handlers:
        root.addHandler(logfire_handler)

Config._setup_logging = patched_setup_logging

@pytest.fixture(autouse=True)
def clean_test_data_dir():
    """
    Automatically clean tests/gamedata/ before each test and ensure it exists.
    This keeps tests isolated from previous runs and production data.
    """
    # Remove existing directory contents
    if os.path.isdir(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    
    # Create necessary subdirectories that the app expects
    os.makedirs(os.path.join(TEST_DATA_DIR, 'sessions'), exist_ok=True)
    os.makedirs(os.path.join(TEST_DATA_DIR, 'characters'), exist_ok=True)
    
    # Copy scenarios from production to test data
    prod_scenarios_dir = os.path.join(PROD_DATA_DIR, 'scenarios')
    test_scenarios_dir = os.path.join(TEST_DATA_DIR, 'scenarios')
    if os.path.isdir(prod_scenarios_dir):
        shutil.copytree(prod_scenarios_dir, test_scenarios_dir)
    else:
        os.makedirs(test_scenarios_dir, exist_ok=True)

    # Copy static data files (equipment.yaml, skills.yaml, races_and_cultures.yaml)
    for filename in ['equipment.yaml', 'skills.yaml', 'races_and_cultures.yaml', 'stats.yaml']:
        src = os.path.join(PROD_DATA_DIR, filename)
        dst = os.path.join(TEST_DATA_DIR, filename)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    
    yield
    
    # Clean up after as well
    if os.path.isdir(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
        os.makedirs(TEST_DATA_DIR, exist_ok=True)

import pytest_asyncio


@pytest_asyncio.fixture
async def async_client():
    from httpx import ASGITransport, AsyncClient

    from back.app import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def user_token(async_client):
    email = "fixture_user@example.com"
    pwd = "StrongPassword123!"

    # Register user via API for integration test realism
    await async_client.post("/api/auth/register", json={
        "email": email,
        "password": pwd,
        "full_name": "Fixture User"
    })
    
    # Login
    response = await async_client.post("/api/auth/token", data={"username": email, "password": pwd})
    return response.json()["access_token"]

@pytest_asyncio.fixture
async def admin_token(async_client):
    from back.models.domain.user import User, UserRole
    from back.services.auth_service import AuthService
    from back.services.user_manager_factory import UserManagerFactory

    # We need to manually create an admin because register endpoint only creates users
    user_manager = UserManagerFactory.get_user_manager()
    auth_service = AuthService(user_manager)
    
    email = "fixture_admin@example.com"
    pwd = "StrongPassword123!"
    hashed = auth_service.get_password_hash(pwd)
    
    admin = User(
        email=email,
        hashed_password=hashed,
        full_name="Fixture Admin",
        role=UserRole.ADMIN
    )
    
    # Check if exists (idempotency)
    existing = await user_manager.get_by_email(email)
    if not existing:
        await user_manager.create(admin)
    else:
        # Ensure role is admin (critical for tests)
        if existing.role != UserRole.ADMIN:
            existing.role = UserRole.ADMIN
            await user_manager.update(existing)
    
    # Login
    response = await async_client.post("/api/auth/token", data={"username": email, "password": pwd})
    return response.json()["access_token"]
