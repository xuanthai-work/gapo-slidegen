from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import get_current_user
from .config import get_settings
from .database import get_session
from .generation.factory import build_image_provider
from .generation.image_provider import ImageGenerationProvider, ImageGenerationRequest
from .generation.provider import ProviderConfigurationError, ProviderError
from .models import AssetRecord, User
from .storage import LocalObjectStorage, ObjectStorage
from .storage.assets import ALLOWED_IMAGE_TYPES, detect_image_type, store_asset

router = APIRouter(prefix="/v1/assets", tags=["assets"])


class AssetView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size: int


class GenerateImageInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=2_000)
    aspect_ratio: Literal["1:1", "3:4", "4:3", "9:16", "16:9"] = "16:9"

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if not prompt:
            raise ValueError("Image prompt cannot be empty.")
        return prompt


def get_asset_storage() -> ObjectStorage:
    return LocalObjectStorage(get_settings().storage_root)


def get_image_provider() -> ImageGenerationProvider:
    try:
        return build_image_provider()
    except ProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.post("", response_model=AssetView, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(get_asset_storage)],
    file: UploadFile = File(...),
) -> AssetRecord:
    settings = get_settings()
    limit = min(settings.max_upload_bytes, 10 * 1024 * 1024)
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Image exceeds 10 MB.")
    if detect_image_type(data) not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PNG, JPEG, and WebP images are supported.",
        )
    return store_asset(
        owner_id=user.id,
        session=session,
        storage=storage,
        filename=file.filename or "image",
        data=data,
    )


@router.post("/generate", response_model=AssetView, status_code=status.HTTP_201_CREATED)
def generate_asset(
    payload: GenerateImageInput,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(get_asset_storage)],
    provider: Annotated[ImageGenerationProvider, Depends(get_image_provider)],
) -> AssetRecord:
    try:
        generated = provider.generate_image(
            ImageGenerationRequest(prompt=payload.prompt, aspect_ratio=payload.aspect_ratio)
        )
        limit = min(get_settings().max_upload_bytes, 10 * 1024 * 1024)
        if not generated.data or len(generated.data) > limit:
            raise ProviderError("The generated image is empty or exceeds 10 MB.")
        detected_type = detect_image_type(generated.data)
        if detected_type not in ALLOWED_IMAGE_TYPES:
            raise ProviderError("The image provider returned an unsupported image format.")
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[detected_type]
        return store_asset(
            owner_id=user.id,
            session=session,
            storage=storage,
            filename=f"generated-{uuid4().hex[:12]}.{extension}",
            data=generated.data,
        )
    except ProviderConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except ProviderError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.get("/{asset_id}/content")
def get_asset_content(
    asset_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(get_asset_storage)],
) -> Response:
    record = session.scalar(
        select(AssetRecord).where(AssetRecord.id == asset_id, AssetRecord.owner_id == user.id)
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return Response(
        storage.get(record.storage_key),
        media_type=record.content_type,
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(get_asset_storage)],
) -> None:
    record = session.scalar(
        select(AssetRecord).where(AssetRecord.id == asset_id, AssetRecord.owner_id == user.id)
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    storage.delete(record.storage_key)
    session.delete(record)
    session.flush()
