"""
Prolog Grammar Handler.

Implements the GrammarHandler interface for parsing Prolog programs.
"""

import time
import hashlib
from pathlib import Path
from typing import List, Optional
from collections import Counter

from grammar_uncertainty.grammars.base import GrammarHandler, ParseResult
from grammar_uncertainty.structs import Rule, ParseContext
from grammar_uncertainty.utils import get_tree_depth, count_nodes


class PrologGrammarHandler(GrammarHandler):
    """
    Grammar handler for Prolog programs.

    This handler uses ANTLR4 to parse Prolog programs and extract
    grammar rules with rich metadata.
    """

    def __init__(self):
        self._parser_module = None
        self._lexer_module = None
        self._listener_module = None

    @property
    def name(self) -> str:
        return "prolog"

    @property
    def description(self) -> str:
        return "Prolog logic programming language"

    @property
    def file_extensions(self) -> List[str]:
        return [".pl", ".prolog"]

    def _get_generated_dir(self) -> Path:
        """Get the directory for generated ANTLR files."""
        return Path(__file__).parent / "generated"

    def is_setup_complete(self) -> bool:
        """Check if ANTLR parser files have been generated."""
        generated_dir = self._get_generated_dir()
        required_files = [
            "prologLexer.py",
            "prologParser.py",
            "prologListener.py",
        ]
        return all((generated_dir / f).exists() for f in required_files)

    def setup(self, force: bool = False) -> bool:
        """
        Download Prolog grammar and generate ANTLR parser files.

        Args:
            force: If True, regenerate even if files exist.

        Returns:
            True if setup was successful.
        """
        import os
        import subprocess
        import urllib.request

        generated_dir = self._get_generated_dir()
        generated_dir.mkdir(parents=True, exist_ok=True)

        # ANTLR version configuration
        ANTLR_VERSION = "4.13.2"
        ANTLR_JAR = f"antlr-{ANTLR_VERSION}-complete.jar"
        ANTLR_URL = f"https://www.antlr.org/download/{ANTLR_JAR}"
        GRAMMAR_URL = "https://raw.githubusercontent.com/antlr/grammars-v4/master/prolog/prolog.g4"

        # Check if already setup
        if self.is_setup_complete() and not force:
            print(f"Prolog grammar already set up in {generated_dir}")
            return True

        # Download grammar file
        grammar_file = generated_dir / "prolog.g4"
        if not grammar_file.exists() or force:
            print("Downloading Prolog grammar...")
            urllib.request.urlretrieve(GRAMMAR_URL, grammar_file)

        # Download ANTLR JAR
        antlr_jar = generated_dir / ANTLR_JAR
        if not antlr_jar.exists():
            print(f"Downloading ANTLR {ANTLR_VERSION}...")
            urllib.request.urlretrieve(ANTLR_URL, antlr_jar)

        # Remove old generated files if force
        if force:
            for f in generated_dir.glob("prolog*.py"):
                f.unlink()

        # Generate parser
        print("Generating ANTLR parser...")
        try:
            subprocess.run(
                ["java", "-jar", str(antlr_jar), "-Dlanguage=Python3", "prolog.g4"],
                cwd=generated_dir,
                check=True,
            )
            print("Parser generated successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error generating parser: {e}")
            print("Please make sure Java is installed.")
            return False
        except FileNotFoundError:
            print("Java not found. Please install Java to generate the parser.")
            return False

    def _load_parser_modules(self):
        """Lazy-load the ANTLR parser modules."""
        if self._parser_module is not None:
            return

        if not self.is_setup_complete():
            raise RuntimeError(
                "Prolog grammar not set up. Run 'grammar-uncertainty setup prolog' first."
            )

        import sys
        generated_dir = self._get_generated_dir()

        # Add generated dir to path temporarily
        sys.path.insert(0, str(generated_dir))
        try:
            from prologLexer import prologLexer
            from prologParser import prologParser
            from prologListener import prologListener

            self._lexer_module = prologLexer
            self._parser_module = prologParser
            self._listener_module = prologListener
        finally:
            sys.path.remove(str(generated_dir))

    def parse(self, program: str, program_index: int = 0) -> ParseResult:
        """
        Parse a Prolog program and extract grammar rules.

        Args:
            program: The program source code.
            program_index: Index of the program in a batch.

        Returns:
            ParseResult containing rules and metadata.
        """
        from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
        from antlr4.error.ErrorStrategy import BailErrorStrategy

        self._load_parser_modules()

        try:
            # Create input stream
            input_stream = InputStream(program.strip())

            # Create lexer and parser
            lexer = self._lexer_module(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = self._parser_module(token_stream)
            parser._errHandler = BailErrorStrategy()

            # Parse - Prolog grammar uses 'p_text' as start rule
            start_time = time.time()
            tree = parser.p_text()
            parse_time = time.time() - start_time

            # Collect metrics
            tree_depth = get_tree_depth(tree)
            node_count = count_nodes(tree)
            token_count = len(token_stream.tokens)

            # Create listener and walk tree
            listener = PrologRuleCollector(
                parser, program_index=program_index, full_text=program.strip()
            )
            walker = ParseTreeWalker()
            walker.walk(listener, tree)

            # Get results
            rules = listener.get_rules()
            rule_sequence = listener.get_rule_sequence()
            avg_branching = listener.get_average_branching()

            metadata = {
                "index": program_index,
                "tree_depth": tree_depth,
                "node_count": node_count,
                "token_count": token_count,
                "parse_time": parse_time,
                "rule_count": len(rules),
                "unique_rules": len(set(rule.structure_hash for rule in rules)),
                "average_branching": avg_branching,
                "variables": listener.context.variables,
                "operators_used": list(listener.context.operators),
                "symbol_frequencies": dict(listener.context.symbols_seen),
                "most_common_symbols": listener.context.symbols_seen.most_common(10),
                "rule_sequence_hash": hashlib.md5(
                    ",".join(rule_sequence).encode()
                ).hexdigest(),
            }

            return ParseResult(success=True, rules=rules, metadata=metadata)

        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e),
                metadata={"index": program_index},
            )


class PrologRuleCollector:
    """
    ANTLR listener to collect grammar rules from Prolog parse trees.
    """

    def __init__(self, parser, program_index: int = 0, full_text: str = ""):
        self.parser = parser
        self.rules: List[Rule] = []
        self.context = ParseContext()
        self.program_index = program_index
        self.full_text = full_text
        self.terminal_values = {}
        self.start_time = time.time()
        self.rule_sequence: List[str] = []
        self.node_branch_counts = Counter()

    def visitTerminal(self, node):
        """Called when visiting a terminal node."""
        pass

    def visitErrorNode(self, node):
        """Called when visiting an error node."""
        pass

    def enterEveryRule(self, ctx):
        """Called when entering every rule during parsing."""
        rule_name = self.parser.ruleNames[ctx.getRuleIndex()]

        # Record entering this node
        node_id, parent_id = self.context.enter_node(rule_name)

        # Extract source text
        source_text = None
        start_index = None
        stop_index = None

        if hasattr(ctx, "start") and hasattr(ctx, "stop") and ctx.start and ctx.stop:
            start_index = ctx.start.start
            stop_index = ctx.stop.stop
            try:
                source_text = ctx.start.getInputStream().getText(
                    ctx.start.start, ctx.stop.stop
                )
            except Exception:
                if self.full_text and 0 <= start_index <= stop_index < len(self.full_text):
                    source_text = self.full_text[start_index : stop_index + 1]

        # Collect terminal tokens
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if hasattr(child, "symbol"):
                self.terminal_values[id(child)] = child.getText()

        # Track rule sequence and branching
        self.rule_sequence.append(rule_name)
        self.node_branch_counts[rule_name] += ctx.getChildCount()

        # Create children list
        children = []
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if hasattr(child, "getRuleIndex"):
                child_rule_name = self.parser.ruleNames[child.getRuleIndex()]
                children.append(child_rule_name)

            elif hasattr(child, "symbol"):
                if child.symbol.type > 0:
                    token_name = self.parser.symbolicNames[child.symbol.type]
                    if token_name:
                        children.append(token_name)
                        self.context.register_symbol(token_name)

                        # Track Prolog-specific operators
                        if token_name in [":-", "?-", ",", ";", "->", "\\+", "=", "\\=",
                                          "==", "\\==", "<", ">", "=<", ">=", "is"]:
                            self.context.register_operator(token_name)

        if children:
            rule = Rule(
                rule_name,
                children,
                context=self.context.get_current_context(),
                depth=len(self.context.current_scope),
                program_index=self.program_index,
                node_id=node_id,
                parent_id=parent_id,
                source_text=source_text,
                start_index=start_index,
                stop_index=stop_index,
            )
            self.rules.append(rule)

    def exitEveryRule(self, ctx):
        """Called when exiting every rule during parsing."""
        self.context.exit_node()

    def get_rules(self) -> List[Rule]:
        """Return collected rules."""
        return self.rules

    def get_rule_sequence(self) -> List[str]:
        """Return the sequence of rules applied."""
        return self.rule_sequence

    def get_average_branching(self) -> dict:
        """Calculate average branching factor by rule type."""
        avg_branching = {}
        rule_counts = Counter(self.rule_sequence)
        for rule, total_branches in self.node_branch_counts.items():
            count = rule_counts[rule]
            if count > 0:
                avg_branching[rule] = total_branches / count
        return avg_branching

    def get_parse_time(self) -> float:
        """Get time taken for parsing."""
        return time.time() - self.start_time
