"""Pydantic schemas for container-lang DSL structured output."""

from pydantic import BaseModel, Field
from typing import List, Optional


class PortMapping(BaseModel):
    """Port mapping from host to container."""
    host: int = Field(..., description="Host port")
    container: int = Field(..., description="Container port")


class EnvVar(BaseModel):
    """Environment variable key-value pair."""
    key: str = Field(..., description="Environment variable name")
    value: str = Field(..., description="Environment variable value")


class Service(BaseModel):
    """Represents a single service in the DSL."""
    name: str = Field(..., description="Service name (e.g., 'web', 'db', 'api')")
    image: str = Field(..., description="Docker image (e.g., 'nginx:latest', 'postgres:16')")
    replicas: int = Field(default=1, ge=1, description="Number of replicas (must be >= 1)")
    ports: List[PortMapping] = Field(
        default_factory=list,
        description="Port mappings from host to container"
    )
    env: List[EnvVar] = Field(
        default_factory=list,
        description="Environment variables"
    )
    volumes: List[str] = Field(
        default_factory=list,
        description="Volume mappings in format 'host_path:container_path'"
    )


class Program(BaseModel):
    """Represents a complete container-lang program."""
    services: List[Service] = Field(
        ...,
        min_length=1,
        description="List of services to deploy"
    )


class ConversationResponse(BaseModel):
    """Response from the LLM during conversation."""
    message: str = Field(..., description="Conversational response to the user")
    program: Optional[Program] = Field(
        None,
        description="Generated DSL program (only when user wants to generate code)"
    )
    needs_clarification: bool = Field(
        default=False,
        description="Whether the assistant needs more information"
    )
