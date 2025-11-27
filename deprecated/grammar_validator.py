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


def validate_and_explain(program: dict) -> tuple[bool, str]:
    """
    Validate a program structure against DSL grammar rules.
    
    Args:
        program: Dictionary representing the program structure
        
    Returns:
        Tuple of (is_valid, explanation_message)
    """
    errors = []
    
    # Check if program has containers
    if not isinstance(program, dict):
        return False, "Program must be a dictionary"
    
    # Support both 'containers' and 'services' for compatibility
    containers = program.get('containers') or program.get('services')
    
    if not containers:
        return False, "Program must have a 'containers' field with at least one container"
    
    if not isinstance(containers, list):
        return False, "'containers' must be a list"
    
    if len(containers) == 0:
        return False, "Program must have at least one container"
    
    # Validate each container
    container_names = set()
    
    for i, container in enumerate(containers):
        container_errors = validate_container(container, i, container_names)
        errors.extend(container_errors)
        
        # Track container names for dependency validation
        if isinstance(container, dict) and 'name' in container:
            container_names.add(container['name'])
    
    # Validate dependencies reference existing containers
    for i, container in enumerate(containers):
        if isinstance(container, dict) and 'depends_on' in container:
            dep_errors = validate_dependencies(container, container_names, i)
            errors.extend(dep_errors)
    
    if errors:
        error_msg = "Validation failed:\n\n" + "\n".join(f"  • {err}" for err in errors)
        return False, error_msg
    
    return True, "✓ Program structure is valid"


def validate_container(container: dict, index: int, existing_names: set) -> List[str]:
    """Validate a single container structure."""
    errors = []
    prefix = f"Container {index + 1}"
    
    # Must be a dictionary
    if not isinstance(container, dict):
        errors.append(f"{prefix}: Must be a dictionary")
        return errors
    
    # Required fields
    if 'name' not in container:
        errors.append(f"{prefix}: Missing required field 'name'")
    else:
        name = container['name']
        if not isinstance(name, str):
            errors.append(f"{prefix}: 'name' must be a string")
        elif not name.strip():
            errors.append(f"{prefix}: 'name' cannot be empty")
        elif name in existing_names:
            errors.append(f"{prefix}: Duplicate container name '{name}'")
    
    if 'image' not in container:
        errors.append(f"{prefix}: Missing required field 'image'")
    else:
        image = container['image']
        if not isinstance(image, str):
            errors.append(f"{prefix}: 'image' must be a string")
        elif not image.strip():
            errors.append(f"{prefix}: 'image' cannot be empty")
    
    # Optional fields validation
    if 'ports' in container:
        port_errors = validate_ports(container['ports'], prefix)
        errors.extend(port_errors)
    
    if 'env' in container:
        env_errors = validate_env(container['env'], prefix)
        errors.extend(env_errors)
    
    if 'volumes' in container:
        volume_errors = validate_volumes(container['volumes'], prefix)
        errors.extend(volume_errors)
    
    if 'depends_on' in container:
        # Just validate structure here, actual dependency check done later
        if not isinstance(container['depends_on'], list):
            errors.append(f"{prefix}: 'depends_on' must be a list")
        else:
            for dep in container['depends_on']:
                if not isinstance(dep, str):
                    errors.append(f"{prefix}: 'depends_on' items must be strings")
    
    return errors


def validate_ports(ports: any, prefix: str) -> List[str]:
    """Validate port mappings."""
    errors = []
    
    if not isinstance(ports, list):
        errors.append(f"{prefix}: 'ports' must be a list")
        return errors
    
    for i, port in enumerate(ports):
        if not isinstance(port, dict):
            errors.append(f"{prefix}: Port {i + 1} must be a dictionary")
            continue
        
        if 'host' not in port:
            errors.append(f"{prefix}: Port {i + 1} missing 'host' field")
        elif not isinstance(port['host'], int):
            errors.append(f"{prefix}: Port {i + 1} 'host' must be an integer")
        elif not (1 <= port['host'] <= 65535):
            errors.append(f"{prefix}: Port {i + 1} 'host' must be between 1 and 65535")
        
        if 'container' not in port:
            errors.append(f"{prefix}: Port {i + 1} missing 'container' field")
        elif not isinstance(port['container'], int):
            errors.append(f"{prefix}: Port {i + 1} 'container' must be an integer")
        elif not (1 <= port['container'] <= 65535):
            errors.append(f"{prefix}: Port {i + 1} 'container' must be between 1 and 65535")
    
    return errors


def validate_env(env: any, prefix: str) -> List[str]:
    """Validate environment variables."""
    errors = []
    
    if not isinstance(env, list):
        errors.append(f"{prefix}: 'env' must be a list")
        return errors
    
    for i, var in enumerate(env):
        if not isinstance(var, dict):
            errors.append(f"{prefix}: Environment variable {i + 1} must be a dictionary")
            continue
        
        if 'key' not in var:
            errors.append(f"{prefix}: Environment variable {i + 1} missing 'key' field")
        elif not isinstance(var['key'], str):
            errors.append(f"{prefix}: Environment variable {i + 1} 'key' must be a string")
        elif not var['key'].strip():
            errors.append(f"{prefix}: Environment variable {i + 1} 'key' cannot be empty")
        
        if 'value' not in var:
            errors.append(f"{prefix}: Environment variable {i + 1} missing 'value' field")
        elif not isinstance(var['value'], str):
            errors.append(f"{prefix}: Environment variable {i + 1} 'value' must be a string")
    
    return errors


def validate_volumes(volumes: any, prefix: str) -> List[str]:
    """Validate volume mounts."""
    errors = []
    
    if not isinstance(volumes, list):
        errors.append(f"{prefix}: 'volumes' must be a list")
        return errors
    
    for i, vol in enumerate(volumes):
        if not isinstance(vol, dict):
            errors.append(f"{prefix}: Volume {i + 1} must be a dictionary")
            continue
        
        if 'host' not in vol:
            errors.append(f"{prefix}: Volume {i + 1} missing 'host' field")
        elif not isinstance(vol['host'], str):
            errors.append(f"{prefix}: Volume {i + 1} 'host' must be a string")
        elif not vol['host'].strip():
            errors.append(f"{prefix}: Volume {i + 1} 'host' cannot be empty")
        
        if 'container' not in vol:
            errors.append(f"{prefix}: Volume {i + 1} missing 'container' field")
        elif not isinstance(vol['container'], str):
            errors.append(f"{prefix}: Volume {i + 1} 'container' must be a string")
        elif not vol['container'].strip():
            errors.append(f"{prefix}: Volume {i + 1} 'container' cannot be empty")
    
    return errors


def validate_dependencies(container: dict, container_names: set, index: int) -> List[str]:
    """Validate that dependencies reference existing containers."""
    errors = []
    prefix = f"Container {index + 1}"
    
    if 'depends_on' not in container:
        return errors
    
    depends_on = container['depends_on']
    container_name = container.get('name', f'#{index + 1}')
    
    if not isinstance(depends_on, list):
        return errors  # Already checked in validate_container
    
    for dep in depends_on:
        if not isinstance(dep, str):
            continue  # Already checked in validate_container
        
        if dep not in container_names:
            errors.append(
                f"{prefix} ('{container_name}'): depends_on references non-existent container '{dep}'"
            )
        
        if dep == container_name:
            errors.append(
                f"{prefix} ('{container_name}'): cannot depend on itself"
            )
    
    return errors


def validate_program_grammar(program: dict) -> tuple[bool, List[str]]:
    """
    Validate program structure and return detailed errors.
    
    Args:
        program: Program dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Support both 'containers' and 'services'
    containers = program.get('containers') or program.get('services')
    
    if not containers:
        errors.append("Missing 'containers' field")
        return False, errors
    
    if not isinstance(containers, list):
        errors.append("'containers' must be a list")
        return False, errors
    
    container_names = set()
    
    for i, container in enumerate(containers):
        container_errors = validate_container(container, i, container_names)
        errors.extend(container_errors)
        
        if isinstance(container, dict) and 'name' in container:
            container_names.add(container['name'])
    
    # Validate dependencies
    for i, container in enumerate(containers):
        if isinstance(container, dict) and 'depends_on' in container:
            dep_errors = validate_dependencies(container, container_names, i)
            errors.extend(dep_errors)
    
    return len(errors) == 0, errors