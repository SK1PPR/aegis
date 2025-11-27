# Quick Start: OTA Benchmarking for nl2dsl-agent

## 🎯 Goal

Run your nl2dsl-agent through the same benchmark tests as other OTA systems (TUF, Balena, RAUC, etc.) and generate comparison graphs.

## 📋 Prerequisites

```bash
# Ensure you have the required dependencies
pip install rich psutil matplotlib seaborn numpy pandas

# Verify your .env file has OPENAI_API_KEY
cat .env | grep OPENAI_API_KEY
```

## 🚀 Three-Step Process

### Step 1: Run the Benchmark (5-10 minutes)

```bash
python run_ota_benchmark.py
```

**What this does:**
- Generates 20+ automotive OTA test cases
- Runs your nl2dsl-agent on each test
- Measures: precision, recall, latency, CPU, memory
- Outputs: `nl2dsl_agent_metrics.json`

**Expected output:**
```
OTA Benchmark Evaluation for nl2dsl-agent
[1/4] Generating OTA test dataset...
  ✓ Generated 20 test cases
  ✓ Safety-critical: 8
  ✓ Multi-ECU: 4

[2/4] Running OTA evaluation...
  Evaluating 20 OTA test cases... 100%

[3/4] Generating OTA-compatible metrics...
  ✓ Metrics exported to metrics_ota-main/nl2dsl_agent_metrics.json

[4/4] Results Summary
  Precision:    87.5%
  Recall:       82.3%
  Breakage:     2.1%
  Avg Latency:  234.5 ms
```

### Step 2: Update Comparison Graphs

```bash
# Update the metrics.py file to include nl2dsl-agent
python update_ota_metrics_graph.py

# Copy metrics to comparison directory
cp metrics_ota-main/nl2dsl_agent_metrics.json metrics_ota-main/

# Generate comparison graphs
cd metrics_ota-main
python metrics.py
```

**What this does:**
- Adds nl2dsl-agent to the OTA comparison framework
- Generates 10 comparison graphs (PDF format)
- Shows nl2dsl-agent vs TUF, Balena, RAUC, etc.

### Step 3: View Results

```bash
# Open the generated graphs
open metrics_ota-main/graphs/01_cpu_usage_comparison.pdf
open metrics_ota-main/graphs/03_duration_comparison.pdf
open metrics_ota-main/graphs/04_latency_comparison.pdf
open metrics_ota-main/graphs/05_success_rates_comparison.pdf

# Or view all at once
open metrics_ota-main/graphs/*.pdf
```

## 📊 Understanding the Metrics

### Key Metrics Explained

1. **Precision** (87.5% in example)
   - Of what your agent generated, how much is correct?
   - Higher is better
   - Target: >85%

2. **Recall** (82.3% in example)
   - Of what should be generated, how much was included?
   - Higher is better
   - Target: >80%

3. **Breakage Rate** (2.1% in example)
   - Percentage of invalid/broken specs
   - Lower is better
   - Target: <5%

4. **Latency** (234.5 ms in example)
   - Time to generate deployment spec
   - Lower is better
   - Trade-off: AI accuracy vs speed

### Comparison Context

| System | Type | Strengths | nl2dsl-agent Advantage |
|--------|------|-----------|------------------------|
| TUF/Uptane | Security-focused | Strong cryptography | + Automotive semantics |
| Balena/HawkBit | IoT general | Wide adoption | + Domain-specific |
| RAUC/SWUpdate | Implementation | Low-level control | + High-level specs |
| Blockchain OTA | Immutable | Audit trail | + Speed, AI accuracy |

## 📁 Generated Files

After running the benchmark, you'll have:

```
nl2dsl-agent/
├── ota_test_dataset.json              # Test cases (20+ scenarios)
├── ota_evaluation_results.json        # Detailed results per test
├── nl2dsl_quick_metrics.json          # Quick summary
└── metrics_ota-main/
    ├── nl2dsl_agent_metrics.json      # OTA-compatible metrics
    └── graphs/
        ├── 01_cpu_usage_comparison.pdf
        ├── 02_memory_usage_comparison.pdf
        ├── 03_duration_comparison.pdf
        ├── 04_latency_comparison.pdf
        ├── 05_success_rates_comparison.pdf
        ├── 06_download_speed_comparison.pdf
        ├── 07_specialized_metrics.pdf
        ├── 08_resource_efficiency_matrix.pdf
        ├── 09_throughput_analysis.pdf
        └── 10_performance_radar.pdf
```

## 🎯 Test Coverage

The benchmark tests your agent on:

### By Category
- ✅ Single ECU updates (infotainment, ADAS)
- ✅ Multi-ECU updates (coordinated deployments)
- ✅ Safety-critical systems (ASIL-B/C/D)
- ✅ Regional updates (US, EU, CN)
- ✅ Rollback scenarios
- ✅ Delta updates (bandwidth optimization)

### By Complexity
- ✅ Simple (basic firmware update)
- ✅ Medium (with pre-conditions)
- ✅ Complex (multi-ECU with dependencies)
- ✅ Very Complex (safety-critical with full verification)

### By Safety Level
- ✅ QM (Quality Managed, non-safety)
- ✅ ASIL-A (lowest safety level)
- ✅ ASIL-B (ADAS systems)
- ✅ ASIL-C (brake control)
- ✅ ASIL-D (powertrain, highest safety)

## 🔍 Detailed Analysis

### View Per-Test Results

```bash
# Open detailed results
cat ota_evaluation_results.json | jq '.detailed_results[] | {id, precision_score, recall_score, spec_valid}'

# Filter only failed tests
cat ota_evaluation_results.json | jq '.detailed_results[] | select(.spec_valid == false)'

# View safety-critical tests
cat ota_evaluation_results.json | jq '.detailed_results[] | select(.safety_class | startswith("ASIL"))'
```

### View Quick Summary

```bash
cat nl2dsl_quick_metrics.json
```

Output:
```json
{
  "system": "nl2dsl-agent",
  "precision": 87.5,
  "recall": 82.3,
  "breakage_rate": 2.1,
  "avg_latency_ms": 234.5,
  "success_rate": 95.0,
  "avg_cpu_pct": 15.2,
  "avg_mem_mb": 342.1,
  "safety_compliance": 96.5
}
```

## 🛠️ Customization

### Add Your Own Test Cases

Edit `ota_test_dataset.py`:

```python
def _generate_custom_cases(self):
    """Add your custom OTA scenarios."""
    cases = [
        OTATestCase(
            id="ota_custom_001",
            category=OTACategory.SINGLE_ECU,
            complexity=OTAComplexity.MEDIUM,
            prompt="Update V2X communication module for EU market",
            expected_ecus=["v2x_module"],
            expected_attributes={
                "v2x_module": ["sw_version", "region", "compliance"]
            },
            safety_class="ASIL-B",
            region="EU",
            description="V2X update with compliance checks"
        )
    ]
    self.test_cases.extend(cases)
```

Then add to `_generate_all_cases()`:
```python
def _generate_all_cases(self):
    # ... existing ...
    self._generate_custom_cases()  # Add this line
```

### Adjust Performance Expectations

Edit `ota_metrics_evaluator.py` to change scoring weights or add custom metrics.

## 📈 Interpreting Graph Comparisons

### CPU Usage Graph
- **Lower is better**
- Expected: nl2dsl-agent middle of pack
- Reason: LLM inference vs simple rule systems

### Memory Usage Graph
- **Lower is better**
- Expected: nl2dsl-agent moderate
- Reason: Model loading vs blockchain storage

### Duration/Latency Graph
- **Lower is better**
- Expected: nl2dsl-agent higher than rules, lower than blockchain
- Trade-off: Accuracy for speed

### Success Rate Graph
- **Higher is better**
- Expected: nl2dsl-agent top tier
- Strength: AI-driven correctness

### Precision/Recall (custom graphs)
- **Higher is better**
- Expected: nl2dsl-agent leading
- Strength: Knowledge base + semantic understanding

## 🚨 Troubleshooting

### Issue: OpenAI API errors

```bash
# Check API key
echo $OPENAI_API_KEY
# or
cat .env | grep OPENAI_API_KEY

# Set if missing
export OPENAI_API_KEY='your-key-here'
```

### Issue: Import errors

```bash
pip install -r requirements.txt

# Or install individually
pip install rich psutil matplotlib seaborn numpy pandas openai python-dotenv
```

### Issue: Graphs don't show nl2dsl-agent

```bash
# Re-run the update script
python update_ota_metrics_graph.py

# Verify metrics file exists
ls -la metrics_ota-main/nl2dsl_agent_metrics.json

# Re-generate graphs
cd metrics_ota-main && python metrics.py
```

### Issue: Low success rate

Check `ota_evaluation_results.json` for specific failures:
```bash
cat ota_evaluation_results.json | jq '.detailed_results[] | select(.spec_valid == false) | {id, validation_errors}'
```

Common issues:
- ECU type mismatch in knowledge base
- Missing safety class patterns
- Region-specific requirements not covered

## 📝 Next Steps

1. **Review Results**: Check `ota_evaluation_results.json` for detailed per-test analysis

2. **Compare Graphs**: Open PDFs in `metrics_ota-main/graphs/` to see how nl2dsl-agent ranks

3. **Iterate**:
   - Add test cases where agent performed poorly
   - Enhance knowledge base with missing patterns
   - Re-run benchmark

4. **Present**: Use generated graphs in papers/presentations

5. **Extend**:
   - Add more OTA systems to compare
   - Create domain-specific metrics
   - Test on real automotive scenarios

## 💡 Tips

- **First run**: Start with fewer test cases to verify setup (edit `ota_test_dataset.py`)
- **CI/CD**: Add `run_ota_benchmark.py` to your CI pipeline
- **Regression**: Re-run after knowledge base updates to track improvements
- **Comparison**: Focus on precision/recall vs traditional systems' speed

## 📚 Further Reading

- `OTA_METRICS_README.md` - Detailed documentation
- `ota_test_dataset.py` - Test case definitions
- `ota_metrics_evaluator.py` - Evaluation logic
- Original OTA papers for comparison context

## ✅ Success Criteria

Your benchmark is successful if:
- ✅ All tests complete without crashes
- ✅ Success rate > 90%
- ✅ Precision > 85%
- ✅ Recall > 80%
- ✅ Breakage rate < 5%
- ✅ Safety compliance > 95% (for ASIL tests)

## 🎉 You're Done!

You now have:
- ✅ Automated OTA benchmarking
- ✅ Comparison with 12 other OTA systems
- ✅ Publication-quality graphs
- ✅ Detailed performance metrics
- ✅ Safety compliance validation

Run anytime with:
```bash
python run_ota_benchmark.py
```
