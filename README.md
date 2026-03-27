# AEGIS: Retrieval-Grounded Generation of Safety-Critical Automotive OTA Deployment Specifications

AEGIS is an LLM-based agent that turns plain-language OTA update requests into schema-valid, ISO 26262-compliant deployment specifications. Rather than generating safety-critical fields from scratch, AEGIS retrieves the closest matching template from a curated knowledge base of validated deployment patterns and constrains the LLM to adapt it — keeping all mandatory safety fields, rollback logic, and schema constraints intact.

> Code artifact for the paper submitted to ASE 2026.
> Repository: [https://github.com/SK1PPR/aegis](https://github.com/SK1PPR/aegis)

---

## How It Works

AEGIS uses a three-stage retrieval pipeline before any LLM generation:

1. **Metadata Filtering** — Hard constraints on ECU type, safety class, SW version, region, hardware revision, and deployment mode. Uses a five-level fallback that never relaxes ECU type or safety class.
2. **Semantic Retrieval** — Dense vector search over metadata-approved candidates using `all-MiniLM-L6-v2` embeddings.
3. **Schema-Aware Re-Ranking** — Composite score: `0.35·semantic + 0.30·schema + 0.20·recency + 0.15·validation`. Top-2 patterns are injected into the LLM prompt as templates.

The LLM (`gpt-4o-2024-08-06`) then adapts the retrieved template to the user's request, preserving all safety-critical fields. The output is validated against the schema and safety rules; errors are fed back for corrective re-prompting.

---

## Results

Evaluated on 18 OTA deployment test cases across 6 ECU types and 5 ASIL safety classes:

| Metric | Value |
|---|---|
| Success Rate | 94.44% |
| ASIL Safety Compliance | 84.62% |
| Rollback Coverage | 84.62% |
| Avg Latency | ~4.2 s |

Compared against grammar-based (GR), template-based (TP), and plain-LLM (PL) baselines on a 28-task benchmark:

| | Validity | Completeness | Extensibility |
|---|---|---|---|
| AEGIS (Ours) | 85.71% | 80.95% | 100% |
| Plain LLM | 92.86% | 87.50% | 100% |
| Grammar-Based | 82.14% | 90.14% | 88.24% |
| Template-Based | 67.86% | 96.48% | 76.47% |

---

## Project Structure

```
aegis/
├── src/
│   ├── agent.py                 # AEGIS agent — three-stage retrieval + LLM generation
│   ├── knowledge_base.py        # Knowledge base, retrieval pipeline, re-ranking
│   ├── ota_metrics_evaluator.py # Benchmark evaluation and metrics
│   ├── ota_test_dataset.py      # 18-case OTA test dataset
│   ├── dataset_generator.py     # 28-task DSL benchmark dataset
│   ├── dsl_generator.py         # DSL generation utilities
│   └── schema.py                # Schema definitions
│
├── data/
│   ├── ota_knowledge_base.json       # 19-pattern retrieval database
│   └── automotive_ota_patterns.json  # Source OTA patterns
│
├── results/
│   ├── ota_evaluation_results.json       # 18-case OTA benchmark results
│   ├── evaluation_summary.json           # 28-task AEGIS results
│   ├── plain_llm_evaluation_summary.json # 28-task PL baseline
│   ├── grammar_evaluation_summary.json   # 28-task GR baseline
│   └── template_evaluation_summary.json  # 28-task TP baseline
│
├── metrics_ota-main/            # Comparison metrics vs TUF, Balena, RAUC, etc.
├── scripts/                     # Knowledge base utilities
├── tests/                       # Test and verification scripts
├── run_ota_benchmark.py         # Main benchmark runner
├── main.py                      # Interactive entry point
├── requirements.txt
└── .env.example
```

---

## Quick Start

```bash
# 1. Clone and set up environment
git clone https://github.com/SK1PPR/aegis
cd aegis
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Run the benchmark
python run_ota_benchmark.py
```

Results are saved to `results/ota_evaluation_results.json`.

---

## Knowledge Base

19 validated OTA deployment patterns covering:
- **ECU types**: Infotainment, ADAS, Powertrain, Telematics, Gateway, Body Control
- **Safety classes**: QM, ASIL-A, ASIL-B, ASIL-C, ASIL-D
- **Deployment modes**: A/B, Dual-bank, Delta, Full, Single-bank
- **Regions**: US, EU, CN, GLOBAL

To add new patterns, edit `data/automotive_ota_patterns.json` and run:
```bash
python scripts/convert_ota_patterns.py
python tests/verify_ota_patterns.py
```

---

## Requirements

- Python 3.9+
- OpenAI API key (`gpt-4o-2024-08-06`)
- See `requirements.txt` for full dependency list
