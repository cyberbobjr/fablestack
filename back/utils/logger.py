# Logger JSON (Grafana/Loki‑friendly) - Migration vers système de logging standard

from datetime import datetime, timezone

from ..config import get_logger

# Logger pour ce module
logger = get_logger(__name__)

def log_debug(message: str, **kwargs):
    """
    ### log_debug
    **Description :** Écrit un message de log JSON sur la sortie standard et/ou dans un fichier si DEBUG est à true ou LOG_FILE défini.
    **Paramètres :**
    - `message` (str) : Message à logger.
    - `kwargs` (dict) : Informations additionnelles à inclure dans le log.
    **Retour :** None
    **Raises :** ValueError si des attributs réservés sont passés dans kwargs.
    """
    # Prévenir le conflit sur les attributs réservés dans kwargs
    reserved_attrs = {'message', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                     'filename', 'module', 'lineno', 'funcName', 'created', 
                     'msecs', 'relativeCreated', 'thread', 'threadName', 
                     'processName', 'process', 'name'}
    
    # Clean kwargs to avoid conflicts
    cleaned_kwargs = {}
    for k, v in kwargs.items():
        if k in reserved_attrs:
            cleaned_kwargs[f"_{k}"] = v
        else:
            cleaned_kwargs[k] = v

    try:
        # Utiliser le système de logging standard avec format JSON
        # Ne pas mettre 'message' ou 'level' dans extra pour éviter les conflits
        extra_data = {
            "log_timestamp": datetime.now(timezone.utc).isoformat(),
            "log_level": "DEBUG",
            **cleaned_kwargs
        }

        # Log via le logger standard Python
        logger.debug(message, extra=extra_data)

    except Exception as e:
        # Log minimal sur erreur de log (pas pour les erreurs de validation)
        print(f"[LOGGING ERROR] {e}")
        import traceback
        print(traceback.format_exc())

def log_info(message: str, **kwargs):
    """
    ### log_info
    **Description :** Log un message d'information.
    **Paramètres :**
    - `message` (str) : Message à logger.
    - `kwargs` (dict) : Informations additionnelles.
    """
    try:
        # Prevent conflicts with reserved attributes
        reserved_attrs = {'message', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'name'}
        
        cleaned_kwargs = {}
        for k, v in kwargs.items():
            if k in reserved_attrs:
                cleaned_kwargs[f"_{k}"] = v
            else:
                cleaned_kwargs[k] = v

        extra_data = {
            "log_timestamp": datetime.now(timezone.utc).isoformat(),
            "log_level": "INFO",
            **cleaned_kwargs
        }
        logger.info(message, extra=extra_data)
    except Exception as e:
        print(f"[LOGGING ERROR] {e}")

def log_warning(message: str, **kwargs):
    """
    ### log_warning
    **Description :** Log un message d'avertissement.
    **Paramètres :**
    - `message` (str) : Message à logger.
    - `kwargs` (dict) : Informations additionnelles.
    """
    try:
        reserved_attrs = {'name', 'message', 'msg', 'args', 'levelname', 'levelno'}
        cleaned_kwargs = {f"_{k}" if k in reserved_attrs else k: v for k, v in kwargs.items()}

        extra_data = {
            "log_timestamp": datetime.now(timezone.utc).isoformat(),
            "log_level": "WARNING",
            **cleaned_kwargs
        }
        logger.warning(message, extra=extra_data)
    except Exception as e:
        print(f"[LOGGING ERROR] {e}")

def log_error(message: str, **kwargs):
    """
    ### log_error
    **Description :** Log un message d'erreur. Inclus automatiquement la stacktrace.
    **Paramètres :**
    - `message` (str) : Message à logger.
    - `kwargs` (dict) : Informations additionnelles.
    """
    try:
        reserved_attrs = {'name', 'message', 'msg', 'args', 'levelname', 'levelno'}
        cleaned_kwargs = {f"_{k}" if k in reserved_attrs else k: v for k, v in kwargs.items()}

        extra_data = {
            "log_timestamp": datetime.now(timezone.utc).isoformat(),
            "log_level": "ERROR",
            **cleaned_kwargs
        }
        # Force exc_info=True to always log stacktrace for errors
        logger.error(message, extra=extra_data, exc_info=True)
    except Exception as e:
        print(f"[LOGGING ERROR] {e}")

def log_critical(message: str, **kwargs):
    """
    ### log_critical
    **Description :** Log un message critique. Inclus automatiquement la stacktrace.
    **Paramètres :**
    - `message` (str) : Message à logger.
    - `kwargs` (dict) : Informations additionnelles.
    """
    try:
        reserved_attrs = {'name', 'message', 'msg', 'args', 'levelname', 'levelno'}
        cleaned_kwargs = {f"_{k}" if k in reserved_attrs else k: v for k, v in kwargs.items()}

        extra_data = {
            "log_timestamp": datetime.now(timezone.utc).isoformat(),
            "log_level": "CRITICAL",
            **cleaned_kwargs
        }
        # Force exc_info=True to always log stacktrace for critical errors
        logger.critical(message, extra=extra_data, exc_info=True)
    except Exception as e:
        print(f"[LOGGING ERROR] {e}")
