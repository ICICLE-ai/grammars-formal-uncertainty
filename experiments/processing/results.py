"""Results analysis and combination with uncertainty metrics."""

import json
import numpy as np
import pandas as pd


class ResultsAnalyzer:
    """Analyze results and combine with uncertainty metrics."""

    def analyze_json(self, json_file, use_text_majority_as_gt=False):
        """Analyze results JSON file."""
        with open(json_file, "r") as f:
            data = json.load(f)

        results = data.get("results", [])
        rows = []

        for res in results:
            qid = res.get("qid")
            original_gt = res.get("ground_truth")

            # Text consistency
            text_answers = res.get("model_text_answers", [])
            if text_answers:
                majority_text = max(set(text_answers), key=text_answers.count)
                text_consistency = text_answers.count(majority_text) / len(text_answers)
            else:
                majority_text = None
                text_consistency = np.nan

            # SMT consistency
            smt_versions = res.get("valid_smt_versions", [])
            smt_answers = [ver.get("smt_evaluation") for ver in smt_versions
                           if ver.get("smt_evaluation") is not None]
            if smt_answers:
                majority_smt = max(set(smt_answers), key=smt_answers.count)
                smt_consistency = smt_answers.count(majority_smt) / len(smt_answers)
            else:
                majority_smt = None
                smt_consistency = np.nan

            # Set ground truth
            gt = majority_text if use_text_majority_as_gt else original_gt

            # Correctness
            text_correct = 1 if majority_text == gt else 0
            smt_correct = 1 if majority_smt == gt else 0
            smt_matches_text = 1 if majority_smt == majority_text else 0

            rows.append({
                "qid": qid,
                "original_ground_truth": original_gt,
                "majority_text": majority_text,
                "majority_smt": majority_smt,
                "text_consistency": text_consistency,
                "smt_consistency": smt_consistency,
                "text_correct": text_correct,
                "smt_correct": smt_correct,
                "smt_matches_text": smt_matches_text,
                "n_text": len(text_answers),
                "n_smt": len(smt_versions)
            })

        return pd.DataFrame(rows)

    def combine_results(self, df, uncertainty_metrics):
        """Combine results with uncertainty metrics."""
        df_result = df.copy()

        # Get all available metrics from the first non-empty entry
        all_metrics = []
        for qid, metrics in uncertainty_metrics.items():
            if metrics:
                all_metrics = list(metrics.keys())
                break

        # Add columns for all uncertainty metrics
        for metric in all_metrics:
            df_result[metric] = np.nan

        # Fill values
        for idx, row in df_result.iterrows():
            qid = row['qid']
            if qid in uncertainty_metrics:
                for metric in all_metrics:
                    if metric in uncertainty_metrics[qid]:
                        df_result.at[idx, metric] = uncertainty_metrics[qid][metric]

        return df_result
