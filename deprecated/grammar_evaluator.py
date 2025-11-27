"""Evaluate grammar-based approach using CFG and Lark."""

import time
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from grammar_based_generator import GrammarBasedGenerator
from dataset_generator import TestCase
from schema import Program, Service, PortMapping, EnvVar
from grammar_validator import validate_and_explain

console = Console()


@dataclass
class GrammarResult:
    """Result for grammar-based evaluation."""
    test_id: str
    category: str
    complexity: str
    prompt: str
    
    # Validity metrics
    grammar_valid: bool
    parser_valid: bool
    lark_valid: bool
    grammar_errors: str = ""
    parser_errors: str = ""
    lark_errors: str = ""
    
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
class GrammarMetrics:
    """Metrics for grammar-based approach."""
    total_tests: int
    validity_percentage: float
    grammar_pass_rate: float
    parser_pass_rate: float
    lark_pass_rate: float
    completeness_percentage: float
    avg_service_coverage: float
    avg_attribute_coverage: float
    extensibility_percentage: float
    avg_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    by_category: Dict[str, Dict[str, float]] = None
    by_complexity: Dict[str, Dict[str, float]] = None
    
    def __post_init__(self):
        if self.by_category is None:
            self.by_category = {}
        if self.by_complexity is None:
            self.by_complexity = {}


class GrammarEvaluator:
    """Evaluate grammar-based DSL generation."""
    
    def __init__(self, parser_path: str = None):
        """Initialize evaluator."""
        self.generator = GrammarBasedGenerator()
        self.parser_path = parser_path or self._find_parser()
        self.results: List[GrammarResult] = []
    
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
    
    def _parse_dsl_to_program(self, dsl_code: str) -> Optional[Program]:
        """Parse DSL code to Program object."""
        try:
            services = []
            current_service = None
            
            lines = dsl_code.strip().split('\n')
            for line in lines:
                line = line.strip()
                
                if line.startswith('service ') and '{' in line:
                    name = line.split()[1].strip()
                    current_service = {
                        'name': name,
                        'image': '',
                        'replicas': 1,
                        'ports': [],
                        'env': [],
                        'volumes': []
                    }
                
                elif line.startswith('image ') and current_service:
                    image = line.split('image', 1)[1].strip().strip('"')
                    current_service['image'] = image
                
                elif line.startswith('replicas ') and current_service:
                    replicas = int(line.split()[1])
                    current_service['replicas'] = replicas
                
                elif line.startswith('ports ') and current_service:
                    ports_str = line.split('ports', 1)[1].strip()
                    for port_pair in ports_str.split(','):
                        if ':' in port_pair:
                            host, container = port_pair.strip().split(':')
                            current_service['ports'].append({
                                'host': int(host),
                                'container': int(container)
                            })
                
                elif line.startswith('env ') and current_service:
                    env_str = line.split('env', 1)[1].strip()
                    for env_pair in env_str.split(','):
                        if '=' in env_pair:
                            key, value = env_pair.strip().split('=', 1)
                            current_service['env'].append({
                                'key': key,
                                'value': value
                            })
                
                elif line.startswith('volumes ') and current_service:
                    volumes_str = line.split('volumes', 1)[1].strip()
                    for vol in volumes_str.split(','):
                        vol = vol.strip().strip('"')
                        if vol:
                            current_service['volumes'].append(vol)
                
                elif line == '}' and current_service:
                    services.append(Service(
                        name=current_service['name'],
                        image=current_service['image'],
                        replicas=current_service['replicas'],
                        ports=[PortMapping(**p) for p in current_service['ports']],
                        env=[EnvVar(**e) for e in current_service['env']],
                        volumes=current_service['volumes']
                    ))
                    current_service = None
            
            if services:
                return Program(services=services)
            return None
            
        except Exception as e:
            return None
    
    def _validate_with_parser(self, dsl_code: str) -> Tuple[bool, str]:
        """Validate with Rust parser."""
        if not self.parser_path:
            return False, "Parser not available"

        try:
            temp_file = "/tmp/grammar_eval.container"
            with open(temp_file, "w") as f:
                f.write(dsl_code)

            result = subprocess.run(
                [self.parser_path, "--plan", temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )

            return result.returncode == 0, result.stderr if result.returncode != 0 else "Valid"
        except Exception as e:
            return False, str(e)
    
    def _calculate_completeness(
        self,
        expected_services: List[str],
        expected_attrs: Dict[str, List[str]],
        program: Optional[Program]
    ) -> Tuple[float, List[str], Dict[str, List[str]]]:
        """Calculate completeness score."""
        if not program or not program.services:
            return 0.0, [], {}
        
        generated_services = [s.name for s in program.services]
        generated_attrs = {}
        
        for service in program.services:
            attrs = ["image"]
            if service.replicas > 1:
                attrs.append("replicas")
            if service.ports:
                attrs.append("ports")
            if service.env:
                attrs.append("env")
            if service.volumes:
                attrs.append("volumes")
            generated_attrs[service.name] = attrs
        
        # Service coverage
        service_matches = len(set(expected_services) & set(generated_services))
        service_coverage = service_matches / len(expected_services) if expected_services else 0
        
        # Attribute coverage
        attr_scores = []
        for service_name in expected_services:
            if service_name in expected_attrs and service_name in generated_attrs:
                expected_set = set(expected_attrs[service_name])
                generated_set = set(generated_attrs[service_name])
                matches = len(expected_set & generated_set)
                score = matches / len(expected_set) if expected_set else 0
                attr_scores.append(score)
        
        attr_coverage = sum(attr_scores) / len(attr_scores) if attr_scores else 0
        completeness = (service_coverage + attr_coverage) / 2
        
        return completeness, generated_services, generated_attrs
    
    def evaluate_test_case(self, test_case: TestCase) -> GrammarResult:
        """Evaluate single test case."""
        result = GrammarResult(
            test_id=test_case.id,
            category=test_case.category,
            complexity=test_case.complexity,
            prompt=test_case.prompt,
            services_expected=test_case.expected_services,
            attributes_expected=test_case.expected_attributes,
            grammar_valid=False,
            parser_valid=False,
            lark_valid=False
        )
        
        try:
            # Generate code
            start_time = time.time()
            dsl_code = self.generator.generate(test_case.prompt)
            result.generation_time = time.time() - start_time
            result.generated_code = dsl_code
            
            if not dsl_code:
                result.grammar_errors = "Failed to generate code"
                return result
            
            # Lark validation (CFG)
            lark_valid, lark_msg = self.generator.validate(dsl_code)
            result.lark_valid = lark_valid
            result.lark_errors = "" if lark_valid else lark_msg
            
            # Parse to Program
            program = self._parse_dsl_to_program(dsl_code)
            
            if program:
                # Grammar validation (semantic)
                is_valid, message = validate_and_explain(program)
                result.grammar_valid = is_valid
                result.grammar_errors = "" if is_valid else message
                
                # Parser validation (Rust)
                if self.parser_path:
                    parser_valid, parser_msg = self._validate_with_parser(dsl_code)
                    result.parser_valid = parser_valid
                    result.parser_errors = "" if parser_valid else parser_msg
                
                # Completeness
                completeness, gen_services, gen_attrs = self._calculate_completeness(
                    test_case.expected_services,
                    test_case.expected_attributes,
                    program
                )
                result.completeness_score = completeness
                result.services_generated = gen_services
                result.attributes_generated = gen_attrs
            else:
                result.grammar_errors = "Failed to parse generated code"
                
        except Exception as e:
            result.grammar_errors = f"Exception: {str(e)}"
        
        return result
    
    def evaluate_dataset(self, test_cases: List[TestCase], save_results: bool = True) -> GrammarMetrics:
        """Evaluate full dataset."""
        self.results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Evaluating Grammar-Based...",
                total=len(test_cases)
            )
            
            for test_case in test_cases:
                result = self.evaluate_test_case(test_case)
                self.results.append(result)
                progress.advance(task)
        
        # Calculate metrics
        grammar_valid = sum(1 for r in self.results if r.grammar_valid)
        parser_valid = sum(1 for r in self.results if r.parser_valid)
        lark_valid = sum(1 for r in self.results if r.lark_valid)
        all_valid = sum(1 for r in self.results if r.grammar_valid and r.parser_valid and r.lark_valid)
        
        completeness_scores = [r.completeness_score for r in self.results]
        avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
        
        latencies = sorted([r.generation_time for r in self.results])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        median_latency = latencies[len(latencies) // 2] if latencies else 0
        p95_index = int(len(latencies) * 0.95)
        p99_index = int(len(latencies) * 0.99)
        
        edge_complex = [r for r in self.results if r.complexity == "complex" or r.category == "edge_case"]
        extensibility = sum(1 for r in edge_complex if r.grammar_valid) / len(edge_complex) if edge_complex else 0
        
        metrics = GrammarMetrics(
            total_tests=len(self.results),
            validity_percentage=(all_valid / len(self.results)) * 100,
            grammar_pass_rate=(grammar_valid / len(self.results)) * 100,
            parser_pass_rate=(parser_valid / len(self.results)) * 100,
            lark_pass_rate=(lark_valid / len(self.results)) * 100,
            completeness_percentage=avg_completeness * 100,
            avg_service_coverage=avg_completeness * 100,
            avg_attribute_coverage=avg_completeness * 100,
            extensibility_percentage=extensibility * 100,
            avg_latency=avg_latency,
            median_latency=median_latency,
            p95_latency=latencies[p95_index] if p95_index < len(latencies) else latencies[-1],
            p99_latency=latencies[p99_index] if p99_index < len(latencies) else latencies[-1],
            by_category=self._breakdown_by_field("category"),
            by_complexity=self._breakdown_by_field("complexity")
        )
        
        if save_results:
            self._save_results(metrics)
        
        return metrics
    
    def _breakdown_by_field(self, field: str) -> Dict[str, Dict[str, float]]:
        """Generate breakdown by field."""
        breakdown = {}
        field_values = set(getattr(r, field) for r in self.results)
        
        for value in field_values:
            filtered = [r for r in self.results if getattr(r, field) == value]
            if not filtered:
                continue
            
            grammar_valid = sum(1 for r in filtered if r.grammar_valid)
            lark_valid = sum(1 for r in filtered if r.lark_valid)
            completeness = sum(r.completeness_score for r in filtered) / len(filtered)
            avg_latency = sum(r.generation_time for r in filtered) / len(filtered)
            
            breakdown[value] = {
                "total": len(filtered),
                "grammar_pass_rate": (grammar_valid / len(filtered)) * 100,
                "lark_pass_rate": (lark_valid / len(filtered)) * 100,
                "completeness": completeness * 100,
                "avg_latency": avg_latency
            }
        
        return breakdown
    
    def _save_results(self, metrics: GrammarMetrics):
        """Save results to files."""
        # Summary
        summary = {
            "approach": "Grammar-Based (CFG + Lark)",
            "total_tests": metrics.total_tests,
            "validity_percentage": round(metrics.validity_percentage, 2),
            "grammar_pass_rate": round(metrics.grammar_pass_rate, 2),
            "parser_pass_rate": round(metrics.parser_pass_rate, 2),
            "lark_pass_rate": round(metrics.lark_pass_rate, 2),
            "completeness_percentage": round(metrics.completeness_percentage, 2),
            "extensibility_percentage": round(metrics.extensibility_percentage, 2),
            "avg_latency_seconds": round(metrics.avg_latency, 3),
            "median_latency_seconds": round(metrics.median_latency, 3),
            "p95_latency_seconds": round(metrics.p95_latency, 3),
        }
        
        with open("grammar_evaluation_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        # Detailed report
        detailed = {
            "metadata": summary,
            "metrics": asdict(metrics),
            "test_results": [asdict(r) for r in self.results]
        }
        
        with open("grammar_evaluation_report.json", "w") as f:
            json.dump(detailed, f, indent=2)
        
        console.print("\n[green]Grammar-based results saved to:[/green]")
        console.print("  - grammar_evaluation_summary.json")
        console.print("  - grammar_evaluation_report.json")


def main():
    """Run grammar-based evaluation."""
    console.print("\n[bold cyan]═══ Grammar-Based Evaluation ═══[/bold cyan]\n")
    
    # Load dataset
    with open("test_dataset.json", "r") as f:
        data = json.load(f)
    
    test_cases = [TestCase(**tc) for tc in data["test_cases"]]
    console.print(f"[green]Loaded {len(test_cases)} test cases[/green]\n")
    
    # Run evaluation
    evaluator = GrammarEvaluator()
    
    if not evaluator.parser_path:
        console.print("[yellow]⚠ Rust parser not found[/yellow]\n")
    
    metrics = evaluator.evaluate_dataset(test_cases)
    
    # Print results
    from rich.table import Table
    table = Table(title="Grammar-Based Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    table.add_row("Total Tests", str(metrics.total_tests))
    table.add_row("Validity (All)", f"{metrics.validity_percentage:.2f}%")
    table.add_row("Grammar Pass Rate", f"{metrics.grammar_pass_rate:.2f}%")
    table.add_row("Parser Pass Rate", f"{metrics.parser_pass_rate:.2f}%")
    table.add_row("Lark (CFG) Pass Rate", f"{metrics.lark_pass_rate:.2f}%")
    table.add_row("Completeness", f"{metrics.completeness_percentage:.2f}%")
    table.add_row("Extensibility", f"{metrics.extensibility_percentage:.2f}%")
    table.add_row("Avg Latency", f"{metrics.avg_latency:.3f}s")
    table.add_row("Median Latency", f"{metrics.median_latency:.3f}s")
    table.add_row("P95 Latency", f"{metrics.p95_latency:.3f}s")
    
    console.print(table)
    console.print("\n[green]✓ Grammar-based evaluation complete![/green]\n")


if __name__ == "__main__":
    main()