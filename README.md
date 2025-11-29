# Grammars of Formal Uncertainty

PCFG-based uncertainty quantification for programs. Extracts probabilistic context-free grammars from source code and computes entropy metrics.

## Install

```bash
pip install -e .
# or
docker-compose up
```

## Usage

```python
from grammar_uncertainty import GrammarAnalyzer

result = GrammarAnalyzer(grammar="smtlib").analyze("/path/to/programs")
print(result.uncertainty.grammar_entropy, result.uncertainty.perplexity)
```

```bash
grammar-uncertainty setup smtlib
grammar-uncertainty analyze ./programs --grammar smtlib --output results.json
grammar-uncertainty serve --port 8000
```

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


