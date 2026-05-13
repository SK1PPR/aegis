# RGOTA: Retrieval-Grounded Generation of Safety-Critical Automotive OTA Deployment Specifications

RGOTA converts natural-language automotive OTA deployment requests into structured, safety-aware deployment specifications. It retrieves validated OTA patterns first, filters them by hard metadata such as ECU type and ASIL class, re-ranks them by semantic and schema fit, and then asks `gpt-4o-2024-08-06` to adapt the retrieved template.

This repository is the code and artifact bundle for the ASE 2026 paper, "RGOTA: Retrieval-Grounded Generation of Safety-Critical Automotive OTA Deployment Specifications."

## What Is Included

```text
src/
  agent.py                  LLM agent and prompt construction
  knowledge_base.py         Three-stage retrieval pipeline
  ota_metrics_evaluator.py  18-case OTA benchmark metrics
  ota_test_dataset.py       OTA benchmark cases
  dataset_generator.py      28-task baseline benchmark data
  dsl_generator.py          DSL generation utilities
  schema.py                 Schema helpers

data/
  ota_knowledge_base.json       Curated OTA retrieval patterns
  automotive_ota_patterns.json  Source pattern data
  ota_test_dataset.json         Generated OTA benchmark cases

results/
  ota_evaluation_results.json       Paper Table 2/3 OTA results
  evaluation_summary.json           RGOTA 28-task benchmark summary
  plain_llm_evaluation_summary.json Plain LLM baseline summary
  grammar_evaluation_summary.json   Grammar baseline summary
  template_evaluation_summary.json  Template baseline summary

metrics_ota-main/
  Baseline OTA framework metrics and generated comparison graphs

scripts/
  verify_ota_setup.py      Environment/setup checks
  convert_ota_patterns.py  Knowledge-base conversion utility
```

## Environment

Use a virtual environment in the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For a quick offline smoke test, no OpenAI key is required:

```bash
RGOTA_EMBEDDING_BACKEND=hash python tests/quick_test.py
```

The default retrieval backend uses `sentence-transformers/all-MiniLM-L6-v2`, matching the paper. The `hash` backend is only for deterministic local smoke tests when model downloads or caches are unavailable.

## Run The Live Benchmark

The full benchmark calls OpenAI and requires an API key:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
python run_ota_benchmark.py
```

The live run rewrites:

```text
data/ota_test_dataset.json
results/ota_evaluation_results.json
results/nl2dsl_quick_metrics.json
metrics_ota-main/nl2dsl_agent_metrics.json
```

Because live LLM calls can vary by model/service behavior and latency, the checked-in `results/` files are the archived artifact values used for the paper tables.

## Results

OTA benchmark on 18 deployment cases across six ECU types and five safety classes:

| Category | Count | Success | Precision | Recall |
|---|---:|---:|---:|---:|
| Single ECU | 2 | 100.00% | 62.72% | 75.00% |
| Multi-ECU | 2 | 100.00% | 31.74% | 43.33% |
| Safety Critical | 2 | 100.00% | 32.14% | 40.00% |
| Infotainment | 2 | 100.00% | 61.05% | 65.00% |
| ADAS | 2 | 100.00% | 31.97% | 22.17% |
| Powertrain | 2 | 100.00% | 31.38% | 38.00% |
| Regional | 2 | 100.00% | 61.18% | 65.00% |
| Rollback | 2 | 50.00% | 64.29% | 84.00% |
| Delta Update | 2 | 100.00% | 61.25% | 65.00% |
| Overall | 18 | 94.44% | 47.71% | 53.59% |

28-task baseline comparison:

| Approach | Validity | Completeness | Extensibility | Grammar Pass | Latency |
|---|---:|---:|---:|---:|---:|
| Template-Based | 67.86% | 96.48% | 76.47% | 78.57% | 0.002s |
| Grammar-Based | 82.14% | 90.14% | 88.24% | 92.86% | 0.002s |
| Plain LLM | 92.86% | 87.50% | 100.00% | 100.00% | 1.534s |
| RGOTA | 85.71% | 80.95% | 100.00% | 100.00% | 4.423s |

## Knowledge Base Maintenance

To update OTA patterns:

```bash
python scripts/convert_ota_patterns.py
RGOTA_EMBEDDING_BACKEND=hash python tests/verify_ota_patterns.py
```

Use the default embedding backend for final experiments, and use `RGOTA_EMBEDDING_BACKEND=hash` for quick offline checks.
