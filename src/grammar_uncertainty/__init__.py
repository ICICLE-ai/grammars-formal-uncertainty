"""
Grammar Uncertainty Analyzer

A Python package for analyzing uncertainty in Probabilistic Context-Free Grammars
derived from program source code.

Usage:
    from grammar_uncertainty import GrammarAnalyzer

    analyzer = GrammarAnalyzer(grammar="smtlib")
    result = analyzer.analyze("/path/to/programs")
    print(result.uncertainty.grammar_entropy)
"""

from grammar_uncertainty.core.analyzer import GrammarAnalyzer, AnalysisResult

__version__ = "0.1.0"
__all__ = ["GrammarAnalyzer", "AnalysisResult", "__version__"]
