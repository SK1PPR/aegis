"""Generates container-lang DSL code from structured JSON."""

from schema import Program, Service, PortMapping, EnvVar
from typing import List


def format_env_value(value: str) -> str:
    """Format environment variable value - quote if it contains spaces."""
    if ' ' in value or any(c in value for c in [',', '=', '#']):
        return f'"{value}"'
    return value


def format_env_vars(env: List[EnvVar]) -> str:
    """Format environment variables as KEY=value,KEY2=value2."""
    return ', '.join(f'{var.key}={format_env_value(var.value)}' for var in env)


def format_ports(ports: List[PortMapping]) -> str:
    """Format port mappings as host:container,host:container."""
    return ','.join(f'{p.host}:{p.container}' for p in ports)


def format_volumes(volumes: List[str]) -> str:
    """Format volume mappings as quoted strings."""
    return ', '.join(f'"{vol}"' for vol in volumes)


def generate_service(service: Service, indent: int = 2) -> str:
    """Generate DSL code for a single service."""
    ind = ' ' * indent
    lines = [f'service {service.name} {{']

    # Image (required)
    lines.append(f'{ind}image "{service.image}"')

    # Replicas (always include, default is 1)
    lines.append(f'{ind}replicas {service.replicas}')

    # Ports (optional)
    if service.ports:
        lines.append(f'{ind}ports {format_ports(service.ports)}')

    # Environment variables (optional)
    if service.env:
        lines.append(f'{ind}env {format_env_vars(service.env)}')

    # Volumes (optional)
    if service.volumes:
        lines.append(f'{ind}volumes {format_volumes(service.volumes)}')

    lines.append('}')
    return '\n'.join(lines)


def generate_dsl(program: Program) -> str:
    """Generate complete DSL code from a Program."""
    service_blocks = [generate_service(svc) for svc in program.services]
    return '\n\n'.join(service_blocks) + '\n'


def validate_program(program: Program) -> List[str]:
    """Validate a program and return list of errors."""
    errors = []

    if not program.services:
        errors.append("Program must have at least one service")
        return errors

    seen_names = set()
    for svc in program.services:
        # Check for duplicate names
        if svc.name in seen_names:
            errors.append(f"Duplicate service name: {svc.name}")
        seen_names.add(svc.name)

        # Validate replicas
        if svc.replicas < 1:
            errors.append(f"Service '{svc.name}': replicas must be >= 1")

        # Validate ports
        for port in svc.ports:
            if port.host <= 0 or port.host > 65535:
                errors.append(f"Service '{svc.name}': invalid host port {port.host}")
            if port.container <= 0 or port.container > 65535:
                errors.append(f"Service '{svc.name}': invalid container port {port.container}")

    return errors
