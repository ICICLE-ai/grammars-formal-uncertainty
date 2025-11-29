"""
Class to track context during parse tree traversal.
"""

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


class ParseContext:
    """
    Tracks the context of the parser's state during parse tree traversal.

    This provides a dynamic snapshot of where the parser is within the
    program's structure at any given moment, including scope information,
    variable declarations, operator usage, and symbol frequencies.

    Attributes:
        variables: Dictionary of declared variables and their types.
        current_scope: Stack of node types representing current scope path.
        operators: Set of operators used.
        node_counter: Counter for assigning unique node IDs.
        parent_stack: Stack of parent node IDs.
        node_map: Mapping from node IDs to nodes.
        rule_sequences: Sequence of rules applied.
        symbols_seen: Counter of symbol occurrences.
    """

    def __init__(self):
        self.variables: Dict[str, str] = {}
        self.current_scope: List[str] = []
        self.operators: set = set()
        self.node_counter: int = 0
        self.parent_stack: List[int] = []
        self.node_map: Dict[int, Any] = {}
        self.rule_sequences: List[str] = []
        self.symbols_seen: Counter = Counter()

    def enter_node(self, node_type: str) -> Tuple[int, Optional[int]]:
        """
        Record entering a node during traversal.

        Args:
            node_type: The type/name of the node being entered.

        Returns:
            Tuple of (node_id, parent_id).
        """
        self.node_counter += 1
        node_id = self.node_counter
        parent_id = self.parent_stack[-1] if self.parent_stack else None

        self.current_scope.append(node_type)
        self.parent_stack.append(node_id)

        return node_id, parent_id

    def exit_node(self) -> None:
        """Record exiting a node during traversal."""
        if self.current_scope:
            self.current_scope.pop()
        if self.parent_stack:
            self.parent_stack.pop()

    def register_variable(self, name: str, var_type: str) -> None:
        """Register a variable declaration."""
        self.variables[name] = var_type

    def register_operator(self, op: str) -> None:
        """Register an operator usage."""
        self.operators.add(op)

    def register_symbol(self, symbol: str) -> None:
        """Track symbol frequency."""
        self.symbols_seen[symbol] += 1

    def get_current_context(self) -> Dict[str, Any]:
        """
        Get a snapshot of the current context.

        Returns:
            Dictionary containing scope, depth, variables, operators, and symbols.
        """
        return {
            "scope": "/".join(self.current_scope),
            "scope_depth": len(self.current_scope),
            "variables_defined": len(self.variables),
            "operators_used": list(self.operators),
            "common_symbols": [s for s, c in self.symbols_seen.most_common(5)],
        }

    def reset(self) -> None:
        """Reset the context for reuse."""
        self.variables.clear()
        self.current_scope.clear()
        self.operators.clear()
        self.node_counter = 0
        self.parent_stack.clear()
        self.node_map.clear()
        self.rule_sequences.clear()
        self.symbols_seen.clear()
