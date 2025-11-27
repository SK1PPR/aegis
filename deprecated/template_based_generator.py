"""Template-based DSL generator using Jinja2 and pattern matching."""

import re
from typing import List, Dict, Optional, Tuple
from jinja2 import Environment, BaseLoader, Template

# Service templates
SERVICE_TEMPLATES = {
    'nginx': {
        'image': 'nginx:1.25',
        'default_port': 80,
        'keywords': ['nginx', 'web server', 'http server'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'apache': {
        'image': 'httpd:2.4',
        'default_port': 80,
        'keywords': ['apache', 'httpd'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'caddy': {
        'image': 'caddy:2',
        'default_port': 80,
        'keywords': ['caddy'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'postgres': {
        'image': 'postgres:16',
        'default_port': 5432,
        'keywords': ['postgres', 'postgresql', 'database', 'db'],
        'default_env': 'POSTGRES_USER=admin,POSTGRES_PASSWORD=secret123,POSTGRES_DB=myapp',
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'mysql': {
        'image': 'mysql:8',
        'default_port': 3306,
        'keywords': ['mysql'],
        'default_env': 'MYSQL_ROOT_PASSWORD=secret123,MYSQL_DATABASE=myapp',
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'mongodb': {
        'image': 'mongo:7',
        'default_port': 27017,
        'keywords': ['mongodb', 'mongo'],
        'default_env': 'MONGO_INITDB_ROOT_USERNAME=admin,MONGO_INITDB_ROOT_PASSWORD=secret123',
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'redis': {
        'image': 'redis:7',
        'default_port': 6379,
        'keywords': ['redis', 'cache'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'node': {
        'image': 'node:18',
        'default_port': 3000,
        'keywords': ['node', 'express', 'api'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'python': {
        'image': 'python:3.11',
        'default_port': 8000,
        'keywords': ['python', 'django', 'flask', 'fastapi'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'java': {
        'image': 'openjdk:17',
        'default_port': 8080,
        'keywords': ['java', 'openjdk', 'spring'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'wordpress': {
        'image': 'wordpress:latest',
        'default_port': 80,
        'keywords': ['wordpress'],
        'default_env': 'WORDPRESS_DB_HOST=db,WORDPRESS_DB_USER=wpuser,WORDPRESS_DB_PASSWORD=wppass',
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'prometheus': {
        'image': 'prom/prometheus:latest',
        'default_port': 9090,
        'keywords': ['prometheus'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'grafana': {
        'image': 'grafana/grafana:latest',
        'default_port': 3000,
        'keywords': ['grafana'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'elasticsearch': {
        'image': 'elasticsearch:8.11.0',
        'default_port': 9200,
        'keywords': ['elasticsearch', 'elastic'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'logstash': {
        'image': 'logstash:8.11.0',
        'default_port': 5000,
        'keywords': ['logstash'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'kibana': {
        'image': 'kibana:8.11.0',
        'default_port': 5601,
        'keywords': ['kibana'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'jenkins': {
        'image': 'jenkins/jenkins:lts',
        'default_port': 8080,
        'keywords': ['jenkins'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'gitlab-runner': {
        'image': 'gitlab/gitlab-runner:latest',
        'default_port': None,
        'keywords': ['gitlab runner', 'runner'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'nexus': {
        'image': 'sonatype/nexus3:latest',
        'default_port': 8081,
        'keywords': ['nexus', 'repository'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'rabbitmq': {
        'image': 'rabbitmq:3-management',
        'default_port': 5672,
        'keywords': ['rabbitmq'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'kafka': {
        'image': 'confluentinc/cp-kafka:latest',
        'default_port': 9092,
        'keywords': ['kafka'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'zookeeper': {
        'image': 'zookeeper:latest',
        'default_port': 2181,
        'keywords': ['zookeeper'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
    'node-exporter': {
        'image': 'prom/node-exporter:latest',
        'default_port': 9100,
        'keywords': ['node-exporter', 'exporter'],
        'template': '''service {{ name }} {
  image "{{ image }}"
{%- if replicas > 1 %}
  replicas {{ replicas }}
{%- endif %}
{%- if ports %}
  ports {{ ports }}
{%- endif %}
{%- if env %}
  env {{ env }}
{%- endif %}
{%- if volumes %}
  volumes {{ volumes }}
{%- endif %}
}'''
    },
}


class TemplateBasedGenerator:
    """Generate DSL code using templates and pattern matching."""
    
    def __init__(self):
        self.env = Environment(loader=BaseLoader())
        
    def _identify_services(self, prompt: str) -> List[Dict[str, any]]:
        """Identify services mentioned in the prompt."""
        prompt_lower = prompt.lower()
        identified_services = []
        
        # Check for each known service type
        for service_type, config in SERVICE_TEMPLATES.items():
            for keyword in config['keywords']:
                if keyword in prompt_lower:
                    # Determine service name
                    name = self._extract_service_name(prompt, service_type, keyword)
                    
                    service = {
                        'type': service_type,
                        'name': name,
                        'image': config['image'],
                        'default_port': config.get('default_port'),
                        'default_env': config.get('default_env', ''),
                        'template': config['template']
                    }
                    identified_services.append(service)
                    break
        
        return identified_services
    
    def _extract_service_name(self, prompt: str, service_type: str, keyword: str) -> str:
        """Extract or infer service name."""
        prompt_lower = prompt.lower()
        
        # Common name mappings
        name_mappings = {
            'nginx': 'web',
            'apache': 'web',
            'caddy': 'web',
            'postgres': 'db',
            'postgresql': 'db',
            'mysql': 'db',
            'mongodb': 'db',
            'mongo': 'mongodb',
            'redis': 'cache',
            'node': 'api',
            'python': 'app',
            'java': 'api',
            'openjdk': 'api',
            'wordpress': 'wordpress',
            'prometheus': 'prometheus',
            'grafana': 'grafana',
            'elasticsearch': 'elasticsearch',
            'logstash': 'logstash',
            'kibana': 'kibana',
            'jenkins': 'jenkins',
            'gitlab runner': 'runner',
            'runner': 'runner',
            'nexus': 'nexus',
            'rabbitmq': 'rabbitmq',
            'kafka': 'kafka',
            'zookeeper': 'zookeeper',
            'node-exporter': 'exporter',
            'exporter': 'exporter',
        }
        
        # Check if there are multiple of same type (load balancer, proxy, etc.)
        if 'load balanc' in prompt_lower or 'lb' in prompt_lower:
            if keyword in ['nginx', 'apache']:
                return 'loadbalancer'
        
        if 'reverse proxy' in prompt_lower or 'proxy' in prompt_lower:
            if keyword in ['nginx', 'apache']:
                return 'proxy'
        
        if 'frontend' in prompt_lower:
            if keyword in ['nginx', 'apache', 'caddy']:
                return 'frontend'
        
        return name_mappings.get(keyword, name_mappings.get(service_type, 'service'))
    
    def _extract_ports(self, prompt: str, default_port: Optional[int]) -> str:
        """Extract port mappings from prompt."""
        ports = []
        
        # Pattern: "port 80", "on port 5432", "ports 80 and 443", "port 80:8080"
        port_patterns = [
            r'port[s]?\s+(\d+):(\d+)',  # Explicit mapping
            r'port[s]?\s+(\d+)\s+and\s+(\d+)',  # Multiple ports
            r'port[s]?\s+(\d+),\s*(\d+)',  # Comma-separated
            r'on port[s]?\s+(\d+)',  # Single port
            r'listening on\s+(\d+)',  # Listening
            r'port[s]?\s+(\d+)',  # Generic
        ]
        
        for pattern in port_patterns:
            matches = re.findall(pattern, prompt)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        if len(match) == 2:
                            # Could be host:container or port1,port2
                            port1, port2 = match
                            if ':' in prompt or 'mapping' in prompt.lower():
                                ports.append(f"{port1}:{port2}")
                            else:
                                ports.append(f"{port1}:{port1}")
                                ports.append(f"{port2}:{port2}")
                        else:
                            port = match[0]
                            ports.append(f"{port}:{port}")
                    else:
                        ports.append(f"{match}:{match}")
                break
        
        # If no ports found and default exists, use default
        if not ports and default_port:
            ports.append(f"{default_port}:{default_port}")
        
        return ','.join(ports) if ports else ''
    
    def _extract_env_vars(self, prompt: str, default_env: str) -> str:
        """Extract environment variables from prompt."""
        env_vars = []
        
        # Pattern: KEY=value, KEY=value
        env_pattern = r'([A-Z_][A-Z0-9_]*)=([^\s,]+)'
        matches = re.findall(env_pattern, prompt)
        
        if matches:
            env_vars = [f"{key}={value}" for key, value in matches]
        
        # Check for credentials mentioned without format
        if 'username' in prompt.lower() or 'user' in prompt.lower():
            user_match = re.search(r'user(?:name)?\s+(\w+)', prompt.lower())
            if user_match and not any('USER' in ev for ev in env_vars):
                user = user_match.group(1)
                if 'postgres' in prompt.lower():
                    env_vars.append(f"POSTGRES_USER={user}")
                elif 'mysql' in prompt.lower():
                    env_vars.append(f"MYSQL_USER={user}")
                elif 'mongo' in prompt.lower():
                    env_vars.append(f"MONGO_INITDB_ROOT_USERNAME={user}")
        
        if 'password' in prompt.lower():
            pass_match = re.search(r'password\s+(\w+)', prompt.lower())
            if pass_match and not any('PASSWORD' in ev for ev in env_vars):
                password = pass_match.group(1)
                if 'postgres' in prompt.lower():
                    env_vars.append(f"POSTGRES_PASSWORD={password}")
                elif 'mysql' in prompt.lower():
                    env_vars.append(f"MYSQL_PASSWORD={password}")
                elif 'mongo' in prompt.lower():
                    env_vars.append(f"MONGO_INITDB_ROOT_PASSWORD={password}")
        
        if 'database' in prompt.lower() and not any('DB' in ev or 'DATABASE' in ev for ev in env_vars):
            db_match = re.search(r'database\s+(\w+)', prompt.lower())
            if db_match:
                dbname = db_match.group(1)
                if 'postgres' in prompt.lower():
                    env_vars.append(f"POSTGRES_DB={dbname}")
                elif 'mysql' in prompt.lower():
                    env_vars.append(f"MYSQL_DATABASE={dbname}")
        
        # If no env vars found but default exists, use default
        if not env_vars and default_env:
            return default_env
        
        return ','.join(env_vars) if env_vars else ''
    
    def _extract_volumes(self, prompt: str) -> str:
        """Extract volume mappings from prompt."""
        volumes = []
        
        # Pattern: /path/on/host:/path/in/container
        volume_pattern = r'([/\w\-\.]+):([/\w\-\.]+)'
        matches = re.findall(volume_pattern, prompt)
        
        if matches:
            volumes = [f'"{host}:{container}"' for host, container in matches]
        
        # Check for "volume for data persistence" or similar
        if 'volume' in prompt.lower() or 'persistent' in prompt.lower():
            if not volumes:
                # Add default volumes based on service type
                if 'postgres' in prompt.lower():
                    volumes.append('"/data/postgres:/var/lib/postgresql/data"')
                elif 'mysql' in prompt.lower():
                    volumes.append('"/data/mysql:/var/lib/mysql"')
                elif 'mongo' in prompt.lower():
                    volumes.append('"/data/mongo:/data/db"')
                elif 'redis' in prompt.lower():
                    volumes.append('"/data/redis:/data"')
                elif 'jenkins' in prompt.lower():
                    volumes.append('"/data/jenkins:/var/jenkins_home"')
        
        return ','.join(volumes) if volumes else ''
    
    def _extract_replicas(self, prompt: str) -> int:
        """Extract replica count from prompt."""
        # Pattern: "3 replicas", "with 5 replicas", "replicas 2"
        replica_patterns = [
            r'(\d+)\s+replica',
            r'replica[s]?\s+(\d+)',
            r'with\s+(\d+)\s+replica',
        ]
        
        for pattern in replica_patterns:
            match = re.search(pattern, prompt.lower())
            if match:
                return int(match.group(1))
        
        return 1
    
    def generate(self, prompt: str) -> str:
        """Generate DSL code from natural language prompt."""
        # Identify services
        services = self._identify_services(prompt)
        
        if not services:
            # Fallback: try to generate a basic service
            return self._generate_fallback(prompt)
        
        # Generate code for each service
        dsl_code = []
        
        for service in services:
            # Extract attributes
            ports = self._extract_ports(prompt, service['default_port'])
            env = self._extract_env_vars(prompt, service['default_env'])
            volumes = self._extract_volumes(prompt)
            replicas = self._extract_replicas(prompt)
            
            # Render template
            template = self.env.from_string(service['template'])
            code = template.render(
                name=service['name'],
                image=service['image'],
                ports=ports,
                env=env,
                volumes=volumes,
                replicas=replicas
            )
            
            dsl_code.append(code)
        
        return '\n\n'.join(dsl_code)
    
    def _generate_fallback(self, prompt: str) -> str:
        """Generate fallback service when no template matches."""
        # Try to extract basic info
        name = 'service'
        image = 'ubuntu:latest'
        
        # Check for common generic patterns
        if 'web' in prompt.lower():
            name = 'web'
            image = 'nginx:latest'
        elif 'api' in prompt.lower():
            name = 'api'
            image = 'node:18'
        elif 'app' in prompt.lower():
            name = 'app'
            image = 'python:3.11'
        
        ports = self._extract_ports(prompt, None)
        env = self._extract_env_vars(prompt, '')
        volumes = self._extract_volumes(prompt)
        replicas = self._extract_replicas(prompt)
        
        template = self.env.from_string(SERVICE_TEMPLATES['nginx']['template'])
        return template.render(
            name=name,
            image=image,
            ports=ports,
            env=env,
            volumes=volumes,
            replicas=replicas
        )