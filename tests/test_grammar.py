#!/usr/bin/env python3
"""Smoke-test baseline DSL generation and validation helpers."""

import sys
from pathlib import Path

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.dsl_generator import generate_dsl, validate_program
from src.schema import EnvVar, PortMapping, Program, Service


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_valid_program() -> None:
    program = Program(
        services=[
            Service(
                name="web",
                image="nginx:latest",
                replicas=2,
                ports=[PortMapping(host=80, container=80)],
                env=[EnvVar(key="NODE_ENV", value="production")],
            )
        ]
    )

    errors = validate_program(program)
    check(errors == [], f"expected no errors, got {errors}")
    dsl = generate_dsl(program)
    check("service web" in dsl, "generated DSL should include service block")
    check('image "nginx:latest"' in dsl, "generated DSL should include image")


def test_invalid_port() -> None:
    program = Program(
        services=[
            Service(
                name="db",
                image="postgres:16",
                ports=[PortMapping(host=99999, container=5432)],
            )
        ]
    )

    errors = validate_program(program)
    check(errors == ["Service 'db': invalid host port 99999"], f"unexpected errors: {errors}")


def test_invalid_replicas_rejected_by_schema() -> None:
    try:
        Service(name="api", image="node:20", replicas=0)
    except ValidationError:
        return
    raise AssertionError("replicas=0 should fail schema validation")


def main() -> None:
    test_valid_program()
    test_invalid_port()
    test_invalid_replicas_rejected_by_schema()
    print("Baseline DSL grammar smoke tests passed")


if __name__ == "__main__":
    main()
