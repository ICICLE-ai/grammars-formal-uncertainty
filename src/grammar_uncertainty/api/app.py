"""
FastAPI application for Grammar Uncertainty Analyzer.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from grammar_uncertainty import __version__
from grammar_uncertainty.core.analyzer import GrammarAnalyzer
from grammar_uncertainty.grammars import list_grammars, get_grammar_handler
from grammar_uncertainty.api.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    GrammarInfo,
    GrammarsResponse,
    HealthResponse,
    SetupRequest,
    SetupResponse,
    UncertaintyMetricsResponse,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Grammar Uncertainty Analyzer",
        description="Analyze uncertainty in Probabilistic Context-Free Grammars derived from program source code.",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(status="healthy", version=__version__)

    @app.get("/grammars", response_model=GrammarsResponse, tags=["Grammars"])
    async def list_available_grammars():
        """List all available grammar handlers."""
        grammars = []
        for g in list_grammars():
            grammars.append(
                GrammarInfo(
                    name=g.name,
                    description=g.description,
                    file_extensions=g.file_extensions,
                    is_setup=g.is_setup,
                )
            )
        return GrammarsResponse(grammars=grammars)

    @app.post("/setup", response_model=SetupResponse, tags=["Grammars"])
    async def setup_grammar(request: SetupRequest):
        """Set up a grammar (download and generate parser files)."""
        try:
            handler = get_grammar_handler(request.grammar)
            success = handler.setup(force=request.force)
            if success:
                return SetupResponse(
                    success=True,
                    grammar=request.grammar,
                    message=f"Grammar '{request.grammar}' set up successfully",
                )
            else:
                return SetupResponse(
                    success=False,
                    grammar=request.grammar,
                    message=f"Failed to set up grammar '{request.grammar}'",
                )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
    async def analyze(request: AnalyzeRequest):
        """
        Analyze programs in a folder and compute PCFG with uncertainty metrics.

        The folder_path should be accessible from the server's filesystem.
        When running in Docker, mount your data directory to /data.
        """
        try:
            analyzer = GrammarAnalyzer(grammar=request.grammar)

            result = analyzer.analyze(
                folder_path=request.folder_path,
                compute_uncertainty=request.options.compute_uncertainty,
                sample_size=request.options.sample_size,
            )

            # Convert uncertainty metrics
            uncertainty_response = None
            if result.uncertainty:
                uncertainty_response = UncertaintyMetricsResponse(
                    grammar_entropy=result.uncertainty.grammar_entropy,
                    perplexity=result.uncertainty.perplexity,
                    shannon_entropy_by_nt=result.uncertainty.shannon_entropy_by_nt,
                    renyi_entropy_order2=result.uncertainty.renyi_entropy_order2,
                    kl_divergence_from_uniform=result.uncertainty.kl_divergence_from_uniform,
                    nsui=result.uncertainty.nsui,
                    spectral_radius=result.uncertainty.spectral_radius,
                )

            return AnalyzeResponse(
                success=result.success,
                grammar=result.grammar,
                programs_parsed=result.programs_parsed,
                programs_failed=result.programs_failed,
                total_rules=result.total_rules,
                unique_rules=result.unique_rules,
                pcfg=result._serialize_pcfg(),
                pcfg_stats=result.pcfg_stats,
                uncertainty=uncertainty_response,
                errors=result.errors,
                analysis_time_ms=result.analysis_time_ms,
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# Create default app instance
app = create_app()
