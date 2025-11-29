"""Uncertainty analysis pipeline."""

import pandas as pd

from experiments.processing import UncertaintyProcessor, ResultsAnalyzer
from experiments.metrics import MetricsCalculator, CombinedEstimator


def run_uncertainty_analysis(smt_dir, results_json, cache_dir="uncertainty_cache", use_cache=True):
    """Run comprehensive uncertainty analysis with component-level evaluation."""
    print("Processing SMT files...")
    processor = UncertaintyProcessor(base_dir=smt_dir, cache_dir=cache_dir)
    uncertainty_metrics = processor.process_all_directories(use_cache=use_cache)

    print("Analyzing results...")
    analyzer = ResultsAnalyzer()
    results_df = analyzer.analyze_json(results_json)

    print("Combining results...")
    combined_df = analyzer.combine_results(results_df, uncertainty_metrics)

    # Create estimators for ground truth prediction
    print("\n== Predicting SMT Correctness (Ground Truth) ==")
    estimator = CombinedEstimator()
    gt_df, gt_directions = estimator.create_all_estimators(combined_df, 'smt_correct')

    # Evaluate individual components for ground truth
    print("\n=== Component-level Metrics for Ground Truth Prediction ===")
    metrics_calc = MetricsCalculator()
    component_results = metrics_calc.evaluate_individual_metrics(gt_df, 'smt_correct')
    categorized_results = metrics_calc.categorize_metrics(component_results)

    # Print combined results as TSV
    all_results = []
    for category, results in categorized_results.items():
        all_results.append(results)
    combined_results = pd.concat(all_results, ignore_index=True)
    print("\n=== Ground Truth Prediction Results (TSV) ===")
    print(combined_results.to_csv(sep='\t', index=False, float_format="%.4f"))

    # Create estimators for text majority match
    print("\n== Predicting SMT Match with Text Majority ==")
    text_df, text_directions = estimator.create_all_estimators(gt_df, 'smt_matches_text')

    # Evaluate individual components for text majority
    print("\n=== Component-level Metrics for Text Majority Match ===")
    component_results_text = metrics_calc.evaluate_individual_metrics(text_df, 'smt_matches_text')
    categorized_results_text = metrics_calc.categorize_metrics(component_results_text)

    all_results = []
    for category, results in categorized_results_text.items():
        all_results.append(results)
    combined_results = pd.concat(all_results, ignore_index=True)
    print("\n=== Text Majority Match Results (TSV) ===")
    print(combined_results.to_csv(sep='\t', index=False, float_format="%.4f"))

    return {
        'dataframe': text_df,
        'ground_truth_component_results': component_results,
        'text_majority_component_results': component_results_text,
    }
