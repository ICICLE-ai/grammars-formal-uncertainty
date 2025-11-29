"""
Class to represent a grammar rule with rich metadata.
"""

import hashlib
from typing import Any, Dict, List, Optional, Tuple


class Rule:
    """
    Represents a grammar rule with rich metadata.

    A rule consists of a left-hand side (non-terminal) and a right-hand side
    (sequence of terminals and/or non-terminals), along with contextual
    information about where and how the rule was applied.

    Attributes:
        lhs: Left-hand side non-terminal symbol (e.g., "command", "term").
        rhs: Right-hand side symbols as a tuple.
        context: Dictionary containing contextual information.
        depth: Depth in the parse tree.
        program_index: Index of the program this rule came from.
        node_id: Unique ID of the node in the parse tree.
        parent_id: ID of the parent node.
        occurrences: Count of how many times this rule was observed.
        source_text: The actual source code substring for this rule.
        start_index: Starting index in the source.
        stop_index: Ending index in the source.
        structure_hash: MD5 hash of the rule structure.
    """

    def __init__(
        self,
        lhs: str,
        rhs: List[str],
        context: Optional[Dict[str, Any]] = None,
        depth: int = 0,
        program_index: Optional[int] = None,
        node_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        source_text: Optional[str] = None,
        start_index: Optional[int] = None,
        stop_index: Optional[int] = None,
    ):
        self.lhs = lhs
        self.rhs = tuple(rhs)  # Make rhs immutable for hashing
        self.context = context or {}
        self.depth = depth
        self.program_index = program_index
        self.node_id = node_id
        self.parent_id = parent_id
        self.occurrences = 1
        self.source_text = source_text
        self.start_index = start_index
        self.stop_index = stop_index
        self.structure_hash = hashlib.md5(
            f"{lhs}->{','.join(rhs)}".encode()
        ).hexdigest()

    def __eq__(self, other: object) -> bool:
        """Check structural equality (same lhs and rhs)."""
        if not isinstance(other, Rule):
            return False
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __hash__(self) -> int:
        """Hash based only on rule structure."""
        return hash((self.lhs, self.rhs))

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.lhs} -> {' '.join(self.rhs)}"

    def __repr__(self) -> str:
        return self.__str__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to a dictionary representation with metadata."""
        return {
            "lhs": self.lhs,
            "rhs": list(self.rhs),
            "depth": self.depth,
            "program_index": self.program_index,
            "context": self.context,
            "occurrences": self.occurrences,
            "structure_hash": self.structure_hash,
            "source_text": self.source_text,
            "start_index": self.start_index,
            "stop_index": self.stop_index,
        }
