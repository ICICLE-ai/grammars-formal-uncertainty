# Experiments

Evaluates uncertainty metrics as predictors of SMT correctness.

## Setup

```bash
# Build the Docker container (required before first run)
docker compose build
```

## Run

```bash
# List available datasets
docker compose run --rm grammar-uncertainty python -m experiments list-datasets smtlogs

# Run on a specific dataset (auto-discovers smt_programs/ and result_log.json)
docker compose run --rm grammar-uncertainty python -m experiments run smtlogs/ProofWriter/03-mini/200-100/o3-mini-200-100

# Run with explicit paths
docker compose run --rm grammar-uncertainty python -m experiments run \
    --smt-dir smtlogs/ProofWriter/03-mini/200-100/o3-mini-200-100/smt_programs \
    --results smtlogs/ProofWriter/03-mini/200-100/o3-mini-200-100/result_log.json \
    dataset

# Force reprocessing (ignore cache)
docker compose run --rm grammar-uncertainty python -m experiments run --no-cache smtlogs/...
```

## Adding New Datasets

1. Place your dataset in `smtlogs/` with structure:
   ```
   smtlogs/YourDataset/model-name/
   ├── smt_programs/
   │   ├── problem_0/
   │   │   ├── file1.smt2
   │   │   └── file2.smt2
   │   └── problem_1/
   │       └── ...
   └── result_log.json  (or results_log.json)
   ```

2. Rebuild Docker to pick up new files:
   ```bash
   docker compose build
   ```

3. Run experiments on the new dataset.

## Output

- TSV tables with AUROC, ECE, Brier, AURC for each metric
- Cached results in `uncertainty_cache/` (use `--no-cache` to recompute)
