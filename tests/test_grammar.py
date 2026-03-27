#!/usr/bin/env python3
"""Test script to demonstrate grammar validation."""

from schema import Service, Program, PortMapping, EnvVar
from grammar_validator import validate_and_explain
from dsl_generator import generate_dsl


def test_valid_program():
    """Test a valid program."""
    print("=" * 60)
    print("TEST 1: Valid Program")
    print("=" * 60)

    program = Program(services=[
        Service(
            name="web",
            image="nginx:latest",
            replicas=2,
            ports=[PortMapping(host=80, container=80)],
            env=[EnvVar(key="NODE_ENV", value="production")]
        )
    ])

    is_valid, message = validate_and_explain(program)
    print(f"\nResult: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(message)

    if is_valid:
        print("\nGenerated DSL:")
        print("-" * 40)
        print(generate_dsl(program))


def test_invalid_service_name():
    """Test invalid service name with spaces."""
    print("=" * 60)
    print("TEST 2: Invalid Service Name (contains spaces)")
    print("=" * 60)

    program = Program(services=[
        Service(
            name="my web server",  # Invalid: contains spaces
            image="nginx:latest",
            replicas=1
        )
    ])

    is_valid, message = validate_and_explain(program)
    print(f"\nResult: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(message)


def test_invalid_env_key():
    """Test invalid environment variable key."""
    print("=" * 60)
    print("TEST 3: Invalid Env Var Key (starts with number)")
    print("=" * 60)

    program = Program(services=[
        Service(
            name="api",
            image="node:20",
            replicas=1,
            env=[EnvVar(key="123_VAR", value="value")]  # Invalid: starts with number
        )
    ])

    is_valid, message = validate_and_explain(program)
    print(f"\nResult: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(message)


def test_invalid_port():
    """Test invalid port number."""
    print("=" * 60)
    print("TEST 4: Invalid Port Number (out of range)")
    print("=" * 60)

    program = Program(services=[
        Service(
            name="db",
            image="postgres:16",
            replicas=1,
            ports=[PortMapping(host=99999, container=5432)]  # Invalid: > 65535
        )
    ])

    is_valid, message = validate_and_explain(program)
    print(f"\nResult: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(message)


def test_invalid_volume():
    """Test invalid volume format."""
    print("=" * 60)
    print("TEST 5: Invalid Volume Format (missing colon)")
    print("=" * 60)

    program = Program(services=[
        Service(
            name="app",
            image="myapp:latest",
            replicas=1,
            volumes=["./data"]  # Invalid: missing container path
        )
    ])

    is_valid, message = validate_and_explain(program)
    print(f"\nResult: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(message)


def test_multiple_errors():
    """Test program with multiple validation errors."""
    print("=" * 60)
    print("TEST 6: Multiple Validation Errors")
    print("=" * 60)

    program = Program(services=[
        Service(
            name="bad-service-1",  # Valid
            image="not a valid image!!!",  # Invalid image
            replicas=1,
            ports=[PortMapping(host=70000, container=80)],  # Invalid port
            env=[EnvVar(key="BAD KEY", value="value")],  # Invalid: space in key
            volumes=["nocolon"]  # Invalid: missing colon
        )
    ])

    is_valid, message = validate_and_explain(program)
    print(f"\nResult: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(message)


if __name__ == "__main__":
    test_valid_program()
    print("\n")

    test_invalid_service_name()
    print("\n")

    test_invalid_env_key()
    print("\n")

    test_invalid_port()
    print("\n")

    test_invalid_volume()
    print("\n")

    test_multiple_errors()
