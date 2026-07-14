"""
models.py

Data contracts for the Automated Copywriting & Tone Transformer.

- CopyRequest: what the user/CLI provides for one piece of copy.
- CopyResponse: the structured shape we expect the model to return.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional


class CopyRequest(BaseModel):
    product_name: str
    description: str
    platform: Literal["linkedin", "instagram", "email"]
    tone: str = "professional"          # e.g. "witty", "urgent", "friendly"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=400, ge=50, le=2000)


class CopyResponse(BaseModel):
    platform: str
    headline: str
    body: str
    hashtags: Optional[list[str]] = None
