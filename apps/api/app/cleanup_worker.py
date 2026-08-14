import logging
from time import sleep

from .config import get_settings
from .database import SessionLocal
from .sources.cleanup import delete_expired_sources
from .storage import LocalObjectStorage

logger = logging.getLogger(__name__)


def process_once() -> int:
    settings = get_settings()
    storage = LocalObjectStorage(settings.storage_root)
    with SessionLocal() as session:
        try:
            deleted = delete_expired_sources(
                session,
                storage,
                limit=settings.retention_cleanup_batch_size,
            )
            session.commit()
            return deleted
        except Exception:
            session.rollback()
            raise


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            deleted = process_once()
            if deleted:
                logger.info("Deleted %s expired source record(s).", deleted)
        except Exception:
            logger.exception("Source retention cleanup failed; it will be retried.")
        sleep(settings.retention_cleanup_interval_seconds)


if __name__ == "__main__":
    main()
