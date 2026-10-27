"""Shared Pydantic schema primitives."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema with standard Pydantic configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class IDSchema(BaseSchema):
    """Schema mixin providing UUID primary key."""

    id: uuid.UUID = Field(description="Unique record identifier")


class TimestampSchema(BaseSchema):
    """Schema mixin providing creation and modification UTC timestamps."""

    created_at: datetime = Field(description="Record creation UTC timestamp")
    updated_at: datetime = Field(description="Record last modification UTC timestamp")
