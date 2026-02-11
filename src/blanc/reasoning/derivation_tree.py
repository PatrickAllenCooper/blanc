"""
Derivation tree structures for proof tracking.

Implements Definition 13 (AND-OR derivation trees) from paper.tex line 638.

Author: Patrick Cooper
Date: 2026-02-11
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set
from enum import Enum

from blanc.core.theory import Rule


class NodeType(Enum):
    """Type of node in derivation tree."""
    AND = "and"  # All children must be proven
    OR = "or"    # At least one child must be proven
    FACT = "fact"  # Leaf node (fact)


@dataclass
class DerivationNode:
    """
    Node in derivation tree.
    
    Represents a step in the defeasible proof.
    """
    literal: str
    node_type: NodeType
    rule: Optional[Rule] = None
    children: List['DerivationNode'] = field(default_factory=list)
    tag: str = "defeasible"  # "definite" or "defeasible"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "literal": self.literal,
            "node_type": self.node_type.value,
            "rule_label": self.rule.label if self.rule else None,
            "children": [child.to_dict() for child in self.children],
            "tag": self.tag,
        }
    
    def __repr__(self) -> str:
        """String representation."""
        rule_str = f" via {self.rule.label}" if self.rule else ""
        return f"DerivationNode({self.literal}{rule_str}, {self.node_type.value})"


@dataclass
class DerivationTree:
    """
    AND-OR derivation tree.
    
    Definition 13 (paper.tex line 638):
    T(D, q) is the AND-OR tree of the proof of +∂q.
    
    Used for:
    - Anomaly support computation: AnSup(D, α) = {r ∈ Rd | r in T(D, ~α)}
    - Provenance tracking
    - Visualization
    """
    root: DerivationNode
    
    def get_rules_used(self) -> List[Rule]:
        """
        Get all rules used in derivation.
        
        Returns:
            List of rules that appear in the tree (may contain duplicates)
        """
        rules = []
        
        def collect(node: DerivationNode):
            if node.rule:
                rules.append(node.rule)
            for child in node.children:
                collect(child)
        
        collect(self.root)
        return rules
    
    def get_defeasible_rules_used(self) -> List[Rule]:
        """
        Get defeasible rules used in derivation.
        
        Used for anomaly support computation (Definition 13).
        """
        from blanc.core.theory import RuleType
        
        all_rules = self.get_rules_used()
        return [r for r in all_rules if r.rule_type == RuleType.DEFEASIBLE]
    
    def depth(self) -> int:
        """Compute depth of derivation tree."""
        def compute_depth(node: DerivationNode) -> int:
            if not node.children:
                return 0
            return 1 + max(compute_depth(child) for child in node.children)
        
        return compute_depth(self.root)
    
    def size(self) -> int:
        """Compute total number of nodes in tree."""
        def count_nodes(node: DerivationNode) -> int:
            return 1 + sum(count_nodes(child) for child in node.children)
        
        return count_nodes(self.root)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "root": self.root.to_dict(),
            "depth": self.depth(),
            "size": self.size(),
            "rules_used": [r.label for r in self.get_rules_used() if r.label],
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return f"DerivationTree(root={self.root.literal}, depth={self.depth()}, size={self.size()})"


def build_derivation_tree(engine: 'DefeasibleEngine', literal: str) -> Optional[DerivationTree]:
    """
    Build derivation tree for literal.
    
    Definition 13: Construct AND-OR tree T(D, q).
    
    Args:
        engine: Defeasible engine with theory loaded
        literal: Literal to build tree for
    
    Returns:
        DerivationTree if literal is provable, None otherwise
    """
    if not engine.is_defeasibly_provable(literal):
        return None
    
    root = _build_node(engine, literal)
    return DerivationTree(root=root)


def _build_node(engine: 'DefeasibleEngine', literal: str) -> DerivationNode:
    """Recursively build derivation node."""
    from blanc.core.theory import RuleType
    
    # Check if it's a fact
    if literal in engine.theory.facts:
        return DerivationNode(
            literal=literal,
            node_type=NodeType.FACT,
            tag="definite"
        )
    
    # Check if definitely provable via strict rule
    for rule in engine.theory.get_rules_by_type(RuleType.STRICT):
        substitution = engine._match(rule.head, literal)
        if substitution:
            # Check if body is provable
            body_provable = all(
                engine.is_definitely_provable(engine._substitute(b, substitution))
                for b in rule.body
            )
            if body_provable:
                # Build AND node with children
                children = [
                    _build_node(engine, engine._substitute(b, substitution))
                    for b in rule.body
                ]
                return DerivationNode(
                    literal=literal,
                    node_type=NodeType.AND,
                    rule=rule,
                    children=children,
                    tag="definite"
                )
    
    # Check if defeasibly provable via defeasible rule
    for rule in engine.theory.get_rules_by_type(RuleType.DEFEASIBLE):
        substitution = engine._match(rule.head, literal)
        if substitution:
            # Check if body is provable
            body_provable = all(
                engine.is_defeasibly_provable(engine._substitute(b, substitution))
                for b in rule.body
            )
            if body_provable:
                # Build AND node with children
                children = [
                    _build_node(engine, engine._substitute(b, substitution))
                    for b in rule.body
                ]
                return DerivationNode(
                    literal=literal,
                    node_type=NodeType.AND,
                    rule=rule,
                    children=children,
                    tag="defeasible"
                )
    
    # Shouldn't reach here if literal is provable
    return DerivationNode(
        literal=literal,
        node_type=NodeType.FACT,
        tag="defeasible"
    )
