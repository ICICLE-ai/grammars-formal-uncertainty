"""
Main GrammarAnalyzer class that provides a unified interface for grammar analysis.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

from grammar_uncertainty.grammars import get_grammar_handler, list_grammars
from grammar_uncertainty.pcfg import compute_pcfg, export_pcfg_json


@dataclass
class UncertaintyMetrics:
    """Uncertainty metrics computed from a PCFG."""

    grammar_entropy: float = 0.0
    perplexity: float = 0.0
    shannon_entropy_by_nt: Dict[str, float] = field(default_factory=dict)
    renyi_entropy_order2: Dict[str, float] = field(default_factory=dict)
    kl_divergence_from_uniform: Dict[str, float] = field(default_factory=dict)
    confidence_intervals: Dict[str, Any] = field(default_factory=dict)
    nsui: float = 0.0
    spectral_radius: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "grammar_entropy": self.grammar_entropy,
            "perplexity": self.perplexity,
            "shannon_entropy_by_nt": self.shannon_entropy_by_nt,
            "renyi_entropy_order2": self.renyi_entropy_order2,
            "kl_divergence_from_uniform": self.kl_divergence_from_uniform,
            "confidence_intervals": self.confidence_intervals,
            "nsui": self.nsui,
            "spectral_radius": self.spectral_radius,
        }


@dataclass
class AnalysisResult:
    """Result of a grammar analysis."""

    success: bool
    grammar: str
    programs_parsed: int
    programs_failed: int
    total_rules: int
    unique_rules: int
    pcfg: Dict[str, Any] = field(default_factory=dict)
    pcfg_stats: Dict[str, Any] = field(default_factory=dict)
    uncertainty: Optional[UncertaintyMetrics] = None
    parse_metadata: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    analysis_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "grammar": self.grammar,
            "programs_parsed": self.programs_parsed,
            "programs_failed": self.programs_failed,
            "total_rules": self.total_rules,
            "unique_rules": self.unique_rules,
            "pcfg": self._serialize_pcfg(),
            "pcfg_stats": self.pcfg_stats,
            "uncertainty": self.uncertainty.to_dict() if self.uncertainty else None,
            "parse_metadata": self.parse_metadata,
            "errors": self.errors,
            "analysis_time_ms": self.analysis_time_ms,
        }

    def _serialize_pcfg(self) -> Dict[str, Any]:
        """Serialize PCFG with tuple keys to string keys."""
        serialized = {}
        for key, value in self.pcfg.items():
            if isinstance(key, tuple):
                str_key = f"{key[0]}->{','.join(key[1])}"
            else:
                str_key = str(key)
            serialized[str_key] = value
        return serialized

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: str) -> None:
        """Save results to a JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())


class GrammarAnalyzer:
    """
    Main class for analyzing grammars and computing uncertainty metrics.

    This class provides a unified interface for:
    - Parsing programs using ANTLR grammars
    - Computing Probabilistic Context-Free Grammars (PCFGs)
    - Calculating uncertainty metrics (entropy, perplexity, etc.)

    Example:
        >>> from grammar_uncertainty import GrammarAnalyzer
        >>> analyzer = GrammarAnalyzer(grammar="smtlib")
        >>> result = analyzer.analyze("/path/to/smt/programs")
        >>> print(result.uncertainty.grammar_entropy)
    """

    def __init__(self, grammar: str = "smtlib"):
        """
        Initialize the analyzer.

        Args:
            grammar: Name of the grammar to use (e.g., "smtlib", "prolog").
        """
        self.grammar_name = grammar
        self._handler = None

    @property
    def handler(self):
        """Get the grammar handler (lazy initialization)."""
        if self._handler is None:
            self._handler = get_grammar_handler(self.grammar_name)
        return self._handler

    @staticmethod
    def available_grammars() -> List[str]:
        """List available grammar handlers."""
        return [g.name for g in list_grammars()]

    def setup_grammar(self, force: bool = False) -> bool:
        """
        Set up the grammar (download and generate parser).

        Args:
            force: If True, regenerate even if files exist.

        Returns:
            True if setup was successful.
        """
        return self.handler.setup(force=force)

    def analyze(
        self,
        folder_path: str,
        compute_uncertainty: bool = True,
        sample_size: Optional[int] = None,
    ) -> AnalysisResult:
        """
        Analyze programs in a folder.

        Args:
            folder_path: Path to folder containing program files.
            compute_uncertainty: Whether to compute uncertainty metrics.
            sample_size: Number of programs for uncertainty calculation.

        Returns:
            AnalysisResult containing PCFG and uncertainty metrics.
        """
        start_time = time.time()
        errors = []

        # Ensure grammar is set up
        if not self.handler.is_setup_complete():
            if not self.handler.setup():
                return AnalysisResult(
                    success=False,
                    grammar=self.grammar_name,
                    programs_parsed=0,
                    programs_failed=0,
                    total_rules=0,
                    unique_rules=0,
                    errors=["Grammar setup failed"],
                )

        # Load programs
        try:
            programs = self.handler.load_programs(folder_path)
        except FileNotFoundError as e:
            return AnalysisResult(
                success=False,
                grammar=self.grammar_name,
                programs_parsed=0,
                programs_failed=0,
                total_rules=0,
                unique_rules=0,
                errors=[str(e)],
            )

        if not programs:
            return AnalysisResult(
                success=False,
                grammar=self.grammar_name,
                programs_parsed=0,
                programs_failed=0,
                total_rules=0,
                unique_rules=0,
                errors=["No programs found in folder"],
            )

        # Parse programs
        all_rules = []
        parse_metadata = []
        programs_failed = 0

        for i, program in enumerate(programs):
            result = self.handler.parse(program, program_index=i)
            if result.success:
                all_rules.extend(result.rules)
                parse_metadata.append(result.metadata)
            else:
                programs_failed += 1
                errors.append(f"Program {i}: {result.error}")

        programs_parsed = len(programs) - programs_failed

        if not all_rules:
            return AnalysisResult(
                success=False,
                grammar=self.grammar_name,
                programs_parsed=programs_parsed,
                programs_failed=programs_failed,
                total_rules=0,
                unique_rules=0,
                errors=errors or ["No rules extracted from programs"],
            )

        # Compute PCFG
        pcfg, pcfg_stats = compute_pcfg(programs, all_rules, parse_metadata)

        # Compute uncertainty metrics
        uncertainty = None
        if compute_uncertainty and pcfg:
            uncertainty = self._compute_uncertainty(
                pcfg,
                sample_size=sample_size or len(programs),
            )

        analysis_time = (time.time() - start_time) * 1000

        return AnalysisResult(
            success=True,
            grammar=self.grammar_name,
            programs_parsed=programs_parsed,
            programs_failed=programs_failed,
            total_rules=len(all_rules),
            unique_rules=len(pcfg),
            pcfg=pcfg,
            pcfg_stats=pcfg_stats,
            uncertainty=uncertainty,
            parse_metadata=parse_metadata,
            errors=errors,
            analysis_time_ms=analysis_time,
        )

    def _compute_uncertainty(
        self,
        pcfg: Dict,
        sample_size: int,
    ) -> UncertaintyMetrics:
        """Compute uncertainty metrics from a PCFG."""
        import math
        from collections import defaultdict

        # Group rules by LHS
        rules_by_lhs = defaultdict(list)
        for rule_key, rule_data in pcfg.items():
            lhs = rule_data["lhs"]
            rhs = tuple(rule_data["rhs"])
            prob = rule_data["probability"]
            rules_by_lhs[lhs].append((rhs, prob))

        # Calculate Shannon entropy for each non-terminal
        shannon_entropy = {}
        for lhs, rules in rules_by_lhs.items():
            entropy = 0.0
            for _, prob in rules:
                if prob > 0:
                    entropy -= prob * math.log2(prob)
            shannon_entropy[lhs] = entropy

        # Calculate Rényi entropy (order 2)
        renyi_entropy = {}
        for lhs, rules in rules_by_lhs.items():
            sum_sq = sum(prob ** 2 for _, prob in rules)
            if sum_sq > 0:
                renyi_entropy[lhs] = -math.log2(sum_sq)
            else:
                renyi_entropy[lhs] = 0.0

        # Calculate KL divergence from uniform
        kl_divergence = {}
        for lhs, rules in rules_by_lhs.items():
            n = len(rules)
            if n > 0:
                uniform_prob = 1.0 / n
                kl = 0.0
                for _, prob in rules:
                    if prob > 0:
                        kl += prob * math.log2(prob / uniform_prob)
                kl_divergence[lhs] = kl
            else:
                kl_divergence[lhs] = 0.0

        # Calculate grammar-wide entropy (weighted by rule frequency)
        total_entropy = 0.0
        total_weight = 0
        for lhs, entropy in shannon_entropy.items():
            weight = len(rules_by_lhs[lhs])
            total_entropy += entropy * weight
            total_weight += weight

        grammar_entropy = total_entropy / total_weight if total_weight > 0 else 0.0
        perplexity = 2 ** grammar_entropy if grammar_entropy > 0 else 1.0

        # Calculate NSUI (Normalized Structural Uncertainty Index)
        max_possible_entropy = math.log2(len(pcfg)) if len(pcfg) > 1 else 1.0
        nsui = grammar_entropy / max_possible_entropy if max_possible_entropy > 0 else 0.0

        return UncertaintyMetrics(
            grammar_entropy=grammar_entropy,
            perplexity=perplexity,
            shannon_entropy_by_nt=shannon_entropy,
            renyi_entropy_order2=renyi_entropy,
            kl_divergence_from_uniform=kl_divergence,
            nsui=nsui,
        )

    def analyze_and_save(
        self,
        folder_path: str,
        output_path: str,
        compute_uncertainty: bool = True,
    ) -> AnalysisResult:
        """
        Analyze programs and save results to a file.

        Args:
            folder_path: Path to folder containing program files.
            output_path: Path to save the results JSON.
            compute_uncertainty: Whether to compute uncertainty metrics.

        Returns:
            AnalysisResult.
        """
        result = self.analyze(folder_path, compute_uncertainty=compute_uncertainty)
        if result.success:
            result.save(output_path)
        return result
