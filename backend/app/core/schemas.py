"""Shared base for request bodies: unknown fields are rejected, not silently ignored."""

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")
