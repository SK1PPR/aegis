"""Comprehensive metrics evaluation for NL2DSL system."""

import time
import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from agent import DSLAgent
from dataset_generator import DatasetGenerator, TestCase
from grammar_validator import validate_and_explain
from dsl_generator import generate_dsl


console = Console()


@dataclass
class TestResult:
    """Result for a single test case."""
    test_id: str
    category: str
    complexity: str
    prompt: str
    
    # Validity metrics
    grammar_valid: bool
    parser_valid: bool
    grammar_errors: str = ""
    parser_errors: str = ""
    
    # Completeness metrics
    services_generated: List[str] = None
    services_expected: List[str] = None
    attributes_generated: Dict[str, List[str]] = None
    attributes_expected: Dict[str, List[str]] = None
    completeness_score: float = 0.0
    
    # Latency
    generation_time: float = 0.0
    
    # Generated code
    generated_code: str = ""
    
    def __post_init__(self):
        if self.services_generated is None:
            self.services_generated = []
        if self.services_expected is None:
            self.services_expected = []
        if self.attributes_generated is None:
            self.attributes_generated = {}
        if self.attributes_expected is None:
            self.attributes_expected = {}


@dataclass
class MetricsReport:
    """Comprehensive metrics report."""
    # Overall metrics
    total_tests: int
    
    # Validity metrics
    validity_percentage: float
    grammar_pass_rate: float
    parser_pass_rate: float
    
    # Completeness metrics
    completeness_percentage: float
    avg_service_coverage: float
    avg_attribute_coverage: float
    
    # Extensibility metrics (ability to handle new fields)
    extensibility_percentage: float
    
    # Latency metrics
    avg_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    
    # Breakdown by category
    by_category: Dict[str, Dict[str, float]] = None
    by_complexity: Dict[str, Dict[str, float]] = None
    
    # Detailed results
    test_results: List[TestResult] = None
    
    def __post_init__(self):
        if self.by_category is None:
            self.by_category = {}
        if self.by_complexity is None:
            self.by_complexity = {}
        if self.test_results is None:
            self.test_results = []


class MetricsEvaluator:
    """Evaluate NL2DSL system on comprehensive metrics."""
    
    def __init__(self, parser_path: str = None):
        """Initialize evaluator."""
        self.parser_path = parser_path or self._find_parser()
        self.agent = None
        self.results: List[TestResult] = []
        
    def _find_parser(self) -> str:
        """Find the Rust parser executable."""
        parser_paths = [
            "../container-lang/target/release/container-lang",
            "../container-lang/target/debug/container-lang",
        ]
        for path in parser_paths:
            full_path = Path(path).resolve()
            if full_path.exists():
                return str(full_path)
        return None
    
    def _reset_agent(self):
        """Reset agent for fresh conversation."""
        self.agent = DSLAgent()
    
    def _calculate_completeness(
        self,
        expected_services: List[str],
        expected_attrs: Dict[str, List[str]],
        program
    ) -> Tuple[float, List[str], Dict[str, List[str]]]:
        """Calculate completeness score."""
        if not program or not program.services:
            return 0.0, [], {}
        
        generated_services = [s.name for s in program.services]
        generated_attrs = {}
        
        for service in program.services:
            attrs = ["image"]  # Always present
            if service.replicas > 1:
                attrs.append("replicas")
            if service.ports:
                attrs.append("ports")
            if service.env:
                attrs.append("env")
            if service.volumes:
                attrs.append("volumes")
            generated_attrs[service.name] = attrs
        
        # Calculate service coverage
        service_matches = len(set(expected_services) & set(generated_services))
        service_coverage = service_matches / len(expected_services) if expected_services else 0
        
        # Calculate attribute coverage
        attr_scores = []
        for service_name in expected_services:
            if service_name in expected_attrs and service_name in generated_attrs:
                expected_set = set(expected_attrs[service_name])
                generated_set = set(generated_attrs[service_name])
                matches = len(expected_set & generated_set)
                score = matches / len(expected_set) if expected_set else 0
                attr_scores.append(score)
        
        attr_coverage = sum(attr_scores) / len(attr_scores) if attr_scores else 0
        
        # Overall completeness: average of service and attribute coverage
        completeness = (service_coverage + attr_coverage) / 2
        
        return completeness, generated_services, generated_attrs
    
    def _validate_with_parser(self, dsl_code: str) -> Tuple[bool, str]:
        """Validate DSL code with Rust parser."""
        if not self.parser_path:
            return False, "Parser not available"
        
        try:
            temp_file = "/tmp/eval_dsl.container"
            with open(temp_file, "w") as f:
                f.write(dsl_code)
            
            result = subprocess.run(
                [self.parser_path, temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True, "Valid"
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def evaluate_test_case(self, test_case: TestCase) -> TestResult:
        """Evaluate a single test case."""
        result = TestResult(
            test_id=test_case.id,
            category=test_case.category,
            complexity=test_case.complexity,
            prompt=test_case.prompt,
            services_expected=test_case.expected_services,
            attributes_expected=test_case.expected_attributes,
            grammar_valid=False,
            parser_valid=False
        )
        
        try:
            # Reset agent for fresh start
            self._reset_agent()
            
            # Measure generation time
            start_time = time.time()
            response = self.agent.chat(test_case.prompt)
            result.generation_time = time.time() - start_time
            
            # Check if program was generated
            if not response.program:
                # Try one more time with explicit generation request
                response = self.agent.chat("Please generate the DSL code now")
                result.generation_time += time.time() - start_time
            
            if response.program:
                # Grammar validation
                is_valid, message = validate_and_explain(response.program)
                result.grammar_valid = is_valid
                result.grammar_errors = "" if is_valid else message
                
                # Generate code
                code = generate_dsl(response.program)
                result.generated_code = code
                
                # Parser validation
                if self.parser_path:
                    parser_valid, parser_msg = self._validate_with_parser(code)
                    result.parser_valid = parser_valid
                    result.parser_errors = "" if parser_valid else parser_msg
                
                # Completeness calculation
                completeness, gen_services, gen_attrs = self._calculate_completeness(
                    test_case.expected_services,
                    test_case.expected_attributes,
                    response.program
                )
                result.completeness_score = completeness
                result.services_generated = gen_services
                result.attributes_generated = gen_attrs
            
        except Exception as e:
            result.grammar_errors = f"Exception: {str(e)}"
        
        return result
    
    def evaluate_dataset(
        self,
        dataset: List[TestCase],
        save_results: bool = True
    ) -> MetricsReport:
        """Evaluate entire dataset and generate report."""
        self.results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Evaluating test cases...", total=len(dataset))
            
            for test_case in dataset:
                result = self.evaluate_test_case(test_case)
                self.results.append(result)
                progress.advance(task)
        
        # Generate report
        report = self._generate_report()
        
        if save_results:
            self._save_results(report)
        
        return report
    
    def _generate_report(self) -> MetricsReport:
        """Generate comprehensive metrics report."""
        if not self.results:
            return MetricsReport(
                total_tests=0,
                validity_percentage=0,
                grammar_pass_rate=0,
                parser_pass_rate=0,
                completeness_percentage=0,
                avg_service_coverage=0,
                avg_attribute_coverage=0,
                extensibility_percentage=0,
                avg_latency=0,
                median_latency=0,
                p95_latency=0,
                p99_latency=0
            )
        
        # Validity metrics
        grammar_valid = sum(1 for r in self.results if r.grammar_valid)
        parser_valid = sum(1 for r in self.results if r.parser_valid)
        both_valid = sum(1 for r in self.results if r.grammar_valid and r.parser_valid)
        
        # Completeness metrics
        completeness_scores = [r.completeness_score for r in self.results]
        avg_completeness = sum(completeness_scores) / len(completeness_scores)
        
        # Latency metrics
        latencies = sorted([r.generation_time for r in self.results])
        avg_latency = sum(latencies) / len(latencies)
        median_latency = latencies[len(latencies) // 2]
        p95_index = int(len(latencies) * 0.95)
        p99_index = int(len(latencies) * 0.99)
        
        # Extensibility: measure performance on edge cases and complex scenarios
        edge_complex = [r for r in self.results if r.complexity in ["complex"] or r.category == "edge_case"]
        extensibility = sum(1 for r in edge_complex if r.grammar_valid) / len(edge_complex) if edge_complex else 0
        
        # Category and complexity breakdowns
        by_category = self._breakdown_by_field("category")
        by_complexity = self._breakdown_by_field("complexity")
        
        return MetricsReport(
            total_tests=len(self.results),
            validity_percentage=(both_valid / len(self.results)) * 100,
            grammar_pass_rate=(grammar_valid / len(self.results)) * 100,
            parser_pass_rate=(parser_valid / len(self.results)) * 100,
            completeness_percentage=avg_completeness * 100,
            avg_service_coverage=avg_completeness * 100,  # Simplified
            avg_attribute_coverage=avg_completeness * 100,  # Simplified
            extensibility_percentage=extensibility * 100,
            avg_latency=avg_latency,
            median_latency=median_latency,
            p95_latency=latencies[p95_index] if p95_index < len(latencies) else latencies[-1],
            p99_latency=latencies[p99_index] if p99_index < len(latencies) else latencies[-1],
            by_category=by_category,
            by_complexity=by_complexity,
            test_results=self.results
        )
    
    def _breakdown_by_field(self, field: str) -> Dict[str, Dict[str, float]]:
        """Generate metrics breakdown by category or complexity."""
        breakdown = {}
        field_values = set(getattr(r, field) for r in self.results)
        
        for value in field_values:
            filtered = [r for r in self.results if getattr(r, field) == value]
            if not filtered:
                continue
            
            grammar_valid = sum(1 for r in filtered if r.grammar_valid)
            completeness = sum(r.completeness_score for r in filtered) / len(filtered)
            avg_latency = sum(r.generation_time for r in filtered) / len(filtered)
            
            breakdown[value] = {
                "total": len(filtered),
                "grammar_pass_rate": (grammar_valid / len(filtered)) * 100,
                "completeness": completeness * 100,
                "avg_latency": avg_latency
            }
        
        return breakdown
    
    def _save_results(self, report: MetricsReport):
        """Save evaluation results to files."""
        # Save detailed report
        report_dict = asdict(report)
        with open("evaluation_report.json", "w") as f:
            json.dump(report_dict, f, indent=2)
        
        # Save summary
        summary = {
            "total_tests": report.total_tests,
            "validity_percentage": round(report.validity_percentage, 2),
            "grammar_pass_rate": round(report.grammar_pass_rate, 2),
            "parser_pass_rate": round(report.parser_pass_rate, 2),
            "completeness_percentage": round(report.completeness_percentage, 2),
            "extensibility_percentage": round(report.extensibility_percentage, 2),
            "avg_latency_seconds": round(report.avg_latency, 3),
            "median_latency_seconds": round(report.median_latency, 3),
            "p95_latency_seconds": round(report.p95_latency, 3),
        }
        with open("evaluation_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        console.print("\n[green]Results saved to:[/green]")
        console.print("  - evaluation_report.json (detailed)")
        console.print("  - evaluation_summary.json (summary)")
    
    def print_report(self, report: MetricsReport):
        """Print formatted report to console."""
        console.print("\n[bold cyan]═══ EVALUATION REPORT ═══[/bold cyan]\n")
        
        # Overall metrics table
        table = Table(title="Overall Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")
        table.add_column("Description", style="dim")
        
        table.add_row(
            "Validity",
            f"{report.validity_percentage:.2f}%",
            "Configurations passing all checks"
        )
        table.add_row(
            "Grammar Pass Rate",
            f"{report.grammar_pass_rate:.2f}%",
            "Grammar correctness"
        )
        table.add_row(
            "Parser Pass Rate",
            f"{report.parser_pass_rate:.2f}%",
            "Rust parser validation"
        )
        table.add_row(
            "Completeness",
            f"{report.completeness_percentage:.2f}%",
            "Required attributes generated"
        )
        table.add_row(
            "Extensibility",
            f"{report.extensibility_percentage:.2f}%",
            "Complex/edge case handling"
        )
        table.add_row(
            "Avg Latency",
            f"{report.avg_latency:.3f}s",
            "Average generation time"
        )
        table.add_row(
            "Median Latency",
            f"{report.median_latency:.3f}s",
            "Median generation time"
        )
        table.add_row(
            "P95 Latency",
            f"{report.p95_latency:.3f}s",
            "95th percentile"
        )
        table.add_row(
            "P99 Latency",
            f"{report.p99_latency:.3f}s",
            "99th percentile"
        )
        
        console.print(table)
        
        # Category breakdown
        if report.by_category:
            console.print("\n[bold cyan]═══ BY CATEGORY ═══[/bold cyan]\n")
            cat_table = Table(show_header=True, header_style="bold magenta")
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Tests", justify="right")
            cat_table.add_column("Grammar %", justify="right", style="green")
            cat_table.add_column("Complete %", justify="right", style="blue")
            cat_table.add_column("Latency", justify="right", style="yellow")
            
            for cat, metrics in report.by_category.items():
                cat_table.add_row(
                    cat,
                    str(metrics["total"]),
                    f"{metrics['grammar_pass_rate']:.1f}%",
                    f"{metrics['completeness']:.1f}%",
                    f"{metrics['avg_latency']:.3f}s"
                )
            
            console.print(cat_table)
        
        # Complexity breakdown
        if report.by_complexity:
            console.print("\n[bold cyan]═══ BY COMPLEXITY ═══[/bold cyan]\n")
            comp_table = Table(show_header=True, header_style="bold magenta")
            comp_table.add_column("Complexity", style="cyan")
            comp_table.add_column("Tests", justify="right")
            comp_table.add_column("Grammar %", justify="right", style="green")
            comp_table.add_column("Complete %", justify="right", style="blue")
            comp_table.add_column("Latency", justify="right", style="yellow")
            
            for comp, metrics in report.by_complexity.items():
                comp_table.add_row(
                    comp,
                    str(metrics["total"]),
                    f"{metrics['grammar_pass_rate']:.1f}%",
                    f"{metrics['completeness']:.1f}%",
                    f"{metrics['avg_latency']:.3f}s"
                )
            
            console.print(comp_table)
        
        console.print()


def main():
    """Main evaluation script."""
    console.print("[bold cyan]NL2DSL System Evaluation[/bold cyan]\n")
    
    # Generate dataset
    console.print("[yellow]Generating test dataset...[/yellow]")
    generator = DatasetGenerator()
    dataset = generator.get_all_cases()
    generator.save_to_json("test_dataset.json")
    
    stats = generator.get_statistics()
    console.print(f"[green]Generated {stats['total_cases']} test cases[/green]")
    console.print(f"Categories: {', '.join(stats['by_category'].keys())}")
    console.print(f"Complexity levels: {', '.join(stats['by_complexity'].keys())}\n")
    
    # Run evaluation
    console.print("[yellow]Starting evaluation...[/yellow]\n")
    evaluator = MetricsEvaluator()
    
    if not evaluator.parser_path:
        console.print("[yellow]⚠ Rust parser not found - parser validation will be skipped[/yellow]")
        console.print("Build it with: cd ../container-lang && cargo build --release\n")
    
    report = evaluator.evaluate_dataset(dataset)
    
    # Print results
    evaluator.print_report(report)
    
    console.print("[green]✓ Evaluation complete![/green]\n")


if __name__ == "__main__":
    main()