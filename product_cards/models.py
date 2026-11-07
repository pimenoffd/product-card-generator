from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    manufacturer: str | None = None
    specs: dict[str, str | None] = Field(default_factory=dict)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Укажите название товара")
        return value


class GeneratedCopy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    seo_title: str
    seo_description: str
    search_queries: list[str]
    commercial_block: str


class TokenUsage(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)


class GenerationResponse(BaseModel):
    content: GeneratedCopy
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)


class GenerationMetadata(BaseModel):
    generated_at: datetime
    duration_seconds: float
    attempts: int
    models: list[str]
    prompt_version: str
    prompt_hash: str
    usage: TokenUsage


class ProductCard(GeneratedCopy):
    specs: dict[str, str | None]
    missing_fields: list[str]
    warnings: list[str]
    status: Literal["valid", "needs_review"]
    # Older saved cards have no metadata.
    metadata: GenerationMetadata | None = None
