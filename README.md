# Grammars of Formal Uncertainty

<!-- ICICLE metadata start -->
Grammars of Formal Uncertainty uses probabilistic context-free grammars to estimate uncertainty in generated code and formal reasoning tasks.

**Tags:** Foundation-AI

> This ICICLE fork tracks [`DebarghaG/grammars-formal-uncertainty`](https://github.com/DebarghaG/grammars-formal-uncertainty). Send code contributions to [upstream pull requests](https://github.com/DebarghaG/grammars-formal-uncertainty/pulls) and report bugs or feature requests in [upstream issues](https://github.com/DebarghaG/grammars-formal-uncertainty/issues).

### License

[MIT](LICENSE)

## References

- [NeurIPS paper](https://openreview.net/attachment?id=QfKpJ00t2L&name=pdf)
- [Experiment guide](experiments/README.md)
- [Upstream repository](https://github.com/DebarghaG/grammars-formal-uncertainty)

## Acknowledgements

*National Science Foundation (NSF) funded AI institute for Intelligent Cyberinfrastructure with Computational Learning in the Environment (ICICLE) (OAC 2112606)*

## Issue reporting

Report issues on [GitHub](https://github.com/DebarghaG/grammars-formal-uncertainty/issues).

---

# How-To Guides
<!-- ICICLE metadata end -->

PCFG-based uncertainty quantification for programs. Extracts probabilistic context-free grammars from source code and computes entropy metrics.

## Install

```bash
pip install -e .
```

Or with Docker:

```bash
docker compose build
```

## Quick Start

### Python API

```python
from grammar_uncertainty import GrammarAnalyzer

result = GrammarAnalyzer(grammar="smtlib").analyze("/path/to/programs")
print(result.uncertainty.grammar_entropy, result.uncertainty.perplexity)
```

### CLI

```bash
# Setup grammar (downloads ANTLR grammar and generates parser)
grammar-uncertainty setup smtlib

# Analyze a folder of programs
grammar-uncertainty analyze ./programs --grammar smtlib --output results.json

# Start the API server
grammar-uncertainty serve --port 8000
```

### Docker

```bash
# Run CLI commands
docker compose run --rm grammar-uncertainty grammar-uncertainty analyze /data/samplesmtfolder --grammar smtlib

# Start API server
docker compose up
```

## Experiments

Run uncertainty metric evaluation on SMT datasets:

```bash
# List available datasets
docker compose run --rm grammar-uncertainty python -m experiments list-datasets smtlogs

# Run analysis on a dataset
docker compose run --rm grammar-uncertainty python -m experiments run smtlogs/ProofWriter/03-mini/200-100/o3-mini-200-100
```

See [experiments/README.md](experiments/README.md) for details.

## Supported Grammars

| Grammar | Extensions | Setup |
|---------|------------|-------|
| smtlib | .smt2, .smt | `grammar-uncertainty setup smtlib` |
| prolog | .pl, .prolog | `grammar-uncertainty setup prolog` |

Extensible to any [ANTLR v4 grammar](https://github.com/antlr/grammars-v4). Implement `GrammarHandler` in `src/grammar_uncertainty/grammars/`.

## Metrics

- **Grammar Entropy**: Shannon entropy of the PCFG
- **Perplexity**: Exponential of cross-entropy
- **NSUI**: Normalized Syntactic Uncertainty Index
- **KL Divergence**: Distance from uniform distribution
- **Rényi Entropy**: Generalized entropy (α-parameterized)

## API

```bash
curl -X POST localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "/data/programs", "grammar": "smtlib"}'
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| /analyze | POST | Analyze programs |
| /grammars | GET | List grammars |
| /setup | POST | Setup grammar |
| /health | GET | Health check |

## Citation

```bibtex
@inproceedings{
ganguly2025grammars,
title={Grammars of Formal Uncertainty: When to Trust {LLM}s in Automated Reasoning Tasks},
author={Debargha Ganguly and Vikash Singh and Sreehari Sankar and Biyao Zhang and Xuecen Zhang and Srinivasan Iyengar and Xiaotian Han and Amit Sharma and Shivkumar Kalyanaraman and Vipin Chaudhary},
booktitle={The Thirty-ninth Annual Conference on Neural Information Processing Systems},
year={2025},
url={https://openreview.net/forum?id=QfKpJ00t2L}
}
```

## License

MIT
