"""Common response schema used across all endpoints."""

from typing import Any, Optional
from pydantic import BaseModel


class APIResponse(BaseModel):
    """Standardized API response envelope."""
    success: bool
    message: str
    data: Optional[Any] = None
