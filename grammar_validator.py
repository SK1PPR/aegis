"""Grammar validation based on container-lang EBNF rules."""

import re
from typing import List
from schema import Program, Service


# Grammar patterns from container.ebnf
IDENT_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')
NUMBER_PATTERN = re.compile(r'^[0-9]+$')

# Docker image format: [registry/][namespace/]name[:tag][@digest]
# Simplified but covers most cases
IMAGE_PATTERN = re.compile(
    r'^([a-z0-9]+([\.\-][a-z0-9]+)*(\:[0-9]+)?/)?'  # Optional registry
    r'([a-z0-9_-]+/)?'  # Optional namespace
    r'[a-z0-9_-]+'  # Image name
    r'(:[a-z0-9_\.-]+)?'  # Optional tag
    r'(@sha256:[a-f0-9]{64})?$',  # Optional digest
    re.IGNORECASE
)


def validate_identifier(name: str, context: str) -> List[str]:
    """Validate an identifier according to grammar rules."""
    errors = []

    if not name:
        errors.append(f"{context}: identifier cannot be empty")
        return errors

    if not IDENT_PATTERN.match(name):
        errors.append(
            f"{context}: '{name}' is not a valid identifier. "
            f"Must start with letter or underscore, followed by letters, numbers, underscores, or hyphens."
        )

    return errors


def validate_image_format(image: str, service_name: str) -> List[str]:
    """Validate Docker image format."""
    errors = []

    if not image:
        errors.append(f"Service '{service_name}': image cannot be empty")
        return errors

    # Allow simple names like "nginx" or "ubuntu:latest"
    # Also allow full registry paths
    simple_pattern = re.compile(r'^[a-z0-9_-]+$', re.IGNORECASE)
    simple_with_tag = re.compile(r'^[a-z0-9_-]+:[a-z0-9_\.-]+$', re.IGNORECASE)

    if not (simple_pattern.match(image) or
            simple_with_tag.match(image) or
            IMAGE_PATTERN.match(image)):
        errors.append(
            f"Service '{service_name}': '{image}' is not a valid Docker image format. "
            f"Expected format: [registry/]name[:tag] (e.g., 'nginx:latest', 'ghcr.io/org/app:v1.0')"
        )

    return errors


def validate_volume_format(volume: str, service_name: str) -> List[str]:
    """Validate volume mapping format."""
    errors = []

    if not volume:
        errors.append(f"Service '{service_name}': volume mapping cannot be empty")
        return errors

    # Volume format: "host_path:container_path[:mode]"
    parts = volume.split(':')

    if len(parts) < 2:
        errors.append(
            f"Service '{service_name}': invalid volume format '{volume}'. "
            f"Expected 'host_path:container_path' or 'host_path:container_path:mode'"
        )
    elif len(parts) > 3:
        errors.append(
            f"Service '{service_name}': invalid volume format '{volume}'. "
            f"Too many colons. Expected 'host_path:container_path' or 'host_path:container_path:mode'"
        )

    # Validate mode if present
    if len(parts) == 3:
        mode = parts[2]
        if mode not in ['ro', 'rw']:
            errors.append(
                f"Service '{service_name}': invalid volume mode '{mode}'. "
                f"Must be 'ro' (read-only) or 'rw' (read-write)"
            )

    return errors


def validate_service_grammar(service: Service) -> List[str]:
    """Validate a service against grammar rules."""
    errors = []

    # Validate service name
    errors.extend(validate_identifier(service.name, "Service name"))

    # Validate image format
    errors.extend(validate_image_format(service.image, service.name))

    # Validate environment variable keys
    for env_var in service.env:
        errors.extend(
            validate_identifier(env_var.key, f"Service '{service.name}' env var key")
        )

    # Validate volume formats
    for volume in service.volumes:
        errors.extend(validate_volume_format(volume, service.name))

    # Port validation (should be numbers 1-65535) - already done in dsl_generator
    # but let's add format check
    for port in service.ports:
        if port.host < 1 or port.host > 65535:
            errors.append(
                f"Service '{service.name}': host port {port.host} out of range (1-65535)"
            )
        if port.container < 1 or port.container > 65535:
            errors.append(
                f"Service '{service.name}': container port {port.container} out of range (1-65535)"
            )

    # Validate replicas (should be positive number) - already in dsl_generator
    if service.replicas < 1:
        errors.append(
            f"Service '{service.name}': replicas must be at least 1 (got {service.replicas})"
        )

    return errors


def validate_program_grammar(program: Program) -> List[str]:
    """Validate entire program against grammar rules."""
    errors = []

    if not program.services:
        errors.append("Program must have at least one service")
        return errors

    # Check for duplicate service names
    seen_names = set()
    for service in program.services:
        if service.name in seen_names:
            errors.append(f"Duplicate service name: '{service.name}'")
        seen_names.add(service.name)

        # Validate each service
        errors.extend(validate_service_grammar(service))

    return errors


def validate_and_explain(program: Program) -> tuple[bool, str]:
    """
    Validate program and return (is_valid, message).
    If invalid, message explains all errors clearly.
    """
    errors = validate_program_grammar(program)

    if not errors:
        return True, "✓ Program passes all grammar validation rules"

    error_message = "Grammar validation failed:\n"
    for i, error in enumerate(errors, 1):
        error_message += f"  {i}. {error}\n"

    return False, error_message
