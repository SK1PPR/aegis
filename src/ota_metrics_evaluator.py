#!/usr/bin/env python3
"""OTA-specific metrics evaluator for nl2dsl agent benchmarking."""

import time
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from .agent import DSLAgent
from .knowledge_base import ECUType, SafetyClass, DeploymentMode
from .ota_test_dataset import OTATestDatasetGenerator, OTATestCase


console = Console()


@dataclass
class OTATestResult:
    """Result for a single OTA test case."""
    test_id: str
    category: str
    complexity: str
    prompt: str
    safety_class: str
    region: str

    # Validity metrics
    spec_generated: bool
    spec_valid: bool
    validation_errors: str = ""

    # Precision metrics (correctness of what was generated)
    precision_score: float = 0.0  # % of generated ECUs that are correct
    ecu_precision: float = 0.0
    attribute_precision: float = 0.0

    # Recall metrics (completeness of expected items)
    recall_score: float = 0.0  # % of expected ECUs that were generated
    ecu_recall: float = 0.0
    attribute_recall: float = 0.0

    # Safety compliance
    safety_checks_present: bool = False
    rollback_procedure_present: bool = False
    pre_conditions_present: bool = False

    # Latency metrics
    generation_time: float = 0.0
    retrieval_time: float = 0.0

    # Size metrics (for bandwidth comparison)
    spec_size_bytes: int = 0

    # Generated spec
    generated_spec: Dict = None
    retrieved_patterns: List = None

    def __post_init__(self):
        if self.generated_spec is None:
            self.generated_spec = {}
        if self.retrieved_patterns is None:
            self.retrieved_patterns = []


@dataclass
class OTAMetricsReport:
    """Comprehensive OTA metrics report comparable to other OTA systems."""
    # Dataset info
    total_tests: int

    # Core metrics (matching OTA benchmark metrics)
    precision_percentage: float  # Correctness of generated specs
    recall_percentage: float  # Completeness of expected features
    breakage_rate: float  # % of invalid/broken specs

    # Performance metrics
    avg_latency: float  # Average generation time (ms)
    median_latency: float
    p95_latency: float
    p99_latency: float

    # Fields with defaults (must come after required fields)
    system_name: str = "nl2dsl-agent"

    # Resource metrics
    avg_cpu_usage: float = 0.0  # To be measured
    avg_memory_mb: float = 0.0  # To be measured
    avg_spec_size_kb: float = 0.0  # Bandwidth efficiency

    # Safety metrics (automotive-specific)
    safety_compliance_rate: float = 0.0
    rollback_coverage: float = 0.0

    # Success metrics
    success_rate: float = 0.0  # % of valid specs generated

    # Breakdown by category and complexity
    by_category: Dict[str, Dict[str, float]] = None
    by_complexity: Dict[str, Dict[str, float]] = None
    by_safety_class: Dict[str, Dict[str, float]] = None

    # Detailed results
    test_results: List[OTATestResult] = None

    def __post_init__(self):
        if self.by_category is None:
            self.by_category = {}
        if self.by_complexity is None:
            self.by_complexity = {}
        if self.by_safety_class is None:
            self.by_safety_class = {}
        if self.test_results is None:
            self.test_results = []


class OTAMetricsEvaluator:
    """Evaluate nl2dsl agent on OTA-specific metrics."""

    def __init__(self):
        """Initialize evaluator."""
        self.agent = None
        self.results: List[OTATestResult] = []

    def _reset_agent(self):
        """Reset agent for fresh conversation."""
        self.agent = DSLAgent()

    def _map_ecu_type(self, ecu_name: str) -> ECUType:
        """Map ECU name to ECUType enum."""
        mapping = {
            "infotainment": ECUType.INFOTAINMENT,
            "adas_camera": ECUType.ADAS,
            "adas_radar": ECUType.ADAS,
            "adas_lidar": ECUType.ADAS,
            "adas_lka": ECUType.ADAS,  # Lane keeping assist
            "adas_fusion": ECUType.ADAS,
            "gateway": ECUType.GATEWAY,
            "telematics": ECUType.TELEMATICS,
            "powertrain_ecu": ECUType.POWERTRAIN,
            "engine_ecu": ECUType.POWERTRAIN,
            "motor_ecu": ECUType.POWERTRAIN,
            "battery_ecu": ECUType.POWERTRAIN,
            "transmission_ecu": ECUType.POWERTRAIN,
            "brake_ecu": ECUType.BODY_CONTROL,
            "emergency_call": ECUType.TELEMATICS,
        }
        return mapping.get(ecu_name, ECUType.INFOTAINMENT)

    def _map_safety_class(self, safety_str: str) -> SafetyClass:
        """Map safety class string to enum."""
        mapping = {
            "QM": SafetyClass.QM,
            "ASIL-A": SafetyClass.ASIL_A,
            "ASIL-B": SafetyClass.ASIL_B,
            "ASIL-C": SafetyClass.ASIL_C,
            "ASIL-D": SafetyClass.ASIL_D,
        }
        return mapping.get(safety_str, SafetyClass.QM)

    def _calculate_precision_recall(
        self,
        expected_ecus: List[str],
        expected_attrs: Dict[str, List[str]],
        generated_spec: Dict
    ) -> Tuple[float, float, float, float, float, float]:
        """
        Calculate precision and recall metrics.

        Precision: Of what was generated, how much is correct?
        Recall: Of what was expected, how much was generated?
        """
        if not generated_spec or "update_package" not in generated_spec:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        # Extract generated ECUs
        generated_ecus = set()
        generated_attrs = {}

        # Check update_package for ECU info
        update_pkg = generated_spec.get("update_package", {})
        if "target_ecu" in update_pkg:
            ecu_name = update_pkg["target_ecu"].lower().replace("-", "_")
            generated_ecus.add(ecu_name)
            generated_attrs[ecu_name] = list(update_pkg.keys())

        # Check for multi-ECU updates
        if "target_ecus" in update_pkg:
            for ecu in update_pkg["target_ecus"]:
                ecu_name = ecu.lower().replace("-", "_")
                generated_ecus.add(ecu_name)
                generated_attrs[ecu_name] = list(update_pkg.keys())

        # Calculate ECU precision and recall
        expected_ecus_set = set(ecu.lower() for ecu in expected_ecus)

        # ECU precision: % of generated ECUs that are correct
        if generated_ecus:
            correct_ecus = generated_ecus & expected_ecus_set
            ecu_precision = len(correct_ecus) / len(generated_ecus)
        else:
            ecu_precision = 0.0

        # ECU recall: % of expected ECUs that were generated
        if expected_ecus_set:
            correct_ecus = generated_ecus & expected_ecus_set
            ecu_recall = len(correct_ecus) / len(expected_ecus_set)
        else:
            ecu_recall = 0.0

        # Calculate attribute precision and recall
        attr_precision_scores = []
        attr_recall_scores = []

        for ecu in expected_ecus_set:
            if ecu in generated_attrs and ecu in expected_attrs:
                gen_attrs = set(generated_attrs[ecu])
                exp_attrs = set(expected_attrs[ecu])

                if gen_attrs:
                    correct_attrs = gen_attrs & exp_attrs
                    attr_precision_scores.append(len(correct_attrs) / len(gen_attrs))

                if exp_attrs:
                    correct_attrs = gen_attrs & exp_attrs
                    attr_recall_scores.append(len(correct_attrs) / len(exp_attrs))

        attr_precision = sum(attr_precision_scores) / len(attr_precision_scores) if attr_precision_scores else 0.0
        attr_recall = sum(attr_recall_scores) / len(attr_recall_scores) if attr_recall_scores else 0.0

        # Overall scores
        precision = (ecu_precision + attr_precision) / 2
        recall = (ecu_recall + attr_recall) / 2

        return precision, recall, ecu_precision, ecu_recall, attr_precision, attr_recall

    def _check_safety_compliance(self, spec: Dict, safety_class: str) -> Tuple[bool, bool, bool]:
        """Check if safety requirements are present."""
        has_safety_checks = False
        has_rollback = False
        has_preconditions = False

        if not spec:
            return False, False, False

        # Check for safety checks
        if "verification" in spec.get("post_conditions", {}):
            has_safety_checks = True
        if "safety_checks" in spec.get("installation", {}):
            has_safety_checks = True

        # Check for rollback procedure
        if "rollback" in spec.get("installation", {}):
            has_rollback = True
        if "rollback_procedure" in spec:
            has_rollback = True

        # Check for pre-conditions
        if "pre_conditions" in spec and spec["pre_conditions"]:
            has_preconditions = True

        return has_safety_checks, has_rollback, has_preconditions

    def evaluate_single_case(self, test_case: OTATestCase) -> OTATestResult:
        """Evaluate a single OTA test case."""
        # Reset agent for each test
        self._reset_agent()

        # Map test case to agent parameters
        device_type = self._map_ecu_type(test_case.expected_ecus[0])
        safety_class = self._map_safety_class(test_case.safety_class)

        # Measure generation time
        start_time = time.time()

        try:
            # Extract version from expected attributes if available
            sw_version = "2.0.0"  # Default version
            hardware_revision = "rev_A"  # Default hardware revision

            # Try to extract from expected attributes
            for ecu in test_case.expected_ecus:
                if ecu in test_case.expected_attributes:
                    attrs = test_case.expected_attributes[ecu]
                    if 'sw_version' in attrs:
                        # For now use a compatible version from knowledge base
                        sw_version = "2.5.1" if device_type == ECUType.INFOTAINMENT else "3.2.0"
                    if 'hardware_revision' in attrs:
                        hardware_revision = "rev_A"
                    break

            response = self.agent.chat(
                user_message=test_case.prompt,
                device_type=device_type,
                sw_version=sw_version,
                safety_class=safety_class,
                region=test_case.region,
                hardware_revision=hardware_revision,
                deployment_mode=DeploymentMode.A_B  # Use A/B deployment mode
            )
            generation_time = time.time() - start_time

            # Extract spec
            spec = response.deployment_spec if response else None
            spec_generated = spec is not None
            spec_valid = response.is_valid if response else False

            # Calculate precision and recall
            precision, recall, ecu_prec, ecu_rec, attr_prec, attr_rec = \
                self._calculate_precision_recall(
                    test_case.expected_ecus,
                    test_case.expected_attributes,
                    spec or {}
                )

            # Check safety compliance
            has_safety, has_rollback, has_precond = \
                self._check_safety_compliance(spec or {}, test_case.safety_class)

            # Calculate spec size
            spec_size = len(json.dumps(spec)) if spec else 0

            result = OTATestResult(
                test_id=test_case.id,
                category=test_case.category.value,
                complexity=test_case.complexity.value,
                prompt=test_case.prompt,
                safety_class=test_case.safety_class,
                region=test_case.region,
                spec_generated=spec_generated,
                spec_valid=spec_valid,
                validation_errors="" if spec_valid else "Invalid or missing spec",
                precision_score=precision * 100,
                recall_score=recall * 100,
                ecu_precision=ecu_prec * 100,
                ecu_recall=ecu_rec * 100,
                attribute_precision=attr_prec * 100,
                attribute_recall=attr_rec * 100,
                safety_checks_present=has_safety,
                rollback_procedure_present=has_rollback,
                pre_conditions_present=has_precond,
                generation_time=generation_time * 1000,  # Convert to ms
                retrieval_time=0.0,  # Could measure separately
                spec_size_bytes=spec_size,
                generated_spec=spec,
                retrieved_patterns=response.retrieved_patterns if response else []
            )

        except Exception as e:
            generation_time = time.time() - start_time
            result = OTATestResult(
                test_id=test_case.id,
                category=test_case.category.value,
                complexity=test_case.complexity.value,
                prompt=test_case.prompt,
                safety_class=test_case.safety_class,
                region=test_case.region,
                spec_generated=False,
                spec_valid=False,
                validation_errors=str(e),
                generation_time=generation_time * 1000
            )

        return result

    def evaluate_dataset(
        self,
        test_cases: List[OTATestCase],
        save_results: bool = True
    ) -> OTAMetricsReport:
        """Evaluate entire OTA test dataset."""
        self.results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[cyan]Evaluating {len(test_cases)} OTA test cases...",
                total=len(test_cases)
            )

            for test_case in test_cases:
                result = self.evaluate_single_case(test_case)
                self.results.append(result)
                progress.update(task, advance=1)

        # Calculate aggregate metrics
        report = self._generate_report()

        # Save results
        if save_results:
            self._save_results(report)

        return report

    def _generate_report(self) -> OTAMetricsReport:
        """Generate comprehensive metrics report."""
        if not self.results:
            return OTAMetricsReport(
                total_tests=0,
                precision_percentage=0.0,
                recall_percentage=0.0,
                breakage_rate=0.0,
                avg_latency=0.0,
                median_latency=0.0,
                p95_latency=0.0,
                p99_latency=0.0
            )

        # Core metrics
        valid_specs = [r for r in self.results if r.spec_valid]
        total = len(self.results)

        precision_scores = [r.precision_score for r in self.results if r.spec_generated]
        recall_scores = [r.recall_score for r in self.results if r.spec_generated]

        precision_pct = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0
        recall_pct = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0

        breakage_rate = ((total - len(valid_specs)) / total * 100) if total > 0 else 0.0
        success_rate = (len(valid_specs) / total * 100) if total > 0 else 0.0

        # Latency metrics
        latencies = [r.generation_time for r in self.results]
        latencies_sorted = sorted(latencies)

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        median_latency = latencies_sorted[len(latencies_sorted)//2] if latencies_sorted else 0.0
        p95_idx = int(len(latencies_sorted) * 0.95)
        p99_idx = int(len(latencies_sorted) * 0.99)
        p95_latency = latencies_sorted[p95_idx] if latencies_sorted else 0.0
        p99_latency = latencies_sorted[p99_idx] if latencies_sorted else 0.0

        # Size metrics
        spec_sizes = [r.spec_size_bytes for r in self.results if r.spec_generated]
        avg_spec_size_kb = (sum(spec_sizes) / len(spec_sizes) / 1024) if spec_sizes else 0.0

        # Safety metrics
        safety_critical = [r for r in self.results if r.safety_class.startswith("ASIL")]
        if safety_critical:
            safety_compliant = [r for r in safety_critical if r.safety_checks_present]
            safety_compliance_rate = (len(safety_compliant) / len(safety_critical) * 100)

            with_rollback = [r for r in safety_critical if r.rollback_procedure_present]
            rollback_coverage = (len(with_rollback) / len(safety_critical) * 100)
        else:
            safety_compliance_rate = 0.0
            rollback_coverage = 0.0

        # Breakdown by category
        by_category = {}
        for category in set(r.category for r in self.results):
            cat_results = [r for r in self.results if r.category == category]
            cat_valid = [r for r in cat_results if r.spec_valid]
            cat_precision = [r.precision_score for r in cat_results if r.spec_generated]
            cat_recall = [r.recall_score for r in cat_results if r.spec_generated]

            by_category[category] = {
                "success_rate": (len(cat_valid) / len(cat_results) * 100) if cat_results else 0.0,
                "precision": (sum(cat_precision) / len(cat_precision)) if cat_precision else 0.0,
                "recall": (sum(cat_recall) / len(cat_recall)) if cat_recall else 0.0,
                "count": len(cat_results)
            }

        # Breakdown by complexity
        by_complexity = {}
        for complexity in set(r.complexity for r in self.results):
            comp_results = [r for r in self.results if r.complexity == complexity]
            comp_valid = [r for r in comp_results if r.spec_valid]
            comp_precision = [r.precision_score for r in comp_results if r.spec_generated]
            comp_recall = [r.recall_score for r in comp_results if r.spec_generated]

            by_complexity[complexity] = {
                "success_rate": (len(comp_valid) / len(comp_results) * 100) if comp_results else 0.0,
                "precision": (sum(comp_precision) / len(comp_precision)) if comp_precision else 0.0,
                "recall": (sum(comp_recall) / len(comp_recall)) if comp_recall else 0.0,
                "count": len(comp_results)
            }

        # Breakdown by safety class
        by_safety = {}
        for safety in set(r.safety_class for r in self.results):
            safe_results = [r for r in self.results if r.safety_class == safety]
            safe_valid = [r for r in safe_results if r.spec_valid]
            safe_precision = [r.precision_score for r in safe_results if r.spec_generated]
            safe_recall = [r.recall_score for r in safe_results if r.spec_generated]

            by_safety[safety] = {
                "success_rate": (len(safe_valid) / len(safe_results) * 100) if safe_results else 0.0,
                "precision": (sum(safe_precision) / len(safe_precision)) if safe_precision else 0.0,
                "recall": (sum(safe_recall) / len(safe_recall)) if safe_recall else 0.0,
                "count": len(safe_results)
            }

        return OTAMetricsReport(
            total_tests=total,
            precision_percentage=precision_pct,
            recall_percentage=recall_pct,
            breakage_rate=breakage_rate,
            success_rate=success_rate,
            avg_latency=avg_latency,
            median_latency=median_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            avg_spec_size_kb=avg_spec_size_kb,
            safety_compliance_rate=safety_compliance_rate,
            rollback_coverage=rollback_coverage,
            by_category=by_category,
            by_complexity=by_complexity,
            by_safety_class=by_safety,
            test_results=self.results
        )

    def _save_results(self, report: OTAMetricsReport):
        """Save evaluation results to JSON."""

        # Convert test results to dict, handling enums and complex objects
        detailed_results = []
        for r in report.test_results:
            result_dict = asdict(r)
            # Convert retrieved_patterns to simple list (just count them)
            if 'retrieved_patterns' in result_dict:
                # Just store the count, not the full pattern objects
                pattern_count = len(result_dict['retrieved_patterns']) if result_dict['retrieved_patterns'] else 0
                result_dict['retrieved_patterns'] = []
                result_dict['retrieved_pattern_count'] = pattern_count
            detailed_results.append(result_dict)

        results_data = {
            "system": report.system_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": report.total_tests,
                "precision": report.precision_percentage,
                "recall": report.recall_percentage,
                "breakage_rate": report.breakage_rate,
                "success_rate": report.success_rate,
                "avg_latency_ms": report.avg_latency,
                "median_latency_ms": report.median_latency,
                "p95_latency_ms": report.p95_latency,
                "p99_latency_ms": report.p99_latency,
                "avg_spec_size_kb": report.avg_spec_size_kb,
                "safety_compliance_rate": report.safety_compliance_rate,
                "rollback_coverage": report.rollback_coverage
            },
            "by_category": report.by_category,
            "by_complexity": report.by_complexity,
            "by_safety_class": report.by_safety_class,
            "detailed_results": detailed_results
        }

        output_path = Path("results") / "ota_evaluation_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)

        console.print(f"\n✓ Results saved to {output_path}")

    def print_report(self, report: OTAMetricsReport):
        """Print comprehensive metrics report."""
        console.print("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]  OTA METRICS EVALUATION REPORT - nl2dsl-agent         [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]\n")

        # Core Metrics Table
        table = Table(title="Core Metrics (OTA Benchmark Compatible)")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        table.add_column("Unit", style="yellow")

        table.add_row("Precision", f"{report.precision_percentage:.2f}", "%")
        table.add_row("Recall", f"{report.recall_percentage:.2f}", "%")
        table.add_row("Breakage Rate", f"{report.breakage_rate:.2f}", "%")
        table.add_row("Success Rate", f"{report.success_rate:.2f}", "%")
        table.add_row("Avg Latency", f"{report.avg_latency:.2f}", "ms")
        table.add_row("Median Latency", f"{report.median_latency:.2f}", "ms")
        table.add_row("P95 Latency", f"{report.p95_latency:.2f}", "ms")
        table.add_row("P99 Latency", f"{report.p99_latency:.2f}", "ms")
        table.add_row("Avg Spec Size", f"{report.avg_spec_size_kb:.2f}", "KB")

        console.print(table)

        # Safety Metrics Table
        console.print()
        safety_table = Table(title="Safety & Compliance Metrics")
        safety_table.add_column("Metric", style="cyan")
        safety_table.add_column("Value", style="green", justify="right")

        safety_table.add_row("Safety Compliance Rate", f"{report.safety_compliance_rate:.2f}%")
        safety_table.add_row("Rollback Coverage", f"{report.rollback_coverage:.2f}%")

        console.print(safety_table)

        # Category Breakdown
        console.print("\n[bold]Performance by Category:[/bold]")
        cat_table = Table()
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Tests", justify="right")
        cat_table.add_column("Success", justify="right")
        cat_table.add_column("Precision", justify="right")
        cat_table.add_column("Recall", justify="right")

        for cat, metrics in report.by_category.items():
            cat_table.add_row(
                cat,
                str(metrics["count"]),
                f"{metrics['success_rate']:.1f}%",
                f"{metrics['precision']:.1f}%",
                f"{metrics['recall']:.1f}%"
            )

        console.print(cat_table)

        # Complexity Breakdown
        console.print("\n[bold]Performance by Complexity:[/bold]")
        comp_table = Table()
        comp_table.add_column("Complexity", style="cyan")
        comp_table.add_column("Tests", justify="right")
        comp_table.add_column("Success", justify="right")
        comp_table.add_column("Precision", justify="right")
        comp_table.add_column("Recall", justify="right")

        for comp, metrics in report.by_complexity.items():
            comp_table.add_row(
                comp,
                str(metrics["count"]),
                f"{metrics['success_rate']:.1f}%",
                f"{metrics['precision']:.1f}%",
                f"{metrics['recall']:.1f}%"
            )

        console.print(comp_table)

        console.print("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]\n")


if __name__ == "__main__":
    console.print("\n[bold cyan]OTA Metrics Evaluator[/bold cyan]\n")
    console.print("This will evaluate the nl2dsl agent on OTA-specific benchmarks")
    console.print("comparable to TUF, Balena, RAUC, etc.\n")

    # Generate test dataset
    console.print("[1/2] Generating OTA test dataset...")
    generator = OTATestDatasetGenerator()
    test_cases = generator.get_all_cases()
    stats = generator.get_statistics()
    console.print(f"  ✓ {stats['total_cases']} test cases generated\n")

    # Run evaluation
    console.print("[2/2] Running evaluation...")
    evaluator = OTAMetricsEvaluator()
    report = evaluator.evaluate_dataset(test_cases, save_results=True)

    # Print report
    evaluator.print_report(report)
