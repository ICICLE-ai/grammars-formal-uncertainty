"""Uncertainty metrics extraction from SMT programs."""

import os
import json
import pandas as pd
from tqdm.auto import tqdm

from grammar_uncertainty import GrammarAnalyzer
from grammar_uncertainty.core.uncertainty import PCFGUncertaintyAnalyzer
from grammar_uncertainty.pcfg import export_pcfg_json


class UncertaintyProcessor:
    """Process SMT files and extract uncertainty metrics with caching."""

    def __init__(self, base_dir=None, cache_dir="uncertainty_cache"):
        self.base_dir = str(base_dir) if base_dir is not None else None
        self.cache_dir = cache_dir
        self.uncertainty_files = {}
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_path(self, base_path):
        """Get cache file path based on input path."""
        base_path_str = str(base_path) if not isinstance(base_path, str) else base_path
        parts = base_path_str.rstrip('/').split('/')
        key_parts = parts[-3:] if len(parts) >= 3 else parts
        cache_key = '_'.join(key_parts)
        return os.path.join(self.cache_dir, f"{cache_key}_metrics.json")

    def process_smt_directory(self, qid_dir):
        """Process SMT2 files for a single QID using GrammarAnalyzer."""
        qid = os.path.basename(qid_dir)

        # 1. Parse with GrammarAnalyzer
        analyzer = GrammarAnalyzer(grammar="smtlib")
        result = analyzer.analyze(qid_dir)

        if not result.success or not result.pcfg:
            print(f"Failed to analyze {qid}: {result.errors}")
            return None

        # 2. Export PCFG to temp file
        pcfg_file = os.path.join(self.cache_dir, f"{qid}_pcfg.json")
        export_pcfg_json(result.pcfg, result.pcfg_stats, pcfg_file)

        # 3. Run PCFGUncertaintyAnalyzer on exported PCFG
        try:
            uncertainty_analyzer = PCFGUncertaintyAnalyzer(
                pcfg_file,
                sample_size=result.programs_parsed
            )

            # 4. Save uncertainty JSON
            output_file = os.path.join(self.cache_dir, f"{qid}_uncertainty.json")
            uncertainty_analyzer.save_analysis_to_json(output_file)
            return output_file
        except Exception as e:
            print(f"Error analyzing uncertainty for {qid}: {e}")
            return None

    def process_all_directories(self, use_cache=True):
        """Process all QID directories with caching."""
        if not self.base_dir:
            raise ValueError("Base directory not set")

        # Check cache
        cache_path = self.get_cache_path(self.base_dir)
        if use_cache and os.path.exists(cache_path):
            print(f"Loading cached results from {cache_path}")
            try:
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                    self.uncertainty_files = cache_data.get('uncertainty_files', {})
                    return cache_data.get('metrics', {})
            except Exception as e:
                print(f"Error loading cache: {e}")

        print("Processing directories...")
        self.uncertainty_files = {}

        qid_dirs = [d for d in os.listdir(self.base_dir)
                    if os.path.isdir(os.path.join(self.base_dir, d))]

        for qid_dir in tqdm(qid_dirs, desc="Processing QIDs"):
            full_path = os.path.join(self.base_dir, qid_dir)
            uncertainty_file = self.process_smt_directory(full_path)
            if uncertainty_file:
                self.uncertainty_files[qid_dir] = uncertainty_file

        # Extract and cache metrics
        metrics = self.extract_uncertainty_metrics()

        # Save to cache
        try:
            cache_data = {
                'uncertainty_files': self.uncertainty_files,
                'metrics': metrics,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
            print(f"Saved results to cache: {cache_path}")
        except Exception as e:
            print(f"Error saving cache: {e}")

        return metrics

    def extract_uncertainty_metrics(self):
        """Extract metrics from JSON files."""
        metrics = {}

        for qid, file_path in tqdm(self.uncertainty_files.items(), desc="Extracting metrics"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                    # Standard metrics
                    metrics[qid] = {
                        # Information theory metrics
                        'grammar_entropy': data['information_theory']['grammar_entropy'],
                        'perplexity': data['information_theory']['perplexity'],
                        'kl_divergence_from_uniform': data['information_theory']['kl_divergence_from_uniform'],
                        'nsui': data['information_theory']['nsui'],

                        # NSUI components
                        'max_entropy': data['information_theory']['nsui_components']['max_entropy'],
                        'entropy_ratio': data['information_theory']['nsui_components']['entropy_ratio'],
                        'spectral_factor': data['information_theory']['nsui_components']['spectral_factor'],

                        # Statistical analysis
                        'spectral_radius': data['statistical_analysis']['spectral_radius']
                    }

                    # Renyi entropy
                    if 'renyi_entropy_order2_by_nt' in data['information_theory']:
                        renyi_values = list(data['information_theory']['renyi_entropy_order2_by_nt'].values())
                        if renyi_values:
                            metrics[qid]['renyi_entropy_order2'] = sum(renyi_values) / len(renyi_values)

                    if 'renyi_entropy_order05_by_nt' in data['information_theory']:
                        renyi_values = list(data['information_theory']['renyi_entropy_order05_by_nt'].values())
                        if renyi_values:
                            metrics[qid]['renyi_entropy_order05'] = sum(renyi_values) / len(renyi_values)

                    # Rule distribution metrics
                    if 'rule_distribution_metrics' in data['statistical_analysis']:
                        rule_metrics = data['statistical_analysis']['rule_distribution_metrics']
                        for key in ['mean', 'std', 'skew', 'kurtosis']:
                            if key in rule_metrics:
                                metrics[qid][f'rule_dist_{key}'] = rule_metrics[key]

                    # Grammar structure metrics
                    if 'grammar_structure' in data:
                        for key in ['num_nonterminals', 'num_rules', 'avg_rules_per_nt',
                                    'avg_rhs_length', 'max_branching_factor']:
                            if key in data['grammar_structure']:
                                metrics[qid][f'grammar_{key}'] = data['grammar_structure'][key]
            except Exception as e:
                print(f"Error extracting metrics from {file_path}: {e}")

        return metrics
