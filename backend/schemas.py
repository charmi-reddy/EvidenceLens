from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClaimStatus(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ClaimResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=500)
    status: ClaimStatus
    evidence: str = Field(min_length=1, max_length=700)
    explanation: str = Field(min_length=1, max_length=700)
    confidence: Literal["low", "medium", "high"]


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_status: ClaimStatus
    claims: list[ClaimResult] = Field(min_length=1, max_length=20)
    limitations: list[str] = Field(max_length=10)

    @field_validator("limitations")
    @classmethod
    def validate_limitations(cls, items: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 500 for item in items):
            raise ValueError("Each limitation must contain 1-500 characters")
        return [item.strip() for item in items]
