from back.config import load_config
from back.interfaces.user_manager_protocol import UserManagerProtocol
from back.services.user_manager_json import JsonUserManager
from back.services.user_manager_sqlite import SqliteUserManager
from back.utils.logger import get_logger

logger = get_logger(__name__)

class UserManagerFactory:
    @staticmethod
    def get_user_manager() -> UserManagerProtocol:
        config = load_config()
        storage_config = config.get("storage", {})
        backend = storage_config.get("user_backend", "json").lower()
        
        logger.info(f"Initializing User Manager with backend: {backend}")

        if backend == "sqlite":
            db_path = storage_config.get("sqlite_path")
            return SqliteUserManager(db_path=db_path)
        else:
            return JsonUserManager()
