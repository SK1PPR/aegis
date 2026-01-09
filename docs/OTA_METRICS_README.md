# nl2dsl-agent OTA Metrics Integration

## Overview

This integration allows nl2dsl-agent to be benchmarked against other OTA update systems
(TUF, Balena, RAUC, SWUpdate, etc.) using comparable metrics.

## Files Created

1. **ota_test_dataset.py** - Generates automotive OTA test scenarios
2. **ota_metrics_evaluator.py** - Evaluates nl2dsl-agent on OTA metrics
3. **run_ota_benchmark.py** - Main benchmark runner
4. **update_ota_metrics_graph.py** - Updates visualization scripts

## Running the Benchmark

### Step 1: Run the OTA Benchmark

```bash
python run_ota_benchmark.py
```

This will:
- Generate 20+ OTA test cases covering:
  - Single and multi-ECU updates
  - Safety-critical systems (ASIL-A through ASIL-D)
  - Different regions (US, EU, CN)
  - Rollback scenarios
  - Delta updates
- Evaluate nl2dsl-agent on each test case
- Generate metrics comparable to other OTA systems
- Output: `nl2dsl_agent_metrics.json`

### Step 2: Integrate with OTA Comparison Graphs

```bash
# Update metrics.py to include nl2dsl-agent
python update_ota_metrics_graph.py

# Copy metrics file to OTA directory
cp metrics_ota-main/nl2dsl_agent_metrics.json metrics_ota-main/

# Generate comparison graphs
cd metrics_ota-main
python metrics.py
```

### Step 3: View Results

Generated graphs will be in `metrics_ota-main/graphs/`:
- `01_cpu_usage_comparison.pdf` - CPU usage across all systems
- `02_memory_usage_comparison.pdf` - Memory usage comparison
- `03_duration_comparison.pdf` - Update duration times
- `04_latency_comparison.pdf` - Network latency
- `05_success_rates_comparison.pdf` - Success rates
- And more...

## Metrics Collected

### Core Metrics (Comparable to other OTA systems)

- **Precision** - Correctness of generated deployment specs (%)
- **Recall** - Completeness of expected features (%)
- **Breakage Rate** - Invalid/broken specs (%)
- **Success Rate** - Valid specs generated (%)

### Performance Metrics

- **CPU Usage** - Average CPU utilization (%)
- **Memory Usage** - RAM consumption (MB)
- **Latency** - Average generation time (ms)
- **Spec Size** - Bandwidth efficiency (KB)

### Safety Metrics (Automotive-specific)

- **Safety Compliance** - ASIL requirements met (%)
- **Rollback Coverage** - Rollback procedures included (%)
- **Pre-condition Checks** - Safety validations present (%)

## Expected Performance

Based on nl2dsl-agent's architecture:

### Strengths
- ✅ **High Precision** - AI-driven accuracy in spec generation
- ✅ **High Recall** - Knowledge base ensures completeness
- ✅ **Safety Compliance** - Automotive domain knowledge
- ✅ **Spec Size** - Efficient JSON format

### Trade-offs
- ⚠️ **Latency** - LLM inference adds overhead vs rule-based systems
- ⚠️ **CPU/Memory** - Higher than lightweight systems, lower than full blockchain

## Test Categories

The benchmark includes:

1. **Single ECU Updates** (simple)
   - Infotainment firmware
   - Basic ADAS updates

2. **Multi-ECU Updates** (complex)
   - Coordinated radar + camera updates
   - Gateway + telematics + infotainment

3. **Safety-Critical Updates** (ASIL-B/C/D)
   - Powertrain ECU (ASIL-D)
   - Brake control (ASIL-C)
   - ADAS systems (ASIL-B)

4. **Regional Updates**
   - China market (local protocols)
   - EU market (GDPR, eCall)
   - US market

5. **Rollback Scenarios**
   - Single ECU rollback
   - Multi-ECU coordinated rollback

6. **Delta Updates**
   - Bandwidth optimization
   - A/B partitioning

## Interpreting Results

### Good Performance Indicators

- Precision > 85%
- Recall > 80%
- Breakage Rate < 5%
- Success Rate > 90%
- Safety Compliance > 95% (for ASIL systems)

### Comparison Context

- **vs TUF/Uptane** - Similar security focus, nl2dsl adds automotive semantics
- **vs Balena/HawkBit** - nl2dsl is automotive-specific, others are general IoT
- **vs RAUC/SWUpdate** - nl2dsl is higher-level (specification vs implementation)
- **vs Blockchain OTA** - nl2dsl is faster, blockchain has immutability

## Customization

### Adding More Test Cases

Edit `ota_test_dataset.py`:

```python
def _generate_custom_cases(self):
    cases = [
        OTATestCase(
            id="ota_custom_001",
            category=OTACategory.CUSTOM,
            complexity=OTAComplexity.MEDIUM,
            prompt="Your custom OTA scenario",
            expected_ecus=["your_ecu"],
            expected_attributes={"your_ecu": ["attr1", "attr2"]},
            safety_class="ASIL-B",
            region="US",
            description="Description"
        )
    ]
    self.test_cases.extend(cases)
```

### Adjusting Metrics

Edit `ota_metrics_evaluator.py` to add custom metrics or adjust scoring.

## Troubleshooting

### Issue: No metrics file generated

**Solution**: Check that OPENAI_API_KEY is set in .env file

### Issue: Import errors

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Graphs don't include nl2dsl-agent

**Solution**:
1. Run `python update_ota_metrics_graph.py`
2. Ensure `nl2dsl_agent_metrics.json` is in `metrics_ota-main/`
3. Re-run `python metrics.py`

## Output Files

- `ota_test_dataset.json` - Generated test cases
- `ota_evaluation_results.json` - Detailed evaluation results
- `nl2dsl_agent_metrics.json` - Metrics in OTA-compatible format
- `nl2dsl_quick_metrics.json` - Quick reference summary

## Questions?

For issues or questions about the OTA benchmark integration, check:
1. The detailed results in `ota_evaluation_results.json`
2. Individual test case results
3. Console output during benchmark run
