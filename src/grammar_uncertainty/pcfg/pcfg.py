"""
PCFG (Probabilistic Context-Free Grammar) computation module.

Extracts grammar rules from parse trees and computes probabilities using
maximum likelihood estimation (MLE).
"""

from collections import defaultdict, Counter
import json
import os
from typing import Dict, List, Tuple, Any


class PCFGModel:
    """PCFG model using maximum likelihood estimation."""

    def __init__(self):
        self._pcfg = {}
        self.global_stats = {}

    def compute_pcfg(self, programs, all_rules, parse_metadata_list, beta=0.0):
        """
        Compute PCFG from collected rules using MLE.

        Args:
            programs: List of program sources
            all_rules: List of Rule objects from parse trees
            parse_metadata_list: Metadata about parsing
            beta: Laplace smoothing parameter (0 = no smoothing)

        Returns:
            Tuple of (pcfg_dict, global_stats)
        """
        if not all_rules:
            empty_stats = {
                "total_rules": 0,
                "unique_rules": 0,
                "non_terminals": 0,
                "parse_metadata": parse_metadata_list
            }
            self.global_stats = empty_stats
            return {}, empty_stats

        # Count rules
        rule_count = defaultdict(int)
        rule_map = {}
        lhs_count = defaultdict(int)
        lhs_to_rules = defaultdict(set)

        # Track statistics
        rule_depth_distribution = defaultdict(list)
        rule_context_distribution = defaultdict(list)
        program_rule_distribution = defaultdict(lambda: defaultdict(int))
        rule_source_examples = defaultdict(list)

        for rule in all_rules:
            rule_key = (rule.lhs, tuple(rule.rhs) if isinstance(rule.rhs, list) else rule.rhs)
            rule_count[rule_key] += 1
            lhs_count[rule.lhs] += 1
            lhs_to_rules[rule.lhs].add(rule_key)
            rule_map[rule_key] = rule

            rule_depth_distribution[rule_key].append(rule.depth)

            if hasattr(rule, 'context') and rule.context:
                rule_context_distribution[rule_key].append(rule.context)

            if hasattr(rule, 'program_index') and rule.program_index is not None:
                program_rule_distribution[rule.program_index][rule_key] += 1

            if hasattr(rule, 'source_text') and rule.source_text and len(rule_source_examples[rule_key]) < 5:
                rule_source_examples[rule_key].append({
                    "text": rule.source_text,
                    "program_index": getattr(rule, 'program_index', None),
                    "start_index": getattr(rule, 'start_index', None),
                    "stop_index": getattr(rule, 'stop_index', None)
                })

        # Compute probabilities
        _pcfg = {}
        for rule_key, count in rule_count.items():
            lhs = rule_key[0]
            num_rules_with_lhs = len(lhs_to_rules[lhs])

            # MLE with optional Laplace smoothing
            probability = (count + beta) / (lhs_count[lhs] + beta * num_rules_with_lhs)

            rule_obj = rule_map[rule_key]
            depths = rule_depth_distribution[rule_key]

            program_distribution = {}
            for prog_idx in range(len(programs)):
                program_distribution[str(prog_idx)] = program_rule_distribution[prog_idx][rule_key]

            _pcfg[rule_key] = {
                "rule": str(rule_obj),
                "lhs": lhs,
                "rhs": list(rule_key[1]) if isinstance(rule_key[1], tuple) else rule_key[1],
                "probability": probability,
                "count": count,
                "depth_stats": {
                    "avg": sum(depths) / len(depths) if depths else 0,
                    "max": max(depths) if depths else 0,
                    "min": min(depths) if depths else 0,
                    "distribution": dict(Counter(depths))
                },
                "contexts": rule_context_distribution[rule_key],
                "program_distribution": program_distribution,
                "structure_hash": getattr(rule_obj, 'structure_hash', ''),
                "source_examples": rule_source_examples[rule_key]
            }

        # Global statistics
        if _pcfg:
            global_stats = {
                "total_rules": len(all_rules),
                "unique_rules": len(rule_count),
                "non_terminals": len(lhs_count),
                "max_probability": max(entry["probability"] for entry in _pcfg.values()),
                "min_probability": min(entry["probability"] for entry in _pcfg.values()),
                "avg_probability": sum(entry["probability"] for entry in _pcfg.values()) / len(_pcfg),
                "parse_metadata": parse_metadata_list,
                "lhs_distribution": dict(lhs_count),
                "rule_depth_summary": {
                    "max": max(entry["depth_stats"]["max"] for entry in _pcfg.values()),
                    "min": min(entry["depth_stats"]["min"] for entry in _pcfg.values()),
                    "avg": sum(entry["depth_stats"]["avg"] for entry in _pcfg.values()) / len(_pcfg)
                },
                "rules_with_source_examples": sum(1 for entry in _pcfg.values() if entry["source_examples"])
            }
        else:
            global_stats = {
                "total_rules": 0,
                "unique_rules": 0,
                "non_terminals": 0,
                "parse_metadata": parse_metadata_list
            }

        self._pcfg = _pcfg
        self.global_stats = global_stats
        return _pcfg, global_stats

    def get_pcfg(self):
        """Return the computed PCFG."""
        return self._pcfg, self.global_stats

    def export_pcfg_json(self, filename="logs/pcfg_model.json"):
        """Export PCFG to JSON."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        json_data = {
            "metadata": self.global_stats,
            "rules": {}
        }

        for rule_key, rule_data in self._pcfg.items():
            std_key = f"{rule_key[0]}->{','.join(rule_key[1])}"

            base_entry = {
                "lhs": rule_key[0],
                "rhs": list(rule_key[1]),
                "probability": rule_data["probability"]
            }

            base_entry["_"] = {
                "count": rule_data.get("count", 0),
                "depth_stats": rule_data.get("depth_stats", {}),
                "program_distribution": rule_data.get("program_distribution", {}),
                "structure_hash": rule_data.get("structure_hash", "")
            }

            if "contexts" in rule_data and rule_data["contexts"]:
                base_entry["_"]["contexts"] = {
                    "count": len(rule_data["contexts"]),
                    "sample": rule_data["contexts"][0] if rule_data["contexts"] else {}
                }

            if "source_examples" in rule_data and rule_data["source_examples"]:
                base_entry["_"]["source_examples"] = rule_data["source_examples"]

            json_data["rules"][std_key] = base_entry

        with open(filename, 'w') as f:
            json.dump(json_data, f, indent=2)

        return filename


def compute_pcfg(programs, all_rules, parse_metadata_list, **kwargs):
    """
    Compute PCFG from collected rules.

    Args:
        programs: List of program sources
        all_rules: List of Rule objects
        parse_metadata_list: Parsing metadata

    Returns:
        Tuple of (pcfg_dict, global_stats)
    """
    model = PCFGModel()
    return model.compute_pcfg(programs, all_rules, parse_metadata_list)


def export_pcfg_json(_pcfg, global_stats, filename="logs/pcfg_model.json"):
    """Export PCFG to JSON file."""
    model = PCFGModel()
    model._pcfg = _pcfg
    model.global_stats = global_stats
    return model.export_pcfg_json(filename)
