"""
Utility functions for ANTLR parse tree manipulation.
"""

from typing import Any


def get_tree_depth(tree: Any) -> int:
    """
    Calculate the depth of an ANTLR parse tree.

    Args:
        tree: An ANTLR parse tree node with getChildCount() and getChild(i) methods.

    Returns:
        The maximum depth of the tree (0 for leaf nodes).
    """
    if tree.getChildCount() == 0:
        return 0

    return 1 + max(
        get_tree_depth(tree.getChild(i)) for i in range(tree.getChildCount())
    )


def count_nodes(tree: Any) -> int:
    """
    Count the total number of nodes in an ANTLR parse tree.

    Args:
        tree: An ANTLR parse tree node with getChildCount() and getChild(i) methods.

    Returns:
        Total count of nodes including the root.
    """
    count = 1  # Count this node
    for i in range(tree.getChildCount()):
        count += count_nodes(tree.getChild(i))
    return count


def get_tree_text(tree: Any) -> str:
    """
    Get the text content of an ANTLR parse tree node.

    Args:
        tree: An ANTLR parse tree node.

    Returns:
        The text representation of the node.
    """
    if hasattr(tree, "getText"):
        return tree.getText()
    return str(tree)
