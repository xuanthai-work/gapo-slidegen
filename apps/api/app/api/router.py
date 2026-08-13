from fastapi import APIRouter

from app.api.routes import auth, generation, outlines, presentations, slides

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(presentations.router, prefix="/presentations", tags=["presentations"])
api_router.include_router(outlines.router, prefix="/presentations", tags=["outlines"])
api_router.include_router(
    generation.presentation_router,
    prefix="/presentations",
    tags=["generation"],
)
api_router.include_router(generation.job_router, prefix="/generation-jobs", tags=["generation"])
api_router.include_router(slides.router, tags=["slides"])
