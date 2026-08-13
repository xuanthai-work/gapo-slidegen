import uuid

from fastapi import APIRouter, Response, status

from app.api.errors import capability_not_implemented
from app.schemas.slide import SlideContent, SlideReorderRequest, SlideUpdate

router = APIRouter()


@router.patch("/slides/{slide_id}", response_model=SlideContent)
async def update_slide(slide_id: uuid.UUID, payload: SlideUpdate) -> SlideContent:
    del slide_id, payload
    capability_not_implemented("Slide service")


@router.post(
    "/presentations/{presentation_id}/slides/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reorder_slides(
    presentation_id: uuid.UUID, payload: SlideReorderRequest
) -> Response:
    del presentation_id, payload
    capability_not_implemented("Slide service")


@router.delete("/slides/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slide(slide_id: uuid.UUID) -> Response:
    del slide_id
    capability_not_implemented("Slide service")
