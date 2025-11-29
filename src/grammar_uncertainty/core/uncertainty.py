#!/usr/bin/env python3
"""
# Advanced SMT-LIB PCFG Uncertainty Analyzer

## Overview
This script provides comprehensive uncertainty analysis for Probabilistic Context-Free Grammars (PCFGs)
derived from Language Model (LLM) generated SMT-LIB programs. It includes advanced information-theoretic
measures, statistical analysis, and comparative analysis between different PCFGs.

## Usage
```
python uncertainty.py [--primary PCFG_FILE] [--secondary PCFG_FILE] [--sample-size SIZE] [--output OUTPUT_FILE]
```

Arguments:
- `--primary`: Path to the primary PCFG JSON file (default: "logs/smtlib_pcfg.json")
- `--secondary`: Optional path to a secondary PCFG JSON file for comparison
- `--sample-size`: Number of programs used to generate the PCFG(s) (default: 5)
- `--output`: Optional path to save analysis results as JSON

## Advanced Measures

### Information Theory
- Shannon entropy (bits of uncertainty)
- Perplexity (exponential of entropy)
- Rényi entropy (generalized entropy for α=0.5, 2, ∞)
- Cross-entropy between grammars
- KL divergence and Jensen-Shannon divergence
- Information radius and mutual information

### Statistical Analysis
- Confidence intervals using Wilson score method
- Rule probability distributions and fitting
- Spectral analysis of the dependency graph
- Structural significance tests
- Grammar complexity metrics

"""

import json
import math
import argparse
import numpy as np
import os
from collections import defaultdict, Counter
import scipy.stats as stats
import statsmodels.stats.proportion as prop
from scipy.spatial.distance import jensenshannon
from scipy.special import rel_entr

class PCFGUncertaintyAnalyzer:
    """
    Advanced analyzer for uncertainty in Probabilistic Context-Free Grammars
    derived from LLM-generated programs.
    """
    
    def __init__(self, pcfg_file, sample_size=5, secondary_pcfg_file=None):
        """
        Initialize with a PCFG JSON file and optional secondary file for comparison.
        
        Args:
            pcfg_file (str): Path to the primary PCFG JSON file
            sample_size (int): Number of programs used to induce the grammar
            secondary_pcfg_file (str, optional): Path to a secondary PCFG for comparison
        """
        self.pcfg = self._load_pcfg(pcfg_file)
        self.sample_size = sample_size
        self.rules_by_lhs = self._group_rules_by_lhs()
        
        # Load secondary PCFG if provided
        self.secondary_pcfg = None
        self.secondary_rules_by_lhs = None
        if secondary_pcfg_file:
            self.secondary_pcfg = self._load_pcfg(secondary_pcfg_file)
            self.secondary_rules_by_lhs = self._group_rules_by_lhs(self.secondary_pcfg)
            
        # Cache for computed values
        self._cache = {}
            
    def _load_pcfg(self, pcfg_file):
        """Load the PCFG from a JSON file"""
        with open(pcfg_file, 'r') as f:
            data = json.load(f)
            # The first script exports the rules under a "rules" key
            if "rules" in data:
                return data["rules"]
            return data  # Fallback to the whole data if "rules" key doesn't exist
            
    def _group_rules_by_lhs(self, pcfg=None):
        """Group rules by their left-hand side (non-terminal)"""
        if pcfg is None:
            pcfg = self.pcfg
            
        rules_by_lhs = defaultdict(list)
        for rule_key, rule_data in pcfg.items():
            lhs = rule_data['lhs']
            rhs = tuple(rule_data['rhs'])
            probability = rule_data['probability']
            rules_by_lhs[lhs].append((rhs, probability))
        return rules_by_lhs
    
    def calculate_rule_entropies(self, rules_by_lhs=None):
        """
        Calculate entropy for each non-terminal's production rules.
        
        Entropy measures the uncertainty in the probability distribution of rules.
        Higher entropy means more uncertainty in which rule will be selected.
        
        Args:
            rules_by_lhs (dict, optional): Rules grouped by LHS, defaults to primary PCFG
            
        Returns:
            dict: Mapping from non-terminals to their entropy values
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        entropies = {}
        for lhs, rules in rules_by_lhs.items():
            # Extract probabilities
            probabilities = [prob for _, prob in rules]
            # Calculate entropy: -sum(p * log(p))
            entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
            entropies[lhs] = entropy
        
        return entropies
    
    def calculate_renyi_entropy(self, alpha=2.0, rules_by_lhs=None):
        """
        Calculate Rényi entropy of order alpha for each non-terminal.
        
        Rényi entropy is a generalization of Shannon entropy.
        Special cases:
        - alpha = 0: Max-entropy (log of support size)
        - alpha = 1: Shannon entropy
        - alpha = 2: Collision entropy
        - alpha = inf: Min-entropy
        
        Args:
            alpha (float): Order of Rényi entropy
            rules_by_lhs (dict, optional): Rules grouped by LHS
            
        Returns:
            dict: Mapping from non-terminals to their Rényi entropy values
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        renyi_entropies = {}
        
        for lhs, rules in rules_by_lhs.items():
            # Extract probabilities
            probabilities = [prob for _, prob in rules]
            
            # Handle different alpha cases
            if alpha == 1:  # Shannon entropy
                entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
            elif alpha == float('inf'):  # Min-entropy
                if probabilities:
                    entropy = -math.log2(max(probabilities))
                else:
                    entropy = 0
            elif alpha == 0:  # Max-entropy
                entropy = math.log2(len(probabilities))
            else:
                # General case: 1/(1-alpha) * log(sum(p^alpha))
                sum_prob_alpha = sum(p**alpha for p in probabilities if p > 0)
                if sum_prob_alpha > 0:
                    entropy = (1/(1-alpha)) * math.log2(sum_prob_alpha)
                else:
                    entropy = 0
                    
            renyi_entropies[lhs] = entropy
            
        return renyi_entropies
    
    def calculate_grammar_entropy(self, rules_by_lhs=None):
        """
        Calculate overall grammar entropy based on weighted average of non-terminal entropies.
        
        Returns:
            float: Overall grammar entropy
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            entropies = self.calculate_rule_entropies()
        else:
            entropies = self.calculate_rule_entropies(rules_by_lhs)
        
        # Weight each non-terminal's entropy by its frequency of occurrence
        nt_counts = self._estimate_nonterminal_frequencies(rules_by_lhs)
        total_count = sum(nt_counts.values())
        
        if total_count == 0:
            return sum(entropies.values()) / len(entropies)  # Simple average if no frequency data
        
        weighted_entropy = sum(entropies[nt] * (nt_counts.get(nt, 0) / total_count) 
                               for nt in entropies.keys())
        return weighted_entropy
    
        # I have made this negative
        
    def _estimate_nonterminal_frequencies(self, rules_by_lhs=None):
        """
        Estimate the frequency of each non-terminal in derivations.
        This is an approximation based on rule structure.
        
        Returns:
            dict: Mapping from non-terminals to estimated frequencies
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        # Start with script as the root
        counts = {'script': 1}
        queue = ['script']
        
        # Process each non-terminal and its derivations
        processed = set()
        while queue:
            current = queue.pop(0)
            if current in processed:
                continue
                
            processed.add(current)
            
            # Skip if it's a terminal or not in our grammar
            if current not in rules_by_lhs:
                continue
            
            # For each rule from this non-terminal
            for rhs, prob in rules_by_lhs[current]:
                # Count occurrences of non-terminals in the RHS
                for symbol in rhs:
                    if symbol in rules_by_lhs:  # If it's a non-terminal
                        counts[symbol] = counts.get(symbol, 0) + prob * counts[current]
                        queue.append(symbol)
        
        return counts
    
    def calculate_rule_confidence_intervals(self, confidence=0.95, rules_by_lhs=None, sample_size=None):
        """
        Calculate confidence intervals for rule probabilities.
        
        Args:
            confidence (float): Confidence level (default: 0.95 for 95% CI)
            rules_by_lhs (dict, optional): Rules grouped by LHS
            sample_size (int, optional): Override sample size for calculation
            
        Returns:
            dict: Mapping from rule keys to their confidence intervals
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        if sample_size is None:
            sample_size = self.sample_size
            
        confidence_intervals = {}
        
        for lhs, rules in rules_by_lhs.items():
            # For each rule with this LHS
            for i, (rhs, prob) in enumerate(rules):
                # Create a rule identifier
                rule_key = f"{lhs}->{','.join(rhs)}"
                
                # Estimate the count of this rule based on probability
                if len(rules) == 1:
                    # If there's only one rule for this LHS, we're certain about it
                    confidence_intervals[rule_key] = (1.0, 1.0)
                    continue
                    
                # Estimate the expected count based on probability
                expected_count = int(prob * sample_size + 0.5)  # Round to nearest int
                
                # Calculate Wilson score interval (works better for small sample sizes)
                interval = prop.proportion_confint(
                    expected_count, sample_size, 
                    alpha=1-confidence, method='wilson'
                )
                
                confidence_intervals[rule_key] = interval
                
        return confidence_intervals
    
    def calculate_critical_spectral_radius(self, rules_by_lhs=None):
        """
        Calculate the spectral radius of the dependency graph Jacobian matrix.
        
        This helps assess the computational complexity of working with this grammar.
        A value < 1 ensures tractable computations.
        
        Returns:
            float: Estimated spectral radius
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        # Build the dependency graph as an adjacency matrix
        non_terminals = list(rules_by_lhs.keys())
        n = len(non_terminals)
        nt_index = {nt: i for i, nt in enumerate(non_terminals)}
        
        # Create the Jacobian matrix B(1)
        B = np.zeros((n, n))
        
        for i, nt in enumerate(non_terminals):
            rules = rules_by_lhs[nt]
            for rhs, prob in rules:
                # Count non-terminals in RHS
                for symbol in rhs:
                    if symbol in nt_index:  # If it's a non-terminal
                        j = nt_index[symbol]
                        # Increment by probability (assuming polynomial of degree 1)
                        B[j, i] += prob
        
        # Calculate spectral radius (largest eigenvalue)
        eigenvalues = np.linalg.eigvals(B)
        spectral_radius = max(abs(eigenvalues))
        
        return spectral_radius
    
    def calculate_kullback_leibler_divergence(self, prior_probs=None, rules_by_lhs=None):
        """
        Estimate KL divergence between the empirical distribution and a prior.
        
        If no prior is provided, uses a uniform distribution as the prior.
        
        Args:
            prior_probs (dict, optional): Prior probabilities for rules
            rules_by_lhs (dict, optional): Rules grouped by LHS
            
        Returns:
            float: Estimated KL divergence
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        kl_divergence = 0.0
        
        for lhs, rules in rules_by_lhs.items():
            # Number of rules for this non-terminal
            n_rules = len(rules)
            
            # If no prior provided, use uniform distribution
            if prior_probs is None or lhs not in prior_probs:
                prior_rule_probs = [1.0 / n_rules] * n_rules
            else:
                prior_rule_probs = [prior_probs[lhs].get(rhs, 1.0/n_rules) 
                                   for rhs, _ in rules]
            
            # Current rule probabilities
            current_probs = [prob for _, prob in rules]
            
            # Calculate KL divergence component for this non-terminal
            for p, q in zip(current_probs, prior_rule_probs):
                if p > 0 and q > 0:
                    kl_divergence += p * math.log2(p / q)
        
        return kl_divergence
    
    def calculate_jensen_shannon_divergence(self, other_pcfg_rules=None):
        """
        Calculate Jensen-Shannon divergence between two PCFGs.
        
        JS divergence is a symmetric version of KL divergence.
        
        Args:
            other_pcfg_rules (dict, optional): Rules by LHS from another PCFG
            
        Returns:
            dict: JS divergence for each non-terminal
        """
        if other_pcfg_rules is None:
            if self.secondary_rules_by_lhs is None:
                raise ValueError("No secondary PCFG provided for comparison")
            other_pcfg_rules = self.secondary_rules_by_lhs
            
        js_divergences = {}
        
        # Process non-terminals in both grammars
        all_nts = set(self.rules_by_lhs.keys()) | set(other_pcfg_rules.keys())
        
        for nt in all_nts:
            # Get rules for this non-terminal in both grammars
            rules1 = self.rules_by_lhs.get(nt, [])
            rules2 = other_pcfg_rules.get(nt, [])
            
            # If the non-terminal is not in one of the grammars, JS divergence is 1.0 (maximum)
            if not rules1 or not rules2:
                js_divergences[nt] = 1.0
                continue
                
            # Create probability distributions for rules
            # For each RHS, store its probability
            dist1 = {}
            for rhs, prob in rules1:
                dist1[rhs] = prob
                
            dist2 = {}
            for rhs, prob in rules2:
                dist2[rhs] = prob
                
            # Combine all possible RHS
            all_rhs = set(dist1.keys()) | set(dist2.keys())
            
            # Create probability arrays with zero padding for missing rules
            p1 = np.array([dist1.get(rhs, 0.0) for rhs in all_rhs])
            p2 = np.array([dist2.get(rhs, 0.0) for rhs in all_rhs])
            
            # Normalize if needed
            if np.sum(p1) > 0:
                p1 = p1 / np.sum(p1)
            if np.sum(p2) > 0:
                p2 = p2 / np.sum(p2)
            
            # Calculate JS divergence
            js_div = jensenshannon(p1, p2, base=2)
            js_divergences[nt] = js_div
            
        return js_divergences
        
    def calculate_rule_distribution_metrics(self):
        """
        Calculate distribution metrics for rule probabilities.
        
        Returns:
            dict: Metrics for rule probability distributions
        """
        metrics = {}
        
        # Flatten all rule probabilities
        all_probs = []
        for lhs, rules in self.rules_by_lhs.items():
            probs = [prob for _, prob in rules]
            all_probs.extend(probs)
            
        if not all_probs:
            return {"count": 0}
            
        # Calculate basic statistics
        metrics["count"] = len(all_probs)
        metrics["min"] = min(all_probs)
        metrics["max"] = max(all_probs)
        metrics["mean"] = np.mean(all_probs)
        metrics["median"] = np.median(all_probs)
        metrics["std"] = np.std(all_probs)
        metrics["skew"] = stats.skew(all_probs)
        metrics["kurtosis"] = stats.kurtosis(all_probs)
        
        # Check if distribution follows power law using a safer approach
        # Log-transform data
        log_probs = [math.log10(p) for p in all_probs if p > 0]
        if log_probs:
            try:
                # Try fitting a power law distribution (using pareto)
                # This is a safer choice than powerlognorm which has more parameters
                shape, loc, scale = stats.pareto.fit(all_probs)
                metrics["power_law_shape"] = shape
                
                # Test goodness of fit with Kolmogorov-Smirnov test
                ks_statistic, ks_pvalue = stats.kstest(
                    all_probs, 
                    lambda x: stats.pareto.cdf(x, shape, loc=loc, scale=scale)
                )
                metrics["power_law_ks_statistic"] = ks_statistic
                metrics["power_law_ks_pvalue"] = ks_pvalue
            except Exception as e:
                # If fitting fails, log the error but continue
                metrics["power_law_fit_error"] = str(e)
                
        return metrics
        
    def compare_grammars(self):
        """
        Comprehensive comparison between primary and secondary PCFGs.
        
        Returns:
            dict: Detailed grammar comparison metrics
        """
        if self.secondary_rules_by_lhs is None:
            raise ValueError("No secondary PCFG provided for comparison")
            
        comparison = {}
        
        # Basic structure comparison
        primary_nts = set(self.rules_by_lhs.keys())
        secondary_nts = set(self.secondary_rules_by_lhs.keys())
        
        comparison["common_nonterminals"] = list(primary_nts & secondary_nts)
        comparison["primary_only_nonterminals"] = list(primary_nts - secondary_nts)
        comparison["secondary_only_nonterminals"] = list(secondary_nts - primary_nts)
        
        # Calculate JS divergence between distributions
        js_divergences = self.calculate_jensen_shannon_divergence()
        comparison["js_divergence_by_nt"] = js_divergences
        comparison["overall_js_divergence"] = sum(js_divergences.values()) / len(js_divergences) if js_divergences else 0
        
        # Compare rule sets
        primary_rules = set()
        secondary_rules = set()
        
        for lhs, rules in self.rules_by_lhs.items():
            for rhs, _ in rules:
                primary_rules.add((lhs, rhs))
                
        for lhs, rules in self.secondary_rules_by_lhs.items():
            for rhs, _ in rules:
                secondary_rules.add((lhs, rhs))
                
        comparison["common_rules"] = len(primary_rules & secondary_rules)
        comparison["primary_only_rules"] = len(primary_rules - secondary_rules)
        comparison["secondary_only_rules"] = len(secondary_rules - primary_rules)
        
        # Calculate Jaccard similarity for rule sets
        jaccard = len(primary_rules & secondary_rules) / len(primary_rules | secondary_rules) if primary_rules or secondary_rules else 0
        comparison["rule_set_jaccard_similarity"] = jaccard
        
        # Calculate entropy difference
        primary_entropy = self.calculate_grammar_entropy()
        secondary_entropy = self.calculate_grammar_entropy(self.secondary_rules_by_lhs)
        comparison["primary_entropy"] = primary_entropy
        comparison["secondary_entropy"] = secondary_entropy
        comparison["entropy_difference"] = primary_entropy - secondary_entropy
        
        # Calculate cross-entropy
        cross_entropy = self._calculate_cross_entropy()
        comparison["cross_entropy"] = cross_entropy
        
        return comparison
    
    def _calculate_cross_entropy(self):
        """
        Calculate cross-entropy from primary to secondary grammar.
        
        This measures how well the primary grammar predicts the secondary grammar.
        
        Returns:
            float: Cross-entropy value
        """
        if self.secondary_rules_by_lhs is None:
            raise ValueError("No secondary PCFG provided")
            
        cross_entropy = 0.0
        weight_sum = 0.0
        
        # For each non-terminal in secondary grammar
        for lhs, sec_rules in self.secondary_rules_by_lhs.items():
            # Get corresponding rules in primary grammar
            prim_rules = self.rules_by_lhs.get(lhs, [])
            
            if not prim_rules:
                # If the non-terminal doesn't exist in primary, assign high cross-entropy
                nt_cross_entropy = 10.0  # Arbitrary high value
            else:
                # Create probability map for primary grammar
                prim_probs = {rhs: prob for rhs, prob in prim_rules}
                
                # Calculate cross-entropy: -sum(q(x) * log(p(x)))
                nt_cross_entropy = 0.0
                for rhs, q_prob in sec_rules:
                    # If rhs exists in primary, use its probability, otherwise use a small value
                    p_prob = prim_probs.get(rhs, 1e-10)
                    nt_cross_entropy -= q_prob * math.log2(p_prob)
                    
            # Weight by frequency in secondary grammar
            weight = sum(prob for _, prob in sec_rules)
            cross_entropy += nt_cross_entropy * weight
            weight_sum += weight
            
        return cross_entropy / weight_sum if weight_sum > 0 else float('inf')
    
    def calculate_perplexity(self, rules_by_lhs=None):
        """
        Calculate grammar perplexity - a measure of how well the model predicts the sample.
        
        Lower perplexity indicates better predictive performance.
        
        Returns:
            float: Estimated perplexity
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        # Entropy-based approximation of perplexity
        entropies = self.calculate_rule_entropies(rules_by_lhs)
        avg_entropy = sum(entropies.values()) / len(entropies) if entropies else 0
        perplexity = 2 ** avg_entropy
        
        return perplexity
    
    def calculate_grammar_complexity(self, rules_by_lhs=None):
        """
        Calculate multiple grammar complexity metrics.
        
        Returns:
            dict: Grammar complexity metrics
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        complexity = {}
        
        # Count number of non-terminals and rules
        complexity["num_nonterminals"] = len(rules_by_lhs)
        
        total_rules = sum(len(rules) for rules in rules_by_lhs.values())
        complexity["num_rules"] = total_rules
        
        # Average number of rules per non-terminal
        complexity["avg_rules_per_nt"] = total_rules / len(rules_by_lhs) if rules_by_lhs else 0
        
        # Calculate average RHS length
        total_rhs_length = 0
        total_rhs_count = 0
        
        for lhs, rules in rules_by_lhs.items():
            for rhs, _ in rules:
                total_rhs_length += len(rhs)
                total_rhs_count += 1
                
        complexity["avg_rhs_length"] = total_rhs_length / total_rhs_count if total_rhs_count > 0 else 0
        
        # Calculate branching factor
        max_branching = 0
        for lhs, rules in rules_by_lhs.items():
            branching = len(rules)
            max_branching = max(max_branching, branching)
            
        complexity["max_branching_factor"] = max_branching
        
        # Check for left-recursion and right-recursion
        left_recursive = False
        right_recursive = False
        
        for lhs, rules in rules_by_lhs.items():
            for rhs, _ in rules:
                if rhs and rhs[0] == lhs:
                    left_recursive = True
                if rhs and rhs[-1] == lhs:
                    right_recursive = True
                    
        complexity["has_left_recursion"] = left_recursive
        complexity["has_right_recursion"] = right_recursive
        
        # Spectral radius (as a complexity measure)
        complexity["spectral_radius"] = self.calculate_critical_spectral_radius(rules_by_lhs)
        
        return complexity
        
    def calculate_nsui(self, rules_by_lhs=None):
        """
        Calculate the Normalized Structural Uncertainty Index (NSUI).
        
        This novel metric combines grammar entropy and spectral radius to provide
        a comprehensive measure of uncertainty in PCFGs that accounts for both
        rule selection uncertainty and structural complexity.
        
        Args:
            rules_by_lhs (dict, optional): Rules grouped by LHS, defaults to primary PCFG
                
        Returns:
            float: NSUI value between 0 and 1
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        # Calculate actual grammar entropy
        grammar_entropy = self.calculate_grammar_entropy(rules_by_lhs)
        
        # Calculate maximum possible entropy if all rules had uniform probability
        max_entropy = 0.0
        nt_weights = self._estimate_nonterminal_frequencies(rules_by_lhs)
        total_weight = sum(nt_weights.values())
        
        if total_weight > 0:
            for nt, weight in nt_weights.items():
                if nt in rules_by_lhs:
                    # Maximum entropy for this non-terminal would be log2(number of rules)
                    rules_count = len(rules_by_lhs[nt])
                    if rules_count > 1:  # Only non-terminals with multiple rules contribute to max entropy
                        max_entropy += (weight / total_weight) * math.log2(rules_count)
        else:
            # Fallback if weights can't be calculated
            for nt, rules in rules_by_lhs.items():
                rules_count = len(rules)
                if rules_count > 1:
                    max_entropy += math.log2(rules_count) / len(rules_by_lhs)
        
        # If max_entropy is 0, the grammar has no uncertainty
        if max_entropy == 0:
            return 0.0
            
        # Calculate entropy ratio (normalized entropy)
        entropy_ratio = grammar_entropy / max_entropy
        
        # Calculate spectral radius
        spectral_radius = self.calculate_critical_spectral_radius(rules_by_lhs)
        
        # Calculate spectral factor
        spectral_factor = spectral_radius / (1 + spectral_radius)
        
        # Calculate NSUI
        nsui = entropy_ratio * spectral_factor
        
        return nsui

    def calculate_nsui_components(self, rules_by_lhs=None):
        """
        Calculate the components of the NSUI for detailed analysis.
        
        Args:
            rules_by_lhs (dict, optional): Rules grouped by LHS
                
        Returns:
            dict: Components of the NSUI calculation
        """
        if rules_by_lhs is None:
            rules_by_lhs = self.rules_by_lhs
            
        # Calculate all components
        grammar_entropy = self.calculate_grammar_entropy(rules_by_lhs)
        
        # Calculate maximum possible entropy
        max_entropy = 0.0
        nt_weights = self._estimate_nonterminal_frequencies(rules_by_lhs)
        total_weight = sum(nt_weights.values())
        
        if total_weight > 0:
            for nt, weight in nt_weights.items():
                if nt in rules_by_lhs:
                    rules_count = len(rules_by_lhs[nt])
                    if rules_count > 1:
                        max_entropy += (weight / total_weight) * math.log2(rules_count)
        else:
            for nt, rules in rules_by_lhs.items():
                rules_count = len(rules)
                if rules_count > 1:
                    max_entropy += math.log2(rules_count) / len(rules_by_lhs)
        
        entropy_ratio = grammar_entropy / max_entropy if max_entropy > 0 else 0.0
        
        spectral_radius = self.calculate_critical_spectral_radius(rules_by_lhs)
        spectral_factor = spectral_radius / (1 + spectral_radius)
        
        nsui = entropy_ratio * spectral_factor
        
        return {
            "grammar_entropy": grammar_entropy,
            "max_entropy": max_entropy,
            "entropy_ratio": entropy_ratio,
            "spectral_radius": spectral_radius,
            "spectral_factor": spectral_factor,
            "nsui": nsui
        }

    def print_nsui_analysis(self):
        """Print NSUI analysis results"""
        nsui_components = self.calculate_nsui_components()
        
        print("\n----- Normalized Structural Uncertainty Index (NSUI) -----")
        print(f"Grammar entropy: {nsui_components['grammar_entropy']:.4f} bits")
        print(f"Maximum possible entropy: {nsui_components['max_entropy']:.4f} bits")
        print(f"Entropy ratio: {nsui_components['entropy_ratio']:.4f}")
        print(f"Spectral radius: {nsui_components['spectral_radius']:.4f}")
        print(f"Spectral factor: {nsui_components['spectral_factor']:.4f}")
        print(f"NSUI: {nsui_components['nsui']:.4f}")
        
        # Interpret the NSUI value
        if nsui_components['nsui'] < 0.1:
            interpretation = "VERY LOW - Highly consistent program generation with simple structure"
        elif nsui_components['nsui'] < 0.2:
            interpretation = "LOW - Consistent program generation with relatively simple structure"
        elif nsui_components['nsui'] < 0.3:
            interpretation = "MODERATE - Some variability in program generation with moderate structural complexity"
        elif nsui_components['nsui'] < 0.4:
            interpretation = "HIGH - Significant variability with complex structure"
        else:
            interpretation = "VERY HIGH - Extremely variable program generation with highly complex structure"
            
        print(f"Interpretation: {interpretation}")
        
        # If secondary grammar exists, print comparison
        if self.secondary_rules_by_lhs is not None:
            secondary_nsui = self.calculate_nsui(self.secondary_rules_by_lhs)
            print(f"\nSecondary grammar NSUI: {secondary_nsui:.4f}")
            print(f"NSUI difference: {nsui_components['nsui'] - secondary_nsui:.4f}")
            
      
    def print_nsui_analysis(self):
        """Print NSUI analysis results"""
        nsui_components = self.calculate_nsui_components()
        
        print("\n----- Normalized Structural Uncertainty Index (NSUI) -----")
        print(f"Grammar entropy: {nsui_components['grammar_entropy']:.4f} bits")
        print(f"Maximum possible entropy: {nsui_components['max_entropy']:.4f} bits")
        print(f"Entropy ratio: {nsui_components['entropy_ratio']:.4f}")
        print(f"Spectral radius: {nsui_components['spectral_radius']:.4f}")
        print(f"Spectral factor: {nsui_components['spectral_factor']:.4f}")
        print(f"NSUI: {nsui_components['nsui']:.4f}")
        
        # Interpret the NSUI value
        if nsui_components['nsui'] < 0.1:
            interpretation = "VERY LOW - Highly consistent program generation with simple structure"
        elif nsui_components['nsui'] < 0.2:
            interpretation = "LOW - Consistent program generation with relatively simple structure"
        elif nsui_components['nsui'] < 0.3:
            interpretation = "MODERATE - Some variability in program generation with moderate structural complexity"
        elif nsui_components['nsui'] < 0.4:
            interpretation = "HIGH - Significant variability with complex structure"
        else:
            interpretation = "VERY HIGH - Extremely variable program generation with highly complex structure"
            
        print(f"Interpretation: {interpretation}")
        
        # If secondary grammar exists, print comparison
        if self.secondary_rules_by_lhs is not None:
            secondary_nsui = self.calculate_nsui(self.secondary_rules_by_lhs)
            print(f"\nSecondary grammar NSUI: {secondary_nsui:.4f}")
            print(f"NSUI difference: {nsui_components['nsui'] - secondary_nsui:.4f}")
            
                     
    def print_full_analysis(self):
        """Print a complete analysis of the PCFG uncertainty measures"""
        print("\n====== SMT-LIB PCFG Uncertainty Analysis ======")
        print(f"Based on {self.sample_size} LLM-generated programs")
        
        print("\n----- Grammar Structure and Complexity -----")
        complexity = self.calculate_grammar_complexity()
        print(f"Number of non-terminals: {complexity['num_nonterminals']}")
        print(f"Total number of rules: {complexity['num_rules']}")
        print(f"Average rules per non-terminal: {complexity['avg_rules_per_nt']:.2f}")
        print(f"Average RHS length: {complexity['avg_rhs_length']:.2f}")
        print(f"Maximum branching factor: {complexity['max_branching_factor']}")
        print(f"Has left recursion: {complexity['has_left_recursion']}")
        print(f"Has right recursion: {complexity['has_right_recursion']}")
        
        print("\n----- Information Theory Analysis -----")
        
        # Shannon Entropy
        entropies = self.calculate_rule_entropies()
        print("Shannon Entropy by non-terminal (higher = more uncertain):")
        for nt, entropy in sorted(entropies.items(), key=lambda x: -x[1])[:5]:  # Top 5
            rules = self.rules_by_lhs[nt]
            if len(rules) > 1:  # Only show non-terminals with multiple rules
                print(f"  {nt}: {entropy:.4f} bits ({len(rules)} rules)")
                
        # Rényi Entropy
        print("\nRényi Entropy (α=2, collision entropy):")
        renyi_entropies = self.calculate_renyi_entropy(alpha=2)
        for nt, entropy in sorted(renyi_entropies.items(), key=lambda x: -x[1])[:3]:  # Top 3
            if entropy > 0:
                print(f"  {nt}: {entropy:.4f} bits")
                
        # Overall metrics
        grammar_entropy = self.calculate_grammar_entropy()
        print(f"\nOverall grammar entropy: {grammar_entropy:.4f} bits")
        
        perplexity = self.calculate_perplexity()
        print(f"Grammar perplexity: {perplexity:.4f}")
        
        # Divergence from uniform
        kl = self.calculate_kullback_leibler_divergence()
        print(f"KL divergence from uniform prior: {kl:.4f} bits")
        
        print("\n----- Statistical Analysis -----")
        # Distribution metrics
        metrics = self.calculate_rule_distribution_metrics()
        print("Rule probability distribution statistics:")
        print(f"  Mean probability: {metrics.get('mean', 0):.4f}")
        print(f"  Standard deviation: {metrics.get('std', 0):.4f}")
        print(f"  Skewness: {metrics.get('skew', 0):.4f}")
        print(f"  Kurtosis: {metrics.get('kurtosis', 0):.4f}")
        
        # Power law fit
        if 'power_law_alpha' in metrics:
            print(f"\nPower law fit (Zipf-like distribution):")
            print(f"  Alpha parameter: {metrics['power_law_alpha']:.4f}")
            print(f"  Goodness of fit p-value: {metrics['power_law_ks_pvalue']:.4f}")
            print(f"  {'Follows power law' if metrics['power_law_ks_pvalue'] > 0.05 else 'Does not follow power law'}")
        
        # Get confidence intervals for most uncertain rules
        ci = self.calculate_rule_confidence_intervals()
        uncertain_rules = sorted(ci.items(), key=lambda x: x[1][1] - x[1][0], reverse=True)
        print("\nConfidence intervals for most uncertain rules (95% CI):")
        for rule, interval in uncertain_rules[:5]:
            print(f"  {rule}: [{interval[0]:.4f}, {interval[1]:.4f}]")
        
        spectral_radius = self.calculate_critical_spectral_radius()
        print(f"\nSpectral radius: {spectral_radius:.4f}")
        if spectral_radius < 1:
            print("  Grammar is non-critical (guarantees efficient computation)")
        else:
            print("  Grammar is critical (computation may be challenging)")
        
        # Comparative analysis if secondary PCFG provided
        if self.secondary_rules_by_lhs is not None:
            print("\n----- Grammar Comparison -----")
            comparison = self.compare_grammars()
            
            # Print comparison highlights
            print(f"Common non-terminals: {len(comparison['common_nonterminals'])}")
            print(f"Rules unique to primary: {comparison['primary_only_rules']}")
            print(f"Rules unique to secondary: {comparison['secondary_only_rules']}")
            print(f"Rule set Jaccard similarity: {comparison['rule_set_jaccard_similarity']:.4f}")
            print(f"Overall Jensen-Shannon divergence: {comparison['overall_js_divergence']:.4f}")
            print(f"Cross-entropy: {comparison['cross_entropy']:.4f}")
            
            # Non-terminals with highest divergence
            print("\nNon-terminals with highest divergence:")
            js_by_nt = comparison['js_divergence_by_nt']
            for nt, js in sorted(js_by_nt.items(), key=lambda x: -x[1])[:3]:
                print(f"  {nt}: {js:.4f}")
                
        # Print NSUI analysis
        self.print_nsui_analysis()
        
        print("\n----- Uncertainty Summary -----")
        # Determine overall uncertainty level
        if grammar_entropy < 1.0:
            uncertainty = "LOW"
        elif grammar_entropy < 2.0:
            uncertainty = "MODERATE"
        else:
            uncertainty = "HIGH"
            
        print(f"Overall uncertainty assessment: {uncertainty}")
        
        # Most uncertain non-terminals
        sorted_ent = sorted(entropies.items(), key=lambda x: -x[1])
        if sorted_ent:
            print(f"Most uncertain non-terminal: {sorted_ent[0][0]} ({sorted_ent[0][1]:.4f} bits)")
        


          
    def save_analysis_to_json(self, output_file):
        """
        Save complete analysis results to a JSON file.
        
        Args:
            output_file (str): Path to save the JSON output
        """
        # Gather all analysis data
        analysis = {
            "metadata": {
                "sample_size": self.sample_size,
                "has_secondary_pcfg": self.secondary_rules_by_lhs is not None
            },
            "grammar_structure": self.calculate_grammar_complexity(),
            "information_theory": {
                "shannon_entropy_by_nt": self.calculate_rule_entropies(),
                "renyi_entropy_order2_by_nt": self.calculate_renyi_entropy(alpha=2),
                "renyi_entropy_order05_by_nt": self.calculate_renyi_entropy(alpha=0.5),
                "grammar_entropy": self.calculate_grammar_entropy(),
                "perplexity": self.calculate_perplexity(),
                "kl_divergence_from_uniform": self.calculate_kullback_leibler_divergence(),
                "nsui" : self.calculate_nsui(),
                "nsui_components" : self.calculate_nsui_components()

            },
            "statistical_analysis": {
                "rule_distribution_metrics": self.calculate_rule_distribution_metrics(),
                "confidence_intervals": self.calculate_rule_confidence_intervals(),
                "spectral_radius": self.calculate_critical_spectral_radius()
            }
        }
        
        # Add comparison if secondary PCFG provided
        if self.secondary_rules_by_lhs is not None:
            analysis["grammar_comparison"] = self.compare_grammars()
            secondary_nsui = self.calculate_nsui(self.secondary_rules_by_lhs)
            analysis["grammar_comparison"]["secondary_nsui"] = secondary_nsui
            analysis["grammar_comparison"]["nsui_difference"] = analysis["information_theory"]["nsui"] - secondary_nsui
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
            
        print(f"\nAnalysis saved to {output_file}")

def main():
    """Main function to run the analysis"""
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Advanced PCFG Uncertainty Analyzer")
    parser.add_argument("--primary", default="logs/smtlib_pcfg.json", 
                      help="Path to primary PCFG JSON file")
    parser.add_argument("--secondary", default=None,
                      help="Optional path to secondary PCFG JSON file for comparison")
    parser.add_argument("--sample-size", type=int, default=5,
                      help="Number of programs used to generate the PCFG")
    parser.add_argument("--output", default=None,
                      help="Optional path to save analysis results as JSON")
    
    args = parser.parse_args()
    
    try:
        # Check if primary file exists
        if not os.path.exists(args.primary):
            print(f"Error: Primary PCFG file {args.primary} not found.")
            return
            
        # Check if secondary file exists if provided
        if args.secondary and not os.path.exists(args.secondary):
            print(f"Error: Secondary PCFG file {args.secondary} not found.")
            return
        
        # Create analyzer
        analyzer = PCFGUncertaintyAnalyzer(
            args.primary, 
            sample_size=args.sample_size,
            secondary_pcfg_file=args.secondary
        )
        
        # Run and print full analysis
        # analyzer.print_full_analysis()
        
        # Save analysis if output file specified
        if args.output:
            analyzer.save_analysis_to_json(args.output)
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()