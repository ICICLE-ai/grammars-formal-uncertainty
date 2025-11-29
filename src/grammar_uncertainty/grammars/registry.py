"""
Registry of available grammar handlers.

This module provides a central registry for all grammar handlers,
allowing dynamic lookup and listing of available grammars.
"""

from typing import Dict, List, Optional, Type
from grammar_uncertainty.grammars.base import GrammarHandler, GrammarInfo

# Registry of grammar handlers
_GRAMMAR_REGISTRY: Dict[str, Type[GrammarHandler]] = {}


def register_grammar(name: str, handler_class: Type[GrammarHandler]) -> None:
    """
    Register a grammar handler.

    Args:
        name: The grammar name (e.g., 'smtlib').
        handler_class: The GrammarHandler subclass.
    """
    _GRAMMAR_REGISTRY[name.lower()] = handler_class


def get_grammar_handler(name: str) -> GrammarHandler:
    """
    Get a grammar handler instance by name.

    Args:
        name: The grammar name (e.g., 'smtlib').

    Returns:
        An instance of the grammar handler.

    Raises:
        ValueError: If the grammar is not registered.
    """
    name_lower = name.lower()
    if name_lower not in _GRAMMAR_REGISTRY:
        available = ", ".join(_GRAMMAR_REGISTRY.keys())
        raise ValueError(
            f"Unknown grammar: '{name}'. Available grammars: {available or 'none'}"
        )
    return _GRAMMAR_REGISTRY[name_lower]()


def list_grammars() -> List[GrammarInfo]:
    """
    List all registered grammars.

    Returns:
        List of GrammarInfo objects for all registered grammars.
    """
    return [handler_class().get_info() for handler_class in _GRAMMAR_REGISTRY.values()]


def is_grammar_registered(name: str) -> bool:
    """Check if a grammar is registered."""
    return name.lower() in _GRAMMAR_REGISTRY


# Import and register built-in grammars
def _register_builtin_grammars():
    """Register built-in grammar handlers."""
    try:
        from grammar_uncertainty.grammars.smtlib.handler import SMTLibGrammarHandler
        register_grammar("smtlib", SMTLibGrammarHandler)
    except ImportError:
        pass  # Grammar not available

    try:
        from grammar_uncertainty.grammars.prolog.handler import PrologGrammarHandler
        register_grammar("prolog", PrologGrammarHandler)
    except ImportError:
        pass  # Grammar not available


_register_builtin_grammars()
