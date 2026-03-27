# NL2DSL Agent - Natural Language to DSL Generation for OTA Updates

AI-powered system for generating deployment specifications for automotive Over-The-Air (OTA) updates from natural language descriptions.

## Project Structure

```
nl2dsl-agent/
├── src/                      # Core source code
│   ├── __init__.py          # Package initialization
│   ├── agent.py             # Main DSL agent with LLM integration
│   ├── knowledge_base.py    # Three-stage retrieval pipeline
│   ├── ota_metrics_evaluator.py  # Evaluation and metrics
│   ├── ota_test_dataset.py  # Test dataset generation
│   ├── dsl_generator.py     # DSL generation utilities
│   ├── dataset_generator.py # Dataset utilities
│   └── schema.py            # Schema definitions
│
├── data/                     # Data files
│   ├── ota_knowledge_base.json      # Retrieval database (12 patterns)
│   ├── automotive_ota_patterns.json # Source OTA patterns
│   └── ota_test_dataset.json        # Generated test cases
│
├── results/                  # Evaluation results
│   ├── ota_evaluation_results.json  # Detailed benchmark results
│   ├── nl2dsl_quick_metrics.json   # Quick metrics summary
│   └── [historical results]
│
├── scripts/                  # Utility scripts
│   ├── convert_ota_patterns.py     # Convert patterns to KB format
│   ├── fix_safety_class.py         # Fix safety class formatting
│   ├── fix_schema_fields.py        # Fix schema field structure
│   ├── load_automotive_patterns.py # Load patterns into KB
│   ├── update_ota_metrics_graph.py # Update metrics visualization
│   └── verify_ota_setup.py         # Verify setup completeness
│
├── tests/                    # Test files
│   ├── test_agent_simple.py        # Simple agent tests
│   ├── test_grammar.py             # Grammar validation tests
│   └── verify_ota_patterns.py      # Pattern verification
│
├── deprecated/               # Old/unused code (kept for reference)
│   ├── grammar_based_generator.py
│   ├── template_based_generator.py
│   └── [other legacy files]
│
├── docs/                     # Documentation
│   ├── BENCHMARK_RESULTS_FINAL.md
│   ├── OTA_BENCHMARK_SUMMARY.md
│   ├── QUICKSTART_OTA_BENCHMARK.md
│   └── SETUP.md
│
├── metrics_ota-main/         # Metrics for comparison with other systems
│   └── nl2dsl_agent_metrics.json
│
├── run_ota_benchmark.py      # Main benchmark runner
├── main.py                   # Alternative entry point
├── .env                      # Environment variables (API keys)
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Quick Start

### 1. Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

### 3. Run the Benchmark

```bash
python run_ota_benchmark.py
```

This will:
1. Generate 18 OTA test cases
2. Run evaluation using the nl2dsl agent
3. Generate metrics compatible with other OTA systems
4. Save results to `results/` directory

## Key Features

### Three-Stage Retrieval Pipeline

1. **Metadata Filtering** - Deterministic filtering by ECU type, safety class, region
2. **Semantic Search** - Vector-based similarity matching
3. **Schema-Aware Re-Ranking** - Structural and version-aware scoring

### Knowledge Base

- **12 OTA Patterns** covering:
  - Multiple ECU types (infotainment, ADAS, powertrain, telematics, gateway)
  - Safety levels (QM, ASIL-A, ASIL-B, ASIL-D)
  - Regions (US, EU, CN)
  - Deployment modes (A/B, dual-bank, delta, full)

### Evaluation Metrics

- **Precision & Recall** - Accuracy of generated specifications
- **Success Rate** - Percentage of valid deployments
- **Latency** - Generation time (avg, median, P95, P99)
- **Safety Compliance** - Automotive-specific safety checks
- **Rollback Coverage** - Emergency recovery procedures

## Current Performance

Based on the latest benchmark run:

- **Precision**: 61.43%
- **Recall**: 69.44%
- **Success Rate**: 16.67%
- **Avg Latency**: 1552ms
- **Safety Compliance**: 7.69%

## Development

### Running Tests

```bash
# Test agent functionality
python tests/test_agent_simple.py

# Verify OTA patterns
python tests/verify_ota_patterns.py
```

### Adding New Patterns

1. Add patterns to `data/automotive_ota_patterns.json`
2. Run conversion script:
   ```bash
   python scripts/convert_ota_patterns.py
   ```
3. Verify patterns loaded correctly:
   ```bash
   python tests/verify_ota_patterns.py
   ```

### Project Cleanup

The project has been reorganized for clarity:
- Core functionality in `src/`
- Utility scripts in `scripts/`
- Test files in `tests/`
- Results and data separated
- Deprecated code moved to `deprecated/`

## Architecture

### Agent (src/agent.py)
- Manages conversation with LLM
- Integrates with knowledge base for retrieval
- Generates deployment specifications

### Knowledge Base (src/knowledge_base.py)
- Loads and indexes OTA patterns
- Implements three-stage retrieval
- Handles semantic embeddings

### Evaluator (src/ota_metrics_evaluator.py)
- Runs benchmark evaluation
- Calculates precision/recall
- Generates comparative metrics

## Next Steps

1. Improve success rate by:
   - Adding more diverse patterns to knowledge base
   - Better version/hardware matching
   - Enhanced safety validation

2. Expand test coverage:
   - More edge cases
   - Multi-ECU scenarios
   - Regional variations

3. Optimize performance:
   - Reduce latency
   - Improve retrieval accuracy
   - Better LLM prompting

## Contributing

When adding new features:
1. Put core functionality in `src/`
2. Add tests to `tests/`
3. Update documentation in `docs/`
4. Keep utility scripts in `scripts/`

## License

[Your License Here]
