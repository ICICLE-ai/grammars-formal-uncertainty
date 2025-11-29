# Experiments

Evaluates uncertainty metrics as predictors of SMT correctness.

## Run

```bash
# List available datasets
docker compose run --rm grammar-uncertainty python -m experiments list-datasets smtlogs

# Run on a specific dataset (auto-discovers paths)
docker compose run --rm grammar-uncertainty python -m experiments run smtlogs/ProofWriter/03-mini/200-100/o3-mini-200-100

# Run with explicit paths
docker compose run --rm grammar-uncertainty python -m experiments run \
    --smt-dir smtlogs/ProofWriter/03-mini/200-100/o3-mini-200-100/smt_programs \
    --results smtlogs/ProofWriter/03-mini/200-100/o3-mini-200-100/result_log.json \
    dataset

# Force reprocessing (ignore cache)
docker compose run --rm grammar-uncertainty python -m experiments run --no-cache smtlogs/...
```

## Output

- TSV tables with AUROC, ECE, Brier, AURC for each metric
- Cached results in `uncertainty_cache/` (use `--no-cache` to recompute)
