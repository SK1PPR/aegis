"""Evaluate plain LLM approach for comparison with conversational agent."""

import time
import json
import os
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from schema import Program, Service, PortMapping, EnvVar
from dataset_generator import TestCase
from grammar_validator import validate_and_explain
from dsl_generator import generate_dsl

load_dotenv()
console = Console()


@dataclass
class PlainLLMResult:
    """Result for plain LLM evaluation."""
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
    
    # Generated outputs (don't include Program object - it's not JSON serializable)
    generated_code: str = ""
    raw_response: str = ""
    
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
class PlainLLMMetrics:
    """Metrics report for plain LLM approach."""
    total_tests: int
    
    # Validity metrics
    validity_percentage: float
    grammar_pass_rate: float
    parser_pass_rate: float
    
    # Completeness metrics
    completeness_percentage: float
    avg_service_coverage: float
    avg_attribute_coverage: float
    
    # Extensibility metrics
    extensibility_percentage: float
    
    # Latency metrics
    avg_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    
    # Breakdown
    by_category: Dict[str, Dict[str, float]] = None
    by_complexity: Dict[str, Dict[str, float]] = None
    
    # Detailed results (don't include in JSON - too large)
    # We'll save summary only
    
    def __post_init__(self):
        if self.by_category is None:
            self.by_category = {}
        if self.by_complexity is None:
            self.by_complexity = {}


class PlainLLMEvaluator:
    """Evaluate plain LLM approach without conversational agent."""
    
    # System prompt for plain LLM
    SYSTEM_PROMPT = """You are an expert in container-lang DSL code generation.

# Container-lang DSL Syntax
```
service <name> {
  image "<docker-image>"
  replicas <number>
  ports <host>:<container>[,<host>:<container>...]
  env <KEY>=<value>[,<KEY>=<value>...]
  volumes "<host-path>:<container-path>"[,"<host-path>:<container-path>"...]
}
```

# Your Task
Given a natural language description, generate a valid container-lang DSL configuration.

# Rules
1. Always include the 'image' field (required)
2. Only include fields that are specified or clearly needed
3. Use appropriate Docker images (nginx:latest, postgres:16, redis:7, etc.)
4. Default replicas is 1 (omit if not needed)
5. Format ports as host:container
6. Format env as KEY=value
7. Format volumes as "host:container"

# Output Format
Return ONLY valid container-lang DSL code. No explanations, no markdown, no extra text.

# Examples

Input: "nginx web server on port 80"
Output:
service web {
  image "nginx:latest"
  ports 80:80
}

Input: "postgres database on port 5432 with user admin and password secret"
Output:
service db {
  image "postgres:16"
  ports 5432:5432
  env POSTGRES_USER=admin,POSTGRES_PASSWORD=secret
}

Input: "nginx on port 80, postgres on 5432 with credentials, and redis on 6379"
Output:
service web {
  image "nginx:latest"
  ports 80:80
}

service db {
  image "postgres:16"
  ports 5432:5432
  env POSTGRES_USER=admin,POSTGRES_PASSWORD=secret
}

service cache {
  image "redis:7"
  ports 6379:6379
}

Now generate DSL code for the following request:"""

    def __init__(self, parser_path: str = None, model: str = "gpt-4o-2024-08-06"):
        """Initialize plain LLM evaluator."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.parser_path = parser_path or self._find_parser()
        self.results: List[PlainLLMResult] = []
    
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
        """Parse DSL code back to Program object for validation."""
        try:
            services = []
            current_service = None
            
            lines = dsl_code.strip().split('\n')
            for line in lines:
                line = line.strip()
                
                if line.startswith('service ') and '{' in line:
                    # Extract service name
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
                    # Extract image
                    image = line.split('image', 1)[1].strip().strip('"')
                    current_service['image'] = image
                
                elif line.startswith('replicas ') and current_service:
                    # Extract replicas
                    replicas = int(line.split()[1])
                    current_service['replicas'] = replicas
                
                elif line.startswith('ports ') and current_service:
                    # Extract ports
                    ports_str = line.split('ports', 1)[1].strip()
                    for port_pair in ports_str.split(','):
                        if ':' in port_pair:
                            host, container = port_pair.strip().split(':')
                            current_service['ports'].append({
                                'host': int(host),
                                'container': int(container)
                            })
                
                elif line.startswith('env ') and current_service:
                    # Extract env vars
                    env_str = line.split('env', 1)[1].strip()
                    for env_pair in env_str.split(','):
                        if '=' in env_pair:
                            key, value = env_pair.strip().split('=', 1)
                            current_service['env'].append({
                                'key': key,
                                'value': value
                            })
                
                elif line.startswith('volumes ') and current_service:
                    # Extract volumes
                    volumes_str = line.split('volumes', 1)[1].strip()
                    for vol in volumes_str.split(','):
                        vol = vol.strip().strip('"')
                        if vol:
                            current_service['volumes'].append(vol)
                
                elif line == '}' and current_service:
                    # End of service
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
            console.print(f"[yellow]Warning: Could not parse DSL: {e}[/yellow]")
            return None
    
    def _generate_dsl_plain(self, prompt: str) -> Tuple[str, float, str]:
        """Generate DSL code using plain LLM (single-shot)."""
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=2000
            )
            
            generation_time = time.time() - start_time
            dsl_code = response.choices[0].message.content.strip()
            
            # Clean up the response (remove markdown if present)
            if '```' in dsl_code:
                # Extract code from markdown
                parts = dsl_code.split('```')
                for part in parts:
                    if 'service' in part.lower():
                        dsl_code = part.strip()
                        # Remove language identifier if present
                        if dsl_code.startswith('container-lang') or dsl_code.startswith('rust'):
                            dsl_code = '\n'.join(dsl_code.split('\n')[1:])
                        break
            
            return dsl_code.strip(), generation_time, dsl_code
            
        except Exception as e:
            return "", time.time() - start_time, f"Error: {str(e)}"
    
    def _validate_with_parser(self, dsl_code: str) -> Tuple[bool, str]:
        """Validate DSL code with Rust parser."""
        if not self.parser_path:
            return False, "Parser not available"

        try:
            temp_file = "/tmp/plain_llm_eval.container"
            with open(temp_file, "w") as f:
                f.write(dsl_code)

            result = subprocess.run(
                [self.parser_path, "--plan", temp_file],
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
    
    def evaluate_test_case(self, test_case: TestCase) -> PlainLLMResult:
        """Evaluate a single test case with plain LLM."""
        result = PlainLLMResult(
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
            # Generate DSL code with plain LLM
            dsl_code, gen_time, raw_resp = self._generate_dsl_plain(test_case.prompt)
            result.generation_time = gen_time
            result.generated_code = dsl_code
            result.raw_response = raw_resp
            
            if not dsl_code or "Error:" in raw_resp:
                result.grammar_errors = "Failed to generate valid DSL code"
                return result
            
            # Parse DSL to Program object
            program = self._parse_dsl_to_program(dsl_code)
            
            if program:
                # Grammar validation
                is_valid, message = validate_and_explain(program)
                result.grammar_valid = is_valid
                result.grammar_errors = "" if is_valid else message
                
                # Parser validation
                if self.parser_path:
                    parser_valid, parser_msg = self._validate_with_parser(dsl_code)
                    result.parser_valid = parser_valid
                    result.parser_errors = "" if parser_valid else parser_msg
                
                # Completeness calculation
                completeness, gen_services, gen_attrs = self._calculate_completeness(
                    test_case.expected_services,
                    test_case.expected_attributes,
                    program
                )
                result.completeness_score = completeness
                result.services_generated = gen_services
                result.attributes_generated = gen_attrs
            else:
                result.grammar_errors = "Failed to parse generated DSL"
                
        except Exception as e:
            result.grammar_errors = f"Exception: {str(e)}"
        
        return result
    
    def evaluate_dataset(
        self,
        test_cases: List[TestCase],
        save_results: bool = True
    ) -> PlainLLMMetrics:
        """Evaluate entire dataset with plain LLM."""
        self.results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Evaluating Plain LLM...", 
                total=len(test_cases)
            )
            
            for test_case in test_cases:
                result = self.evaluate_test_case(test_case)
                self.results.append(result)
                progress.advance(task)
        
        # Generate metrics report
        metrics = self._generate_metrics()
        
        if save_results:
            self._save_results(metrics)
        
        return metrics
    
    def _generate_metrics(self) -> PlainLLMMetrics:
        """Generate metrics report."""
        if not self.results:
            return PlainLLMMetrics(
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
        
        # Extensibility
        edge_complex = [r for r in self.results if r.complexity == "complex" or r.category == "edge_case"]
        extensibility = sum(1 for r in edge_complex if r.grammar_valid) / len(edge_complex) if edge_complex else 0
        
        # Breakdowns
        by_category = self._breakdown_by_field("category")
        by_complexity = self._breakdown_by_field("complexity")
        
        return PlainLLMMetrics(
            total_tests=len(self.results),
            validity_percentage=(both_valid / len(self.results)) * 100,
            grammar_pass_rate=(grammar_valid / len(self.results)) * 100,
            parser_pass_rate=(parser_valid / len(self.results)) * 100,
            completeness_percentage=avg_completeness * 100,
            avg_service_coverage=avg_completeness * 100,
            avg_attribute_coverage=avg_completeness * 100,
            extensibility_percentage=extensibility * 100,
            avg_latency=avg_latency,
            median_latency=median_latency,
            p95_latency=latencies[p95_index] if p95_index < len(latencies) else latencies[-1],
            p99_latency=latencies[p99_index] if p99_index < len(latencies) else latencies[-1],
            by_category=by_category,
            by_complexity=by_complexity
        )
    
    def _breakdown_by_field(self, field: str) -> Dict[str, Dict[str, float]]:
        """Generate metrics breakdown."""
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
    
    def _save_results(self, metrics: PlainLLMMetrics):
        """Save evaluation results."""
        # Convert metrics to dict (this will only include JSON-serializable fields)
        metrics_dict = asdict(metrics)
        
        # Save detailed report with individual test results
        detailed_report = {
            "metadata": {
                "approach": "Plain LLM (Single-Shot)",
                "model": self.model,
                "total_tests": metrics.total_tests
            },
            "metrics": metrics_dict,
            "test_results": [asdict(r) for r in self.results]
        }
        
        with open("plain_llm_evaluation_report.json", "w") as f:
            json.dump(detailed_report, f, indent=2)
        
        # Save summary
        summary = {
            "approach": "Plain LLM (Single-Shot)",
            "model": self.model,
            "total_tests": metrics.total_tests,
            "validity_percentage": round(metrics.validity_percentage, 2),
            "grammar_pass_rate": round(metrics.grammar_pass_rate, 2),
            "parser_pass_rate": round(metrics.parser_pass_rate, 2),
            "completeness_percentage": round(metrics.completeness_percentage, 2),
            "extensibility_percentage": round(metrics.extensibility_percentage, 2),
            "avg_latency_seconds": round(metrics.avg_latency, 3),
            "median_latency_seconds": round(metrics.median_latency, 3),
            "p95_latency_seconds": round(metrics.p95_latency, 3),
        }
        with open("plain_llm_evaluation_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        console.print("\n[green]Plain LLM results saved to:[/green]")
        console.print("  - plain_llm_evaluation_report.json")
        console.print("  - plain_llm_evaluation_summary.json")


def main():
    """Run plain LLM evaluation."""
    console.print("\n[bold cyan]═══ Plain LLM Evaluation ═══[/bold cyan]\n")
    
    # Load test cases
    console.print("[yellow]Loading test dataset...[/yellow]")
    with open("test_dataset.json", "r") as f:
        data = json.load(f)
    
    from dataset_generator import TestCase
    test_cases = [TestCase(**tc) for tc in data["test_cases"]]
    console.print(f"[green]Loaded {len(test_cases)} test cases[/green]\n")
    
    # Run evaluation
    evaluator = PlainLLMEvaluator()
    
    if not evaluator.parser_path:
        console.print("[yellow]⚠ Rust parser not found - parser validation will be skipped[/yellow]\n")
    
    metrics = evaluator.evaluate_dataset(test_cases)
    
    # Print results using a simpler approach
    console.print("\n[bold cyan]═══ PLAIN LLM RESULTS ═══[/bold cyan]\n")
    
    from rich.table import Table
    table = Table(title="Plain LLM Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    table.add_row("Total Tests", str(metrics.total_tests))
    table.add_row("Validity", f"{metrics.validity_percentage:.2f}%")
    table.add_row("Grammar Pass Rate", f"{metrics.grammar_pass_rate:.2f}%")
    table.add_row("Parser Pass Rate", f"{metrics.parser_pass_rate:.2f}%")
    table.add_row("Completeness", f"{metrics.completeness_percentage:.2f}%")
    table.add_row("Extensibility", f"{metrics.extensibility_percentage:.2f}%")
    table.add_row("Avg Latency", f"{metrics.avg_latency:.3f}s")
    table.add_row("Median Latency", f"{metrics.median_latency:.3f}s")
    table.add_row("P95 Latency", f"{metrics.p95_latency:.3f}s")
    
    console.print(table)
    console.print("\n[green]✓ Plain LLM evaluation complete![/green]\n")


if __name__ == "__main__":
    main()