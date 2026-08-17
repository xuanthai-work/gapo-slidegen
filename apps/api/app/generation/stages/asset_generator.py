from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Protocol
from uuid import UUID

from ...config import get_settings
from ...storage.assets import detect_image_type, store_asset
from ...storage.base import ObjectStorage
from ...storage.local import LocalObjectStorage
from ..image_provider import GeneratedImageData, ImageGenerationProvider, ImageGenerationRequest
from ..provider import ProviderError
from .models import AssetPlan, GeneratedAsset
from .protocols import AssetGenerator as AssetGeneratorProtocol


class NullAssetGenerator:
    """No-op asset generator; layouts keep placeholder shapes."""

    name = "null"

    def generate(self, plan: AssetPlan) -> list[GeneratedAsset]:
        del plan
        return []


class ImageAssetGenerator:
    """Generates images for an asset plan and stores them as owner-scoped assets."""

    name = "image"

    def __init__(
        self,
        *,
        image_provider: ImageGenerationProvider,
        session_factory: object,
        storage: ObjectStorage | None = None,
        concurrency: int = 2,
    ) -> None:
        self.image_provider = image_provider
        self.session_factory = session_factory
        self.storage = storage or LocalObjectStorage(get_settings().storage_root)
        self.concurrency = max(1, concurrency)

    def generate(self, plan: AssetPlan) -> list[GeneratedAsset]:
        if not plan.requests or plan.owner_id is None:
            return []
        results: list[GeneratedAsset] = []
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {
                executor.submit(self._generate_one, plan.owner_id, request): request
                for request in plan.requests
            }
            for future in futures:
                results.append(future.result())
        return results

    def _generate_one(
        self,
        owner_id: UUID,
        request: object,
    ) -> GeneratedAsset:
        from .models import AssetRequest

        asset_request = request if isinstance(request, AssetRequest) else AssetRequest(**request)
        prompt = (asset_request.prompt or "Presentation illustration").strip()
        if not prompt:
            return GeneratedAsset(
                slot=asset_request.slot,
                warning="Empty image prompt; skipped.",
            )
        try:
            generated = self.image_provider.generate_image(
                ImageGenerationRequest(prompt=prompt, aspect_ratio="16:9")
            )
        except Exception as error:
            return GeneratedAsset(
                slot=asset_request.slot,
                warning=f"Image generation failed: {error}"[:500],
            )
        return self._store(owner_id, asset_request, generated)

    def _store(
        self,
        owner_id: UUID,
        request: object,
        generated: GeneratedImageData,
    ) -> GeneratedAsset:
        from .models import AssetRequest

        asset_request = request if isinstance(request, AssetRequest) else AssetRequest(**request)
        limit = min(get_settings().max_upload_bytes, 10 * 1024 * 1024)
        if not generated.data or len(generated.data) > limit:
            return GeneratedAsset(
                slot=asset_request.slot,
                warning="Generated image is empty or exceeds 10 MB.",
            )
        detected = detect_image_type(generated.data)
        if detected is None:
            return GeneratedAsset(
                slot=asset_request.slot,
                warning="Generated image has an unsupported format.",
            )
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[detected]
        try:
            with self.session_factory() as session:
                record = store_asset(
                    owner_id=owner_id,
                    session=session,
                    storage=self.storage,
                    filename=f"generated-{asset_request.slot.name}-{asset_request.slot.slide_index:02d}.{extension}",
                    data=generated.data,
                )
                session.commit()
                return GeneratedAsset(slot=asset_request.slot, asset_id=str(record.id))
        except Exception as error:
            return GeneratedAsset(
                slot=asset_request.slot,
                warning=f"Could not store generated image: {error}"[:500],
            )


# Re-export the protocol alias for cleaner imports.
AssetGenerator = AssetGeneratorProtocol
