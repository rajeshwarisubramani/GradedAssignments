from backend.config.settings import ensure_data_files
from backend.domain.exceptions import LibraryError
from backend.services import LibraryService


def get_service() -> LibraryService:
    """Create and return a ready-to-use library service instance.

    Ensures required data files exist before constructing the service.
    """
    ensure_data_files()
    return LibraryService()


def safe_call(action, *args):
    """Execute an action and convert domain exceptions into user-safe results.

    Returns a tuple where the first value indicates success.
    """
    try:
        return True, action(*args)
    except LibraryError as exc:
        return False, str(exc)

