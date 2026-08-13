import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None = None
    roles: list[str] = Field(default_factory=list)
