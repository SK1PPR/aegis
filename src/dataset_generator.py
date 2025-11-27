"""Generate exhaustive test dataset for NL2DSL evaluation."""

import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class TestCase:
    """Represents a single test case."""
    id: str
    category: str
    complexity: str  # simple, medium, complex
    prompt: str
    expected_services: List[str]
    expected_attributes: Dict[str, List[str]]  # service -> attributes
    description: str


class DatasetGenerator:
    """Generate comprehensive test dataset."""

    def __init__(self):
        self.test_cases: List[TestCase] = []
        self._generate_all_cases()

    def _generate_all_cases(self):
        """Generate all test cases across categories."""
        self._add_basic_web_services()
        self._add_database_services()
        self._add_multi_service_applications()
        self._add_complex_scenarios()
        self._add_edge_cases()
        self._add_real_world_scenarios()

    def _add_basic_web_services(self):
        """Basic single web service scenarios."""
        cases = [
            TestCase(
                id="web_001",
                category="basic_web",
                complexity="simple",
                prompt="I need an nginx web server on port 80",
                expected_services=["web"],
                expected_attributes={"web": ["image", "ports"]},
                description="Single nginx service with port mapping"
            ),
            TestCase(
                id="web_002",
                category="basic_web",
                complexity="simple",
                prompt="Deploy apache web server listening on port 8080",
                expected_services=["web"],
                expected_attributes={"web": ["image", "ports"]},
                description="Apache with custom port"
            ),
            TestCase(
                id="web_003",
                category="basic_web",
                complexity="medium",
                prompt="Set up nginx on ports 80 and 443 with 3 replicas",
                expected_services=["web"],
                expected_attributes={"web": ["image", "ports", "replicas"]},
                description="Nginx with multiple ports and replicas"
            ),
            TestCase(
                id="web_004",
                category="basic_web",
                complexity="medium",
                prompt="I need a caddy server on port 80 with volume /data/web:/usr/share/caddy",
                expected_services=["web"],
                expected_attributes={"web": ["image", "ports", "volumes"]},
                description="Caddy with volume mount"
            ),
            TestCase(
                id="web_005",
                category="basic_web",
                complexity="medium",
                prompt="Deploy nginx with environment variables NGINX_HOST=example.com and NGINX_PORT=80",
                expected_services=["web"],
                expected_attributes={"web": ["image", "env"]},
                description="Nginx with environment variables"
            ),
        ]
        self.test_cases.extend(cases)

    def _add_database_services(self):
        """Database service scenarios."""
        cases = [
            TestCase(
                id="db_001",
                category="database",
                complexity="simple",
                prompt="I need a postgres database on port 5432",
                expected_services=["db"],
                expected_attributes={"db": ["image", "ports"]},
                description="Basic postgres setup"
            ),
            TestCase(
                id="db_002",
                category="database",
                complexity="medium",
                prompt="Set up postgres with username admin, password secret123, and database myapp",
                expected_services=["db"],
                expected_attributes={"db": ["image", "env"]},
                description="Postgres with credentials"
            ),
            TestCase(
                id="db_003",
                category="database",
                complexity="medium",
                prompt="Deploy MySQL on port 3306 with root password mysecret and persistent volume /data/mysql:/var/lib/mysql",
                expected_services=["db"],
                expected_attributes={"db": ["image", "ports", "env", "volumes"]},
                description="MySQL with persistence"
            ),
            TestCase(
                id="db_004",
                category="database",
                complexity="simple",
                prompt="I need redis cache on default port 6379",
                expected_services=["cache"],
                expected_attributes={"cache": ["image", "ports"]},
                description="Redis cache service"
            ),
            TestCase(
                id="db_005",
                category="database",
                complexity="medium",
                prompt="Set up MongoDB on port 27017 with username mongouser, password mongopass, and volume for data persistence",
                expected_services=["db"],
                expected_attributes={"db": ["image", "ports", "env", "volumes"]},
                description="MongoDB with auth and persistence"
            ),
            TestCase(
                id="db_006",
                category="database",
                complexity="complex",
                prompt="Deploy postgres cluster with 3 replicas, credentials admin/secret, port 5432, and data volume /pgdata:/var/lib/postgresql/data",
                expected_services=["db"],
                expected_attributes={"db": ["image", "replicas", "ports", "env", "volumes"]},
                description="Postgres with high availability"
            ),
        ]
        self.test_cases.extend(cases)

    def _add_multi_service_applications(self):
        """Multi-service application scenarios."""
        cases = [
            TestCase(
                id="multi_001",
                category="multi_service",
                complexity="medium",
                prompt="I need nginx web server on port 80 and postgres database on port 5432",
                expected_services=["web", "db"],
                expected_attributes={"web": ["image", "ports"], "db": ["image", "ports"]},
                description="Basic web + database stack"
            ),
            TestCase(
                id="multi_002",
                category="multi_service",
                complexity="complex",
                prompt="Deploy a web app with nginx on port 80, postgres database with user admin password secret on port 5432, and redis cache on port 6379",
                expected_services=["web", "db", "cache"],
                expected_attributes={
                    "web": ["image", "ports"],
                    "db": ["image", "ports", "env"],
                    "cache": ["image", "ports"]
                },
                description="Three-tier web application"
            ),
            TestCase(
                id="multi_003",
                category="multi_service",
                complexity="complex",
                prompt="Set up microservices: api service using node:18 on port 3000, postgres database on 5432 with credentials, and nginx reverse proxy on port 80",
                expected_services=["api", "db", "proxy"],
                expected_attributes={
                    "api": ["image", "ports"],
                    "db": ["image", "ports", "env"],
                    "proxy": ["image", "ports"]
                },
                description="Microservices architecture"
            ),
            TestCase(
                id="multi_004",
                category="multi_service",
                complexity="complex",
                prompt="I need a backend API with python:3.11 on port 8000, MySQL database on 3306, Redis for caching on 6379, and nginx load balancer on port 80 with 2 replicas",
                expected_services=["api", "db", "cache", "loadbalancer"],
                expected_attributes={
                    "api": ["image", "ports"],
                    "db": ["image", "ports"],
                    "cache": ["image", "ports"],
                    "loadbalancer": ["image", "ports", "replicas"]
                },
                description="Full-stack application with load balancing"
            ),
        ]
        self.test_cases.extend(cases)

    def _add_complex_scenarios(self):
        """Complex real-world scenarios."""
        cases = [
            TestCase(
                id="complex_001",
                category="complex",
                complexity="complex",
                prompt="Deploy a WordPress site with wordpress:latest on port 80, MySQL database with MYSQL_ROOT_PASSWORD=rootpass, MYSQL_DATABASE=wordpress, MYSQL_USER=wpuser, MYSQL_PASSWORD=wppass on port 3306, and volumes for both services",
                expected_services=["wordpress", "db"],
                expected_attributes={
                    "wordpress": ["image", "ports", "env", "volumes"],
                    "db": ["image", "ports", "env", "volumes"]
                },
                description="WordPress with MySQL"
            ),
            TestCase(
                id="complex_002",
                category="complex",
                complexity="complex",
                prompt="Set up a monitoring stack: prometheus on port 9090 with volume /data/prometheus:/prometheus, grafana on port 3000 with GF_SECURITY_ADMIN_PASSWORD=admin, and node-exporter on port 9100",
                expected_services=["prometheus", "grafana", "exporter"],
                expected_attributes={
                    "prometheus": ["image", "ports", "volumes"],
                    "grafana": ["image", "ports", "env"],
                    "exporter": ["image", "ports"]
                },
                description="Monitoring infrastructure"
            ),
            TestCase(
                id="complex_003",
                category="complex",
                complexity="complex",
                prompt="Create an ELK stack: elasticsearch on port 9200 with volume /data/es:/usr/share/elasticsearch/data, logstash on port 5000, and kibana on port 5601",
                expected_services=["elasticsearch", "logstash", "kibana"],
                expected_attributes={
                    "elasticsearch": ["image", "ports", "volumes"],
                    "logstash": ["image", "ports"],
                    "kibana": ["image", "ports"]
                },
                description="ELK logging stack"
            ),
        ]
        self.test_cases.extend(cases)

    def _add_edge_cases(self):
        """Edge cases and corner scenarios."""
        cases = [
            TestCase(
                id="edge_001",
                category="edge_case",
                complexity="simple",
                prompt="Deploy nginx",
                expected_services=["web"],
                expected_attributes={"web": ["image"]},
                description="Minimal input - just service name"
            ),
            TestCase(
                id="edge_002",
                category="edge_case",
                complexity="medium",
                prompt="I want a service with 5 replicas",
                expected_services=["service"],
                expected_attributes={"service": ["image", "replicas"]},
                description="Underspecified service"
            ),
            TestCase(
                id="edge_003",
                category="edge_case",
                complexity="medium",
                prompt="Set up a web service with ports 80, 443, 8080 all mapping to container port 80",
                expected_services=["web"],
                expected_attributes={"web": ["image", "ports"]},
                description="Multiple host ports to single container port"
            ),
            TestCase(
                id="edge_004",
                category="edge_case",
                complexity="medium",
                prompt="Deploy a service with 10 environment variables for configuration",
                expected_services=["service"],
                expected_attributes={"service": ["image", "env"]},
                description="Service with many env vars"
            ),
            TestCase(
                id="edge_005",
                category="edge_case",
                complexity="simple",
                prompt="I need latest version of nginx",
                expected_services=["web"],
                expected_attributes={"web": ["image"]},
                description="Version specification"
            ),
        ]
        self.test_cases.extend(cases)

    def _add_real_world_scenarios(self):
        """Real-world production-like scenarios."""
        cases = [
            TestCase(
                id="real_001",
                category="real_world",
                complexity="complex",
                prompt="Deploy a Django application: django app using python:3.11 on port 8000 with SECRET_KEY env, postgres database on 5432 with credentials, redis for session storage on 6379, and nginx as reverse proxy on ports 80 and 443 with 2 replicas",
                expected_services=["app", "db", "redis", "nginx"],
                expected_attributes={
                    "app": ["image", "ports", "env"],
                    "db": ["image", "ports", "env"],
                    "redis": ["image", "ports"],
                    "nginx": ["image", "ports", "replicas"]
                },
                description="Django production setup"
            ),
            TestCase(
                id="real_002",
                category="real_world",
                complexity="complex",
                prompt="Set up a MEAN stack: MongoDB on port 27017 with auth, Express API using node:18 on port 3000 with DB_URL environment variable, and nginx frontend on port 80",
                expected_services=["mongodb", "api", "frontend"],
                expected_attributes={
                    "mongodb": ["image", "ports", "env"],
                    "api": ["image", "ports", "env"],
                    "frontend": ["image", "ports"]
                },
                description="MEAN stack application"
            ),
            TestCase(
                id="real_003",
                category="real_world",
                complexity="complex",
                prompt="Deploy a Java microservice: Spring Boot API using openjdk:17 on port 8080 with SPRING_PROFILES_ACTIVE=prod, postgres database on 5432, Redis cache on 6379, and nginx load balancer on port 80 with 3 replicas",
                expected_services=["api", "db", "cache", "lb"],
                expected_attributes={
                    "api": ["image", "ports", "env"],
                    "db": ["image", "ports"],
                    "cache": ["image", "ports"],
                    "lb": ["image", "ports", "replicas"]
                },
                description="Java microservice stack"
            ),
            TestCase(
                id="real_004",
                category="real_world",
                complexity="complex",
                prompt="Create a CI/CD pipeline services: Jenkins on port 8080 with volume /data/jenkins:/var/jenkins_home, GitLab runner, and Nexus repository on port 8081",
                expected_services=["jenkins", "runner", "nexus"],
                expected_attributes={
                    "jenkins": ["image", "ports", "volumes"],
                    "runner": ["image"],
                    "nexus": ["image", "ports"]
                },
                description="CI/CD infrastructure"
            ),
            TestCase(
                id="real_005",
                category="real_world",
                complexity="complex",
                prompt="Deploy a messaging system: RabbitMQ on port 5672 with management UI on 15672, Kafka on port 9092, and Zookeeper on port 2181 with persistent volumes",
                expected_services=["rabbitmq", "kafka", "zookeeper"],
                expected_attributes={
                    "rabbitmq": ["image", "ports"],
                    "kafka": ["image", "ports", "volumes"],
                    "zookeeper": ["image", "ports", "volumes"]
                },
                description="Message queue infrastructure"
            ),
        ]
        self.test_cases.extend(cases)

    def get_all_cases(self) -> List[TestCase]:
        """Get all test cases."""
        return self.test_cases

    def get_by_category(self, category: str) -> List[TestCase]:
        """Get test cases by category."""
        return [tc for tc in self.test_cases if tc.category == category]

    def get_by_complexity(self, complexity: str) -> List[TestCase]:
        """Get test cases by complexity."""
        return [tc for tc in self.test_cases if tc.complexity == complexity]

    def save_to_json(self, filepath: str):
        """Save dataset to JSON file."""
        data = {
            "metadata": {
                "total_cases": len(self.test_cases),
                "categories": list(set(tc.category for tc in self.test_cases)),
                "complexity_levels": list(set(tc.complexity for tc in self.test_cases)),
            },
            "test_cases": [asdict(tc) for tc in self.test_cases]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_from_json(self, filepath: str):
        """Load dataset from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.test_cases = [TestCase(**tc) for tc in data['test_cases']]

    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        categories = {}
        complexities = {}
        for tc in self.test_cases:
            categories[tc.category] = categories.get(tc.category, 0) + 1
            complexities[tc.complexity] = complexities.get(tc.complexity, 0) + 1

        return {
            "total_cases": len(self.test_cases),
            "by_category": categories,
            "by_complexity": complexities,
            "avg_services_per_case": sum(len(tc.expected_services) for tc in self.test_cases) / len(self.test_cases),
        }


if __name__ == "__main__":
    # Generate and save dataset
    generator = DatasetGenerator()
    generator.save_to_json("test_dataset.json")
    
    stats = generator.get_statistics()
    print("Dataset Statistics:")
    print(json.dumps(stats, indent=2))