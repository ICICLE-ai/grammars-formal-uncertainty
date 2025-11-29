"""Uncertainty quantification metrics calculator."""

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss

from experiments.metrics.types import MetricDirection


class MetricsCalculator:
    """Calculate uncertainty quantification metrics."""

    def determine_metric_direction(self, df, metric_name, target_col):
        """Determine if metric is positively or negatively correlated with target."""
        if len(df[target_col].unique()) < 2 or df[metric_name].isna().sum() > len(df) * 0.5:
            return MetricDirection.UNKNOWN

        try:
            correlation = df[[metric_name, target_col]].corr().iloc[0, 1]
            if correlation > 0:
                return MetricDirection.POSITIVE
            else:
                return MetricDirection.NEGATIVE
        except:
            if metric_name in ['text_consistency', 'smt_consistency']:
                return MetricDirection.POSITIVE
            else:
                return MetricDirection.NEGATIVE

    def calculate_auroc(self, y_true, y_pred, direction=MetricDirection.POSITIVE):
        """Calculate AUROC score."""
        if len(set(y_true)) < 2:
            return np.nan

        try:
            if direction == MetricDirection.POSITIVE:
                auc = roc_auc_score(y_true, y_pred)
            else:
                auc = roc_auc_score(y_true, -y_pred)

            if auc < 0.5:
                auc = 1 - auc

            return float(auc)
        except Exception as e:
            print(f"Error calculating AUROC: {e}")
            return np.nan

    def calculate_ece(self, y_true, y_pred, n_bins=10):
        """Calculate Expected Calibration Error."""
        if len(set(y_true)) < 2:
            return np.nan

        try:
            bin_edges = np.linspace(0, 1, n_bins + 1)
            bin_indices = np.digitize(y_pred, bin_edges[1:-1])

            bin_counts = np.zeros(n_bins)
            bin_sums = np.zeros(n_bins)
            bin_true_sums = np.zeros(n_bins)

            for i in range(n_bins):
                mask = (bin_indices == i)
                bin_counts[i] = np.sum(mask)
                bin_sums[i] = np.sum(y_pred[mask]) if any(mask) else 0
                bin_true_sums[i] = np.sum(y_true[mask]) if any(mask) else 0

            ece = 0
            for i in range(n_bins):
                if bin_counts[i] > 0:
                    bin_avg_pred = bin_sums[i] / bin_counts[i]
                    bin_avg_true = bin_true_sums[i] / bin_counts[i]
                    bin_weight = bin_counts[i] / len(y_pred)
                    ece += bin_weight * np.abs(bin_avg_pred - bin_avg_true)

            return float(ece)
        except Exception as e:
            print(f"Error calculating ECE: {e}")
            return np.nan

    def calculate_brier_score(self, y_true, y_pred):
        """Calculate Brier score."""
        if len(set(y_true)) < 2:
            return np.nan

        try:
            return float(brier_score_loss(y_true, y_pred))
        except Exception as e:
            print(f"Error calculating Brier score: {e}")
            return np.nan

    def calculate_aurc(self, y_true, confidence_scores):
        """Calculate Area Under Risk-Coverage curve."""
        if len(set(y_true)) < 2:
            return np.nan

        try:
            order = np.argsort(confidence_scores)[::-1]
            y_true_ordered = np.array(y_true)[order]

            coverage_levels = np.linspace(0.1, 1.0, 20)
            risks = []

            for coverage in coverage_levels:
                n_samples = int(len(y_true) * coverage)
                if n_samples == 0:
                    continue

                selected_true = y_true_ordered[:n_samples]
                risk = 1.0 - np.mean(selected_true)
                risks.append(risk)

            if risks:
                return float(np.trapezoid(risks, coverage_levels[:len(risks)]))
            else:
                return np.nan
        except Exception as e:
            print(f"Error calculating AURC: {e}")
            return np.nan

    def calculate_error_vs_abstention(self, y_true, confidence_scores, abstention_levels=None):
        """Calculate error rates at different abstention levels."""
        if abstention_levels is None:
            abstention_levels = np.linspace(0, 0.95, 20)

        order = np.argsort(confidence_scores)[::-1]
        y_true_ordered = np.array(y_true)[order]

        baseline_error = 1.0 - np.mean(y_true)

        results = []
        for abstention in abstention_levels:
            coverage = 1.0 - abstention
            n_samples = int(len(y_true) * coverage)

            if n_samples == 0:
                continue

            selected_true = y_true_ordered[:n_samples]
            error_rate = 1.0 - np.mean(selected_true)
            relative_reduction = (baseline_error - error_rate) / baseline_error if baseline_error > 0 else 0
            absolute_reduction = baseline_error - error_rate

            results.append({
                'abstention_level': abstention,
                'coverage': coverage,
                'error_rate': error_rate,
                'relative_error_reduction': relative_reduction,
                'absolute_error_reduction': absolute_reduction
            })

        return pd.DataFrame(results)

    def find_optimal_abstention(self, error_vs_abstention_df, max_abstention=None,
                                 criterion='relative_improvement_per_abstention'):
        """Find the optimal abstention level based on different criteria."""
        df = error_vs_abstention_df.copy()

        if max_abstention is not None:
            df = df[df['abstention_level'] <= max_abstention]

        if df.empty:
            return None

        if criterion == 'min_error':
            idx = df['error_rate'].idxmin()
        elif criterion == 'relative_improvement_per_abstention':
            df['improvement_per_abstention'] = df['relative_error_reduction'] / df['abstention_level']
            df.loc[df['abstention_level'] == 0, 'improvement_per_abstention'] = 0
            idx = df['improvement_per_abstention'].idxmax()
        elif criterion == 'absolute_improvement_per_abstention':
            df['improvement_per_abstention'] = df['absolute_error_reduction'] / df['abstention_level']
            df.loc[df['abstention_level'] == 0, 'improvement_per_abstention'] = 0
            idx = df['improvement_per_abstention'].idxmax()
        else:
            raise ValueError(f"Unknown criterion: {criterion}")

        return df.loc[idx].to_dict()

    def evaluate_individual_metrics(self, df, target_col, min_samples=5, max_abstention=0.5):
        """Evaluate each individual uncertainty metric's predictive performance."""
        exclude_prefixes = ['qid', 'original_', 'majority_', 'combined_', 'n_', 'norm_']
        exclude_suffixes = ['_correct', '_matches_text']

        metrics_to_evaluate = []
        for col in df.columns:
            if any(col.startswith(prefix) for prefix in exclude_prefixes) or \
               any(col.endswith(suffix) for suffix in exclude_suffixes):
                continue
            metrics_to_evaluate.append(col)

        print(f"Metrics to evaluate: {metrics_to_evaluate}")

        for metric in ['text_consistency', 'smt_consistency']:
            if metric in df.columns and metric not in metrics_to_evaluate:
                metrics_to_evaluate.append(metric)

        combined_metrics = [col for col in df.columns if col.startswith('combined_')]
        metrics_to_evaluate.extend(combined_metrics)

        results = []

        for metric in metrics_to_evaluate:
            if metric not in df.columns or df[metric].isna().all():
                continue

            valid_mask = ~df[[metric, target_col]].isna().any(axis=1)
            if valid_mask.sum() < min_samples or len(df.loc[valid_mask, target_col].unique()) < 2:
                continue

            try:
                corr = df.loc[valid_mask, [metric, target_col]].corr().iloc[0, 1]
                y_pred = df.loc[valid_mask, metric].values if corr >= 0 else -df.loc[valid_mask, metric].values
            except:
                y_pred = df.loc[valid_mask, metric].values

            y_true = df.loc[valid_mask, target_col].values

            try:
                auroc = self.calculate_auroc(y_true, y_pred)
                if auroc < 0.5:
                    auroc = 1 - auroc
                    y_pred = -y_pred
            except:
                auroc = np.nan

            try:
                y_pred_norm = (y_pred - np.min(y_pred)) / (np.max(y_pred) - np.min(y_pred))
                brier = self.calculate_brier_score(y_true, y_pred_norm)
                ece = self.calculate_ece(y_true, y_pred_norm)
                aurc = self.calculate_aurc(y_true, y_pred_norm)

                abstention_analysis = self.calculate_error_vs_abstention(y_true, y_pred_norm)
                optimal_abstention = self.find_optimal_abstention(
                    abstention_analysis,
                    max_abstention=max_abstention,
                    criterion='relative_improvement_per_abstention'
                )

                optimal_abstention_level = optimal_abstention['abstention_level'] if optimal_abstention else np.nan
                optimal_error_rate = optimal_abstention['error_rate'] if optimal_abstention else np.nan
                optimal_rel_reduction = optimal_abstention['relative_error_reduction'] if optimal_abstention else np.nan

            except:
                brier = np.nan
                ece = np.nan
                aurc = np.nan
                optimal_abstention_level = np.nan
                optimal_error_rate = np.nan
                optimal_rel_reduction = np.nan

            results.append({
                'Metric': metric,
                'AUROC': auroc,
                'ECE': ece,
                'Brier': brier,
                'AURC': aurc,
                'Optimal_Abstention': optimal_abstention_level,
                'Error_At_Optimal': optimal_error_rate,
                'Relative_Error_Reduction': optimal_rel_reduction
            })

        results_df = pd.DataFrame(results)
        return results_df

    def categorize_metrics(self, results_df):
        """Group metrics by category for better comparison."""
        categories = {
            'Information Theory': [
                'grammar_entropy', 'perplexity', 'kl_divergence_from_uniform', 'nsui',
                'renyi_entropy_order2', 'renyi_entropy_order05'
            ],
            'Structural Properties': [
                'spectral_radius', 'spectral_factor', 'max_entropy', 'entropy_ratio'
            ],
            'Grammar Statistics': [
                'grammar_num_nonterminals', 'grammar_num_rules', 'grammar_avg_rules_per_nt',
                'grammar_avg_rhs_length', 'grammar_max_branching_factor'
            ],
            'Rule Distribution': [
                'rule_dist_mean', 'rule_dist_std', 'rule_dist_skew', 'rule_dist_kurtosis'
            ],
            'Consistency Measures': [
                'text_consistency', 'smt_consistency'
            ],
            'Combined Estimators': [
                col for col in results_df['Metric'] if col.startswith('combined_')
            ]
        }

        categorized = {}
        for category, metrics in categories.items():
            category_metrics = [m for m in metrics if m in results_df['Metric'].values]
            if category_metrics:
                categorized[category] = results_df[results_df['Metric'].isin(category_metrics)].reset_index(drop=True)

        all_categorized = [metric for category in categories.values() for metric in category]
        uncategorized = [m for m in results_df['Metric'] if m not in all_categorized]
        if uncategorized:
            categorized['Other Metrics'] = results_df[results_df['Metric'].isin(uncategorized)].reset_index(drop=True)

        return categorized
