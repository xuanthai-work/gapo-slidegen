from typing import Never

from fastapi import HTTPException, status


def capability_not_implemented(capability: str) -> Never:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{capability} is scaffolded but not implemented",
    )
