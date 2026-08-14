from datetime import timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_session
from ..storage import LocalObjectStorage, ObjectStorage
from .service import SourceService


def get_object_storage() -> ObjectStorage:
    return LocalObjectStorage(get_settings().storage_root)


def get_source_service(
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> SourceService:
    settings = get_settings()
    return SourceService(
        session,
        storage,
        retention=timedelta(hours=settings.source_retention_hours),
    )
