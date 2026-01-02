import asyncio
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from back.config import get_data_dir
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.models.domain.preferences import UserPreferences
from back.models.domain.user import User, UserRole
from back.utils.logger import log_warning

# Default preferences as JSON string
DEFAULT_PREFERENCES_JSON: str = '{"language":"English","theme":"dark","font_size":"medium"}'


class SqliteUserManager(UserManagerProtocol):
    """
    SQLite implementation of UserManagerProtocol.
    Stores users in a SQLite database file.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.data_dir = get_data_dir()
        self.db_path = db_path or str(Path(self.data_dir) / "users.db")
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Escape single quotes in JSON for SQL safety
            escaped_json: str = DEFAULT_PREFERENCES_JSON.replace("'", "''")
            
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "    id TEXT PRIMARY KEY,"
                "    email TEXT UNIQUE NOT NULL,"
                "    hashed_password TEXT NOT NULL,"
                "    full_name TEXT,"
                "    role TEXT NOT NULL DEFAULT 'user',"
                "    is_active INTEGER NOT NULL DEFAULT 1,"
                "    avatar_url TEXT,"
                "    preferences TEXT DEFAULT '" + escaped_json + "',"
                "    daily_portrait_count INTEGER DEFAULT 0,"
                "    last_portrait_date TEXT,"
                "    created_at TEXT,"
                "    updated_at TEXT"
                ")"
            )
            
            # Migration: Add preferences column if it doesn't exist
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'preferences' not in columns:
                cursor.execute(
                    "ALTER TABLE users "
                    "ADD COLUMN preferences TEXT DEFAULT '" + escaped_json + "'"
                )

            if 'daily_portrait_count' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_portrait_count INTEGER DEFAULT 0")
            
            if 'last_portrait_date' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN last_portrait_date TEXT")

            
            conn.commit()

    async def _run_query(self, query: str, params: tuple = (), fetch: str = "all"):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._execute_sync, query, params, fetch)

    def _execute_sync(self, query: str, params: tuple, fetch: str) -> Optional[sqlite3.Row | List[sqlite3.Row]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch == "one":
                result = cursor.fetchone()
            elif fetch == "all":
                result = cursor.fetchall()
            else:
                result = None
            conn.commit()
            return result

    def _row_to_user(self, row: Dict[str, Any]) -> User:
        from datetime import datetime

        # Parse preferences from JSON with error handling
        try:
            preferences_data: dict = json.loads(row["preferences"]) if row.get("preferences") else {}
        except (json.JSONDecodeError, TypeError) as e:
            # Log error and use defaults if preferences are malformed
            user_id: str = row.get("id", "unknown")
            log_warning(f"Failed to parse preferences for user {user_id}: {e}. Using defaults.")
            preferences_data = {}
        
        preferences: UserPreferences = UserPreferences(**preferences_data)
        
        return User(
            id=UUID(row["id"]),
            email=row["email"],
            hashed_password=row["hashed_password"],
            full_name=row["full_name"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            avatar_url=row["avatar_url"],
            preferences=preferences,
            daily_portrait_count=row["daily_portrait_count"] if "daily_portrait_count" in row.keys() and row["daily_portrait_count"] is not None else 0,
            last_portrait_date=datetime.fromisoformat(row["last_portrait_date"]) if "last_portrait_date" in row.keys() and row["last_portrait_date"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    async def get_by_email(self, email: str) -> Optional[User]:
        row = await self._run_query("SELECT * FROM users WHERE email = ?", (email,), fetch="one")
        if row:
            return self._row_to_user(row)
        return None

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        row = await self._run_query("SELECT * FROM users WHERE id = ?", (str(user_id),), fetch="one")
        if row:
            return self._row_to_user(row)
        return None

    async def create(self, user: User) -> User:
        existing = await self.get_by_email(user.email)
        if existing:
            raise ValueError(f"User with email {user.email} already exists")

        preferences_json: str = json.dumps(user.preferences.model_dump())
        
        await self._run_query(
            """
            INSERT INTO users (id, email, hashed_password, full_name, role, is_active, avatar_url, preferences, daily_portrait_count, last_portrait_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(user.id),
                user.email,
                user.hashed_password,
                user.full_name,
                user.role.value,
                1 if user.is_active else 0,
                user.avatar_url,
                preferences_json,
                user.daily_portrait_count,
                user.last_portrait_date.isoformat() if user.last_portrait_date else None,
                user.created_at.isoformat(),
                user.updated_at.isoformat()
            ),
            fetch="none"
        )
        return user

    async def update(self, user: User) -> User:
        # Optimistic check not strictly needed if we trust the caller, but good for safety
        preferences_json: str = json.dumps(user.preferences.model_dump())
        
        await self._run_query(
            """
            UPDATE users SET 
                email = ?, 
                hashed_password = ?, 
                full_name = ?, 
                role = ?, 
                is_active = ?, 
                avatar_url = ?,
                preferences = ?, 
                daily_portrait_count = ?,
                last_portrait_date = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                user.email,
                user.hashed_password,
                user.full_name,
                user.role.value,
                1 if user.is_active else 0,
                user.avatar_url,
                preferences_json,
                user.daily_portrait_count,
                user.last_portrait_date.isoformat() if user.last_portrait_date else None,
                user.updated_at.isoformat(),
                str(user.id)
            ),
            fetch="none"
        )
        return user

    async def delete(self, user_id: UUID) -> bool:
        # Check existence first or rely on rowcount? Sqlite3 wrapper here doesn't return rowcount easily structure-wise
        # Let's just execute delete
        # We can implement rowcount return if needed
        # For now, simplistic:
        existing = await self.get_by_id(user_id)
        if not existing:
            return False
            
        await self._run_query("DELETE FROM users WHERE id = ?", (str(user_id),), fetch="none")
        return True

    async def list_all(self) -> List[User]:
        rows = await self._run_query("SELECT * FROM users", (), fetch="all")
        return [self._row_to_user(row) for row in rows]
