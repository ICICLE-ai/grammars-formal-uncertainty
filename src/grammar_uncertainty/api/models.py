"""
Pydantic models for API request/response validation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyzeOptions(BaseModel):
    """Options for the analyze endpoint."""

    compute_uncertainty: bool = Field(
        default=True,
        description="Whether to compute uncertainty metrics",
    )
    sample_size: Optional[int] = Field(
        default=None,
        description="Number of programs for uncertainty calculation",
    )


class AnalyzeRequest(BaseModel):
    """Request body for the analyze endpoint."""

    folder_path: str = Field(
        ...,
        description="Path to the folder containing program files",
    )
    grammar: str = Field(
        default="smtlib",
        description="Grammar to use for parsing",
    )
    options: AnalyzeOptions = Field(
        default_factory=AnalyzeOptions,
        description="Analysis options",
    )


class UncertaintyMetricsResponse(BaseModel):
    """Uncertainty metrics in the response."""

    grammar_entropy: float
    perplexity: float
    shannon_entropy_by_nt: Dict[str, float]
    renyi_entropy_order2: Dict[str, float]
    kl_divergence_from_uniform: Dict[str, float]
    nsui: float
    spectral_radius: float = 0.0


class AnalyzeResponse(BaseModel):
    """Response body for the analyze endpoint."""

    success: bool
    grammar: str
    programs_parsed: int
    programs_failed: int
    total_rules: int
    unique_rules: int
    pcfg: Dict[str, Any] = Field(default_factory=dict)
    pcfg_stats: Dict[str, Any] = Field(default_factory=dict)
    uncertainty: Optional[UncertaintyMetricsResponse] = None
    errors: List[str] = Field(default_factory=list)
    analysis_time_ms: float


class GrammarInfo(BaseModel):
    """Information about a grammar handler."""

    name: str
    description: str
    file_extensions: List[str]
    is_setup: bool


class GrammarsResponse(BaseModel):
    """Response for the grammars list endpoint."""

    grammars: List[GrammarInfo]


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""

    status: str
    version: str


class SetupRequest(BaseModel):
    """Request body for the setup endpoint."""

    grammar: str = Field(
        default="smtlib",
        description="Grammar to set up",
    )
    force: bool = Field(
        default=False,
        description="Force regeneration even if files exist",
    )


class SetupResponse(BaseModel):
    """Response for the setup endpoint."""

    success: bool
    grammar: str
    message: str


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
