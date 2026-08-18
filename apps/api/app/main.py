from typing import Literal

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from .config import get_settings
from .auth import get_current_user, router as auth_router
from .assets import router as assets_router
from .ingestion import InvalidDocumentError, SourceDocument, UnsupportedDocumentError, extract_document
from .generation import router as generation_router
from .models import User
from .sources import router as sources_router


class _DisableSseCompressionMiddleware(BaseHTTPMiddleware):
    """Strip compression headers from SSE streams so events flush immediately.

    Gzip and other compression schemes buffer the entire response before
    sending, which breaks real-time Server-Sent Events. This middleware
    removes any Content-Encoding applied by upstream middleware/proxies for
    responses whose Content-Type starts with ``text/event-stream``.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            for header in ("content-encoding", "content-length"):
                if header in response.headers:
                    del response.headers[header]
        return response


app = FastAPI(title="Gapo SlideGen API", version="0.1.0")

# Development-only CORS so the browser can connect to SSE directly when needed.
# In production this should be restricted to the actual web origin.
settings = get_settings()
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Make sure SSE responses are never compressed, regardless of middleware/proxy.
app.add_middleware(_DisableSseCompressionMiddleware)

app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(sources_router)
app.include_router(generation_router)


class TextInput(BaseModel):
    kind: Literal["prompt", "manuscript"]
    title: str = Field(default="Untitled source", min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=500_000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/ingestion/text", response_model=SourceDocument)
def ingest_text(payload: TextInput, _: User = Depends(get_current_user)) -> SourceDocument:
    cleaned = payload.text.replace("\x00", "").strip()
    return SourceDocument(
        kind=payload.kind,
        title=payload.title.strip(),
        text=cleaned,
        sections=[{"index": 0, "title": payload.title.strip(), "text": cleaned}],
    )


@app.post("/v1/ingestion/files", response_model=SourceDocument)
async def ingest_file(
    file: UploadFile = File(...), _: User = Depends(get_current_user)
) -> SourceDocument:
    settings = get_settings()
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes} byte limit.",
        )
    try:
        return extract_document(file.filename or "upload", file.content_type, data)
    except UnsupportedDocumentError as error:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(error)) from error
    except InvalidDocumentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
