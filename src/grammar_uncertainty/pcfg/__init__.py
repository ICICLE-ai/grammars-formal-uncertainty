"""
PCFG (Probabilistic Context-Free Grammar) computation.
"""

from grammar_uncertainty.pcfg.pcfg import (
    PCFGModel,
    compute_pcfg,
    export_pcfg_json,
)

__all__ = [
    "PCFGModel",
    "compute_pcfg",
    "export_pcfg_json",
]
