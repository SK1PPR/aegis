"""Grammar-based DSL generator using CFG and Lark parser."""

from lark import Lark, Transformer, v_args
from typing import List, Dict, Optional, Tuple
import re


# Context-Free Grammar for container-lang DSL
CONTAINER_LANG_GRAMMAR = r"""
    start: service+

    service: "service" NAME "{" service_body "}"
    
    service_body: image_decl replicas_decl? ports_decl? env_decl? volumes_decl?
    
    image_decl: "image" STRING
    replicas_decl: "replicas" NUMBER
    ports_decl: "ports" port_mapping ("," port_mapping)*
    env_decl: "env" env_var ("," env_var)*
    volumes_decl: "volumes" volume_mapping ("," volume_mapping)*
    
    port_mapping: NUMBER ":" NUMBER
    env_var: NAME "=" VALUE
    volume_mapping: STRING
    
    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
    VALUE: /[^,\s}]+/
    STRING: ESCAPED_STRING
    NUMBER: /\d+/
    
    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS
"""


class NLToIntermediateRepresentation:
    """Convert natural language to intermediate representation."""
    
    # Keyword mappings for service identification
    SERVICE_KEYWORDS = {
        'nginx': {'type': 'web', 'image': 'nginx:1.25', 'port': 80},
        'apache': {'type': 'web', 'image': 'httpd:2.4', 'port': 80},
        'caddy': {'type': 'web', 'image': 'caddy:2', 'port': 80},
        'postgres': {'type': 'db', 'image': 'postgres:16', 'port': 5432},
        'postgresql': {'type': 'db', 'image': 'postgres:16', 'port': 5432},
        'mysql': {'type': 'db', 'image': 'mysql:8', 'port': 3306},
        'mongodb': {'type': 'mongodb', 'image': 'mongo:7', 'port': 27017},
        'mongo': {'type': 'mongodb', 'image': 'mongo:7', 'port': 27017},
        'redis': {'type': 'cache', 'image': 'redis:7', 'port': 6379},
        'node': {'type': 'api', 'image': 'node:18', 'port': 3000},
        'express': {'type': 'api', 'image': 'node:18', 'port': 3000},
        'python': {'type': 'app', 'image': 'python:3.11', 'port': 8000},
        'django': {'type': 'app', 'image': 'python:3.11', 'port': 8000},
        'flask': {'type': 'app', 'image': 'python:3.11', 'port': 5000},
        'java': {'type': 'api', 'image': 'openjdk:17', 'port': 8080},
        'openjdk': {'type': 'api', 'image': 'openjdk:17', 'port': 8080},
        'spring': {'type': 'api', 'image': 'openjdk:17', 'port': 8080},
        'wordpress': {'type': 'wordpress', 'image': 'wordpress:latest', 'port': 80},
        'prometheus': {'type': 'prometheus', 'image': 'prom/prometheus:latest', 'port': 9090},
        'grafana': {'type': 'grafana', 'image': 'grafana/grafana:latest', 'port': 3000},
        'elasticsearch': {'type': 'elasticsearch', 'image': 'elasticsearch:8.11.0', 'port': 9200},
        'logstash': {'type': 'logstash', 'image': 'logstash:8.11.0', 'port': 5000},
        'kibana': {'type': 'kibana', 'image': 'kibana:8.11.0', 'port': 5601},
        'jenkins': {'type': 'jenkins', 'image': 'jenkins/jenkins:lts', 'port': 8080},
        'gitlab runner': {'type': 'runner', 'image': 'gitlab/gitlab-runner:latest', 'port': None},
        'nexus': {'type': 'nexus', 'image': 'sonatype/nexus3:latest', 'port': 8081},
        'rabbitmq': {'type': 'rabbitmq', 'image': 'rabbitmq:3-management', 'port': 5672},
        'kafka': {'type': 'kafka', 'image': 'confluentinc/cp-kafka:latest', 'port': 9092},
        'zookeeper': {'type': 'zookeeper', 'image': 'zookeeper:latest', 'port': 2181},
        'node-exporter': {'type': 'exporter', 'image': 'prom/node-exporter:latest', 'port': 9100},
    }
    
    def __init__(self):
        self.services = []
    
    def parse(self, prompt: str) -> List[Dict]:
        """Parse natural language to intermediate representation."""
        self.services = []
        prompt_lower = prompt.lower()
        
        # Identify all services in the prompt
        for keyword, config in self.SERVICE_KEYWORDS.items():
            if keyword in prompt_lower:
                service = self._create_service(prompt, keyword, config)
                if service:
                    self.services.append(service)
        
        # Handle special naming cases
        self._resolve_service_names(prompt)
        
        return self.services
    
    def _create_service(self, prompt: str, keyword: str, config: Dict) -> Dict:
        """Create service from keyword and configuration."""
        service = {
            'name': config['type'],
            'image': config['image'],
            'replicas': 1,
            'ports': [],
            'env': [],
            'volumes': []
        }
        
        # Extract ports
        ports = self._extract_ports(prompt, config.get('port'))
        if ports:
            service['ports'] = ports
        
        # Extract environment variables
        env_vars = self._extract_env_vars(prompt, keyword)
        if env_vars:
            service['env'] = env_vars
        
        # Extract volumes
        volumes = self._extract_volumes(prompt, keyword)
        if volumes:
            service['volumes'] = volumes
        
        # Extract replicas
        replicas = self._extract_replicas(prompt)
        if replicas > 1:
            service['replicas'] = replicas
        
        return service
    
    def _extract_ports(self, prompt: str, default_port: Optional[int]) -> List[Tuple[int, int]]:
        """Extract port mappings."""
        ports = []
        
        # Pattern: explicit mapping (80:8080)
        explicit_mappings = re.findall(r'(\d+):(\d+)', prompt)
        for host, container in explicit_mappings:
            ports.append((int(host), int(container)))
        
        # Pattern: "port 80", "on port 5432"
        if not ports:
            simple_ports = re.findall(r'port[s]?\s+(\d+)', prompt.lower())
            for port in simple_ports:
                ports.append((int(port), int(port)))
        
        # Pattern: "ports 80 and 443"
        if not ports:
            and_ports = re.findall(r'port[s]?\s+(\d+)\s+and\s+(\d+)', prompt.lower())
            for port1, port2 in and_ports:
                ports.append((int(port1), int(port1)))
                ports.append((int(port2), int(port2)))
        
        # Use default if no ports found
        if not ports and default_port:
            ports.append((default_port, default_port))
        
        return ports
    
    def _extract_env_vars(self, prompt: str, service_keyword: str) -> List[Tuple[str, str]]:
        """Extract environment variables."""
        env_vars = []
        
        # Pattern: KEY=value
        explicit_env = re.findall(r'([A-Z_][A-Z0-9_]*)=([^\s,}]+)', prompt)
        env_vars.extend(explicit_env)
        
        # Extract credentials for databases
        if service_keyword in ['postgres', 'postgresql']:
            if not any('POSTGRES_USER' in e[0] for e in env_vars):
                user_match = re.search(r'user(?:name)?\s+(\w+)', prompt.lower())
                if user_match:
                    env_vars.append(('POSTGRES_USER', user_match.group(1)))
            
            if not any('POSTGRES_PASSWORD' in e[0] for e in env_vars):
                pass_match = re.search(r'password\s+(\w+)', prompt.lower())
                if pass_match:
                    env_vars.append(('POSTGRES_PASSWORD', pass_match.group(1)))
            
            if not any('POSTGRES_DB' in e[0] for e in env_vars):
                db_match = re.search(r'database\s+(\w+)', prompt.lower())
                if db_match:
                    env_vars.append(('POSTGRES_DB', db_match.group(1)))
        
        elif service_keyword == 'mysql':
            if not any('MYSQL_ROOT_PASSWORD' in e[0] for e in env_vars):
                pass_match = re.search(r'password\s+(\w+)', prompt.lower())
                if pass_match:
                    env_vars.append(('MYSQL_ROOT_PASSWORD', pass_match.group(1)))
            
            if not any('MYSQL_DATABASE' in e[0] for e in env_vars):
                db_match = re.search(r'database\s+(\w+)', prompt.lower())
                if db_match:
                    env_vars.append(('MYSQL_DATABASE', db_match.group(1)))
        
        elif service_keyword in ['mongodb', 'mongo']:
            if not any('MONGO_INITDB_ROOT_USERNAME' in e[0] for e in env_vars):
                user_match = re.search(r'user(?:name)?\s+(\w+)', prompt.lower())
                if user_match:
                    env_vars.append(('MONGO_INITDB_ROOT_USERNAME', user_match.group(1)))
            
            if not any('MONGO_INITDB_ROOT_PASSWORD' in e[0] for e in env_vars):
                pass_match = re.search(r'password\s+(\w+)', prompt.lower())
                if pass_match:
                    env_vars.append(('MONGO_INITDB_ROOT_PASSWORD', pass_match.group(1)))
        
        return env_vars
    
    def _extract_volumes(self, prompt: str, service_keyword: str) -> List[str]:
        """Extract volume mappings."""
        volumes = []
        
        # Pattern: /path/host:/path/container
        explicit_volumes = re.findall(r'([/\w\-\.]+):([/\w\-\.]+)', prompt)
        for host, container in explicit_volumes:
            if '/' in host and '/' in container:  # Ensure they're paths
                volumes.append(f"{host}:{container}")
        
        # Add default volumes for databases if persistence mentioned
        if 'volume' in prompt.lower() or 'persistent' in prompt.lower():
            if not volumes:
                if service_keyword in ['postgres', 'postgresql']:
                    volumes.append('/data/postgres:/var/lib/postgresql/data')
                elif service_keyword == 'mysql':
                    volumes.append('/data/mysql:/var/lib/mysql')
                elif service_keyword in ['mongodb', 'mongo']:
                    volumes.append('/data/mongo:/data/db')
                elif service_keyword == 'redis':
                    volumes.append('/data/redis:/data')
                elif service_keyword == 'jenkins':
                    volumes.append('/data/jenkins:/var/jenkins_home')
                elif service_keyword == 'elasticsearch':
                    volumes.append('/data/es:/usr/share/elasticsearch/data')
        
        return volumes
    
    def _extract_replicas(self, prompt: str) -> int:
        """Extract replica count."""
        # Pattern: "3 replicas", "with 5 replicas", "replicas 2"
        patterns = [
            r'(\d+)\s+replica',
            r'replica[s]?\s+(\d+)',
            r'with\s+(\d+)\s+replica'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt.lower())
            if match:
                return int(match.group(1))
        
        return 1
    
    def _resolve_service_names(self, prompt: str):
        """Resolve service names to avoid conflicts."""
        prompt_lower = prompt.lower()
        
        # Track names and resolve conflicts
        name_counts = {}
        for service in self.services:
            name = service['name']
            if name in name_counts:
                name_counts[name] += 1
                # Rename based on role
                if 'load balanc' in prompt_lower or 'lb' in prompt_lower:
                    service['name'] = 'loadbalancer'
                elif 'reverse proxy' in prompt_lower or 'proxy' in prompt_lower:
                    service['name'] = 'proxy'
                elif 'frontend' in prompt_lower:
                    service['name'] = 'frontend'
                else:
                    service['name'] = f"{name}{name_counts[name]}"
            else:
                name_counts[name] = 1


class GrammarBasedGenerator:
    """Generate DSL using CFG and Lark parser."""
    
    def __init__(self):
        self.parser = Lark(CONTAINER_LANG_GRAMMAR, start='start')
        self.nl_parser = NLToIntermediateRepresentation()
    
    def generate(self, prompt: str) -> str:
        """Generate DSL from natural language."""
        # Step 1: Convert NL to intermediate representation
        services = self.nl_parser.parse(prompt)
        
        if not services:
            return self._generate_fallback(prompt)
        
        # Step 2: Generate DSL from IR
        dsl_code = self._generate_dsl_from_ir(services)
        
        # Step 3: Validate with grammar
        try:
            self.parser.parse(dsl_code)
            return dsl_code
        except Exception as e:
            # If validation fails, try to fix and regenerate
            return self._fix_and_regenerate(services, str(e))
    
    def _generate_dsl_from_ir(self, services: List[Dict]) -> str:
        """Generate DSL code from intermediate representation."""
        dsl_parts = []
        
        for service in services:
            lines = [f"service {service['name']} {{"]
            
            # Image (required)
            lines.append(f'  image "{service["image"]}"')
            
            # Replicas (optional)
            if service['replicas'] > 1:
                lines.append(f"  replicas {service['replicas']}")
            
            # Ports (optional)
            if service['ports']:
                port_mappings = ','.join(f"{host}:{container}" for host, container in service['ports'])
                lines.append(f"  ports {port_mappings}")
            
            # Environment variables (optional)
            if service['env']:
                env_pairs = ','.join(f"{key}={value}" for key, value in service['env'])
                lines.append(f"  env {env_pairs}")
            
            # Volumes (optional)
            if service['volumes']:
                volume_mappings = ','.join(f'"{vol}"' for vol in service['volumes'])
                lines.append(f"  volumes {volume_mappings}")
            
            lines.append("}")
            dsl_parts.append('\n'.join(lines))
        
        return '\n\n'.join(dsl_parts)
    
    def _fix_and_regenerate(self, services: List[Dict], error: str) -> str:
        """Attempt to fix errors and regenerate."""
        # Try to identify and fix common issues
        for service in services:
            # Ensure image is not empty
            if not service['image']:
                service['image'] = 'ubuntu:latest'
            
            # Ensure valid port numbers
            service['ports'] = [(h, c) for h, c in service['ports'] if 0 < h < 65536 and 0 < c < 65536]
            
            # Ensure valid env var names
            service['env'] = [(k, v) for k, v in service['env'] if k and v]
        
        # Try regenerating
        return self._generate_dsl_from_ir(services)
    
    def _generate_fallback(self, prompt: str) -> str:
        """Generate fallback when no services identified."""
        # Try to infer basic service
        name = 'service'
        image = 'ubuntu:latest'
        
        if 'web' in prompt.lower():
            name = 'web'
            image = 'nginx:latest'
        elif 'api' in prompt.lower():
            name = 'api'
            image = 'node:18'
        elif 'app' in prompt.lower():
            name = 'app'
            image = 'python:3.11'
        
        service = {
            'name': name,
            'image': image,
            'replicas': 1,
            'ports': [],
            'env': [],
            'volumes': []
        }
        
        # Extract any mentioned attributes
        replicas_match = re.search(r'(\d+)\s+replica', prompt.lower())
        if replicas_match:
            service['replicas'] = int(replicas_match.group(1))
        
        return self._generate_dsl_from_ir([service])
    
    def validate(self, dsl_code: str) -> Tuple[bool, str]:
        """Validate DSL code against grammar."""
        try:
            self.parser.parse(dsl_code)
            return True, "Valid"
        except Exception as e:
            return False, str(e)