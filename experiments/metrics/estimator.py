"""Combined uncertainty estimators."""

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from experiments.metrics.types import MetricDirection
from experiments.metrics.calculator import MetricsCalculator


class CombinedEstimator:
    """Create combined uncertainty estimators."""

    def create_all_estimators(self, df, target_col):
        """Create and evaluate all estimators."""
        df_result = df.copy()

        metrics_calc = MetricsCalculator()

        base_uncertainty_metrics = [
            'grammar_entropy', 'spectral_radius', 'nsui', 'perplexity',
            'kl_divergence_from_uniform', 'max_entropy', 'spectral_factor',
            'text_consistency', 'smt_consistency'
        ]

        additional_metrics = []
        for col in df.columns:
            if (col.startswith('renyi_') or col.startswith('rule_dist_') or
                col.startswith('grammar_')) and col not in base_uncertainty_metrics:
                additional_metrics.append(col)

        uncertainty_metrics = base_uncertainty_metrics + additional_metrics
        uncertainty_metrics = [m for m in uncertainty_metrics if m in df.columns]

        directions = {}
        for metric in uncertainty_metrics:
            if not df[metric].isna().all():
                directions[metric] = metrics_calc.determine_metric_direction(df, metric, target_col)
                print(f"Direction for {metric}: {directions[metric]}")

        # Create normalized metrics
        normalized_metrics = []
        for metric in uncertainty_metrics:
            if metric in directions and directions[metric] != MetricDirection.UNKNOWN:
                if df[metric].isna().sum() > len(df) * 0.5:
                    continue

                try:
                    norm_col = f"norm_{metric}"
                    min_val = df[metric].min()
                    max_val = df[metric].max()

                    if min_val == max_val:
                        continue

                    if directions[metric] == MetricDirection.POSITIVE:
                        df_result[norm_col] = (df[metric] - min_val) / (max_val - min_val)
                    else:
                        df_result[norm_col] = 1 - (df[metric] - min_val) / (max_val - min_val)

                    normalized_metrics.append(norm_col)
                except Exception as e:
                    print(f"Error normalizing {metric}: {e}")

        # Create simple average ensemble
        if normalized_metrics:
            df_result['combined_average'] = df_result[normalized_metrics].mean(axis=1)

        # Create weighted average based on correlation with target
        if normalized_metrics and len(df_result) > 10:
            try:
                weights = {}
                for metric in normalized_metrics:
                    valid_mask = ~df_result[[metric, target_col]].isna().any(axis=1)
                    if valid_mask.sum() > 5:
                        corr = abs(df_result.loc[valid_mask, [metric, target_col]].corr().iloc[0, 1])
                        if not np.isnan(corr):
                            weights[metric] = corr * corr

                total_weight = sum(weights.values())
                if total_weight > 0:
                    weights = {k: v/total_weight for k, v in weights.items()}

                    df_result['combined_weighted'] = 0
                    for metric, weight in weights.items():
                        df_result['combined_weighted'] += df_result[metric] * weight

                    print("\nWeights for combined_weighted:")
                    for metric, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True)[:5]:
                        print(f"  {metric}: {weight:.4f}")
            except Exception as e:
                print(f"Error creating weighted average: {e}")

        # Create ML ensemble
        specific_features = [
            'grammar_entropy',
            'perplexity',
            'spectral_radius',
            'nsui',
            'spectral_factor',
            'kl_divergence_from_uniform',
            'max_entropy',
            'smt_consistency'
        ]

        available_features = [f for f in specific_features if f in df.columns]

        if len(available_features) >= 3 and 'smt_consistency' in available_features:
            print(f"\nUsing ML ensemble with features: {available_features}")

            df_clean = df.dropna(subset=available_features + [target_col]).copy()

            if len(df_clean) >= 10 and len(df_clean[target_col].unique()) >= 2:
                try:
                    X = df_clean[available_features].copy().values
                    X[:, available_features.index('grammar_entropy')] = -X[:, available_features.index('grammar_entropy')]

                    y = df_clean[target_col].values

                    scaler = StandardScaler()
                    X_scaled = scaler.fit_transform(X)

                    model = LogisticRegression(class_weight='balanced', max_iter=10000, random_state=42)
                    model.fit(X_scaled, y)

                    coeffs = model.coef_[0]
                    print("\nML Ensemble Feature Weights:")
                    for feature, coeff in zip(available_features, coeffs):
                        print(f"  {feature}: {coeff:.4f}")

                    df_result.loc[df_clean.index, 'combined_ml'] = model.predict_proba(X_scaled)[:, 1]

                    simple_metrics = ['grammar_entropy', 'spectral_radius', 'smt_consistency']
                    available_simple = [m for m in simple_metrics if m in available_features]

                    if len(available_simple) == 3:
                        df_result.loc[df_clean.index, 'combined_simple'] = (
                            (1 - (df_clean['grammar_entropy'] - df_clean['grammar_entropy'].min()) /
                            (df_clean['grammar_entropy'].max() - df_clean['grammar_entropy'].min())) * 0.33 +

                            (1 - (df_clean['spectral_radius'] - df_clean['spectral_radius'].min()) /
                            (df_clean['spectral_radius'].max() - df_clean['spectral_radius'].min())) * 0.33 +

                            df_clean['smt_consistency'] * 0.34
                        )

                        ml_auroc = roc_auc_score(df_clean[target_col], df_result.loc[df_clean.index, 'combined_ml'])
                        simple_auroc = roc_auc_score(df_clean[target_col], df_result.loc[df_clean.index, 'combined_simple'])

                        print(f"ML Combined AUROC: {ml_auroc:.4f}")
                        print(f"Simple Combined AUROC: {simple_auroc:.4f}")

                        if simple_auroc > ml_auroc:
                            print("Simple combined model performed better, using it for combined_ml")
                            df_result.loc[df_clean.index, 'combined_ml'] = df_result.loc[df_clean.index, 'combined_simple']

                except Exception as e:
                    print(f"Error creating ML ensemble: {e}")

        return df_result, directions
