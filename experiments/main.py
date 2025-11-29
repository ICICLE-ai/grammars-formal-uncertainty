"""CLI entry point for experiments."""

import os
from pathlib import Path
from typing import Optional

import typer

from experiments.pipeline import run_uncertainty_analysis

app = typer.Typer(help="Run uncertainty analysis experiments on SMT datasets.")


def find_dataset_paths(dataset_path: str) -> tuple[str, str]:
    """Auto-discover smt_programs dir and results JSON from a dataset path."""
    path = Path(dataset_path)

    # Look for smt_programs directory
    smt_dir = None
    if (path / "smt_programs").is_dir():
        smt_dir = str(path / "smt_programs")
    elif path.name == "smt_programs" and path.is_dir():
        smt_dir = str(path)
    else:
        # Maybe the path itself contains QID directories
        subdirs = [d for d in path.iterdir() if d.is_dir()] if path.is_dir() else []
        if subdirs and any((d / "").exists() or len(list(d.glob("*.smt2"))) > 0 for d in subdirs[:3]):
            smt_dir = str(path)

    if not smt_dir:
        raise typer.BadParameter(f"Could not find smt_programs directory in {dataset_path}")

    # Look for results JSON
    results_json = None
    search_dir = path if path.is_dir() else path.parent

    for name in ["result_log.json", "results_log.json", "results.json"]:
        candidate = search_dir / name
        if candidate.exists():
            results_json = str(candidate)
            break

    # Also check parent directory
    if not results_json:
        for name in ["result_log.json", "results_log.json", "results.json"]:
            candidate = search_dir.parent / name
            if candidate.exists():
                results_json = str(candidate)
                break

    if not results_json:
        raise typer.BadParameter(f"Could not find results JSON file in {dataset_path}")

    return smt_dir, results_json


@app.command()
def run(
    dataset: str = typer.Argument(
        ...,
        help="Path to dataset directory (will auto-discover smt_programs/ and result_log.json)"
    ),
    smt_dir: Optional[str] = typer.Option(
        None,
        "--smt-dir",
        help="Explicit path to smt_programs directory (overrides auto-discovery)"
    ),
    results_json: Optional[str] = typer.Option(
        None,
        "--results",
        help="Explicit path to results JSON file (overrides auto-discovery)"
    ),
    cache_dir: str = typer.Option(
        "uncertainty_cache",
        "--cache-dir",
        help="Directory for caching intermediate results"
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Ignore cached results and reprocess all files"
    ),
):
    """Run uncertainty analysis on a dataset."""
    # Resolve paths
    if smt_dir and results_json:
        resolved_smt_dir = smt_dir
        resolved_results_json = results_json
    else:
        auto_smt_dir, auto_results_json = find_dataset_paths(dataset)
        resolved_smt_dir = smt_dir or auto_smt_dir
        resolved_results_json = results_json or auto_results_json

    print(f"SMT directory: {resolved_smt_dir}")
    print(f"Results JSON: {resolved_results_json}")
    print(f"Cache directory: {cache_dir}")
    print(f"Use cache: {not no_cache}")
    print()

    run_uncertainty_analysis(
        smt_dir=resolved_smt_dir,
        results_json=resolved_results_json,
        cache_dir=cache_dir,
        use_cache=not no_cache
    )


@app.command()
def list_datasets(
    base_dir: str = typer.Argument(
        "smtlogs",
        help="Base directory containing datasets"
    ),
):
    """List available datasets in a directory."""
    base_path = Path(base_dir)

    if not base_path.exists():
        print(f"Directory not found: {base_dir}")
        raise typer.Exit(1)

    # Find all result_log.json or results_log.json files
    result_files = list(base_path.rglob("result*.json"))

    if not result_files:
        print(f"No datasets found in {base_dir}")
        raise typer.Exit(0)

    print(f"Found {len(result_files)} dataset(s):\n")

    for result_file in sorted(result_files):
        dataset_dir = result_file.parent
        rel_path = dataset_dir.relative_to(base_path)
        smt_programs = dataset_dir / "smt_programs"

        if smt_programs.exists():
            n_problems = len(list(smt_programs.iterdir()))
            print(f"  {rel_path}")
            print(f"    Problems: {n_problems}")
            print()


if __name__ == "__main__":
    app()
