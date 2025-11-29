"""
Abstract base class for grammar handlers.

To add support for a new grammar/language:
1. Create a new module in grammars/ (e.g., grammars/python/)
2. Implement a class that inherits from GrammarHandler
3. Register it in grammars/registry.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class ParseResult:
    """Result of parsing a single program."""

    success: bool
    rules: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def rule_count(self) -> int:
        return len(self.rules)


@dataclass
class GrammarInfo:
    """Information about a grammar handler."""

    name: str
    description: str
    file_extensions: List[str]
    is_setup: bool = False


class GrammarHandler(ABC):
    """
    Abstract base class for grammar handlers.

    Each grammar handler provides parsing capabilities for a specific
    programming language using ANTLR-generated parsers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the grammar name (e.g., 'smtlib', 'python', 'java')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a human-readable description of the grammar."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Return list of file extensions this grammar handles (e.g., ['.smt2'])."""
        pass

    @abstractmethod
    def setup(self, force: bool = False) -> bool:
        """
        Download grammar and generate ANTLR parser files.

        Args:
            force: If True, regenerate even if files exist.

        Returns:
            True if setup was successful.
        """
        pass

    @abstractmethod
    def is_setup_complete(self) -> bool:
        """Check if the grammar has been set up (parser files generated)."""
        pass

    @abstractmethod
    def parse(self, program: str, program_index: int = 0) -> ParseResult:
        """
        Parse a single program and extract grammar rules.

        Args:
            program: The program source code as a string.
            program_index: Index of the program in a batch (for tracking).

        Returns:
            ParseResult containing rules and metadata.
        """
        pass

    def load_programs(self, folder_path: str) -> List[str]:
        """
        Load all programs from a folder that match this grammar's extensions.

        Args:
            folder_path: Path to folder containing program files.

        Returns:
            List of program source code strings.
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        programs = []
        for ext in self.file_extensions:
            for file_path in folder.rglob(f"*{ext}"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        programs.append(f.read())
                except Exception as e:
                    print(f"Warning: Could not read {file_path}: {e}")

        return programs

    def get_info(self) -> GrammarInfo:
        """Return information about this grammar handler."""
        return GrammarInfo(
            name=self.name,
            description=self.description,
            file_extensions=self.file_extensions,
            is_setup=self.is_setup_complete(),
        )
