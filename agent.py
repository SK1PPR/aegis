"""Conversational agent for natural language to container-lang DSL."""

import os
import json
import subprocess
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
from schema import Program, ConversationResponse
from dsl_generator import generate_dsl, validate_program


# Load environment variables
load_dotenv()


class DSLAgent:
    """Conversational agent that converts natural language to DSL code."""

    SYSTEM_PROMPT = """You are an expert assistant that helps users create container-lang DSL code.

# About container-lang DSL
Container-lang is a simple declarative language for defining containerized services.

Syntax:
```
service <name> {
  image "<docker-image>"
  replicas <number>
  ports <host>:<container>[,<host>:<container>...]
  env <KEY>=<value>[,<KEY>=<value>...]
  volumes "<host-path>:<container-path>"[,"<host-path>:<container-path>"...]
}
```

Required fields:
- name: service identifier
- image: Docker image name

Optional fields:
- replicas: number of instances (default: 1)
- ports: port mappings (host:container)
- env: environment variables
- volumes: volume mounts

# Your role
1. Have a conversation with the user to understand what they want to deploy
2. Ask clarifying questions if needed (image versions, ports, env vars, etc.)
3. When ready, generate the structured Program
4. Help users refine the configuration through conversation

# Common patterns to suggest:
- Web servers: nginx, apache, caddy
- Databases: postgres, mysql, mongodb, redis
- APIs: node, python, go applications
- Standard ports: 80/443 (web), 5432 (postgres), 3306 (mysql), 6379 (redis), 27017 (mongodb)

# Conversation guidelines:
- Be concise and helpful
- Suggest reasonable defaults (e.g., nginx:latest for web servers)
- Ask about critical missing info (ports for web services, credentials for databases)
- Set needs_clarification=true if you need more information before generating
- Only include 'program' in your response when user explicitly wants to generate/update code
"""

    EXAMPLES = [
        {
            "user": "I need a web server",
            "assistant": {
                "message": "I can help you set up a web server! A few questions:\n1. Which web server? (nginx, apache, or caddy)\n2. What ports should it listen on?\n3. Do you have static files to serve?",
                "needs_clarification": True
            }
        },
        {
            "user": "nginx on port 80",
            "assistant": {
                "message": "Great! I'll create an nginx web server on port 80. Should I generate the code now?",
                "needs_clarification": False
            }
        },
        {
            "user": "yes, generate it",
            "assistant": {
                "message": "Here's your nginx web server configuration:",
                "program": {
                    "services": [{
                        "name": "web",
                        "image": "nginx:latest",
                        "replicas": 1,
                        "ports": [{"host": 80, "container": 80}]
                    }]
                },
                "needs_clarification": False
            }
        },
        {
            "user": "I need postgres database and redis cache",
            "assistant": {
                "message": "I'll set up PostgreSQL and Redis for you. For PostgreSQL, do you want to specify:\n1. Database credentials (user/password)?\n2. Port (default 5432)?\n3. Data persistence volume?\n\nFor Redis, default port 6379 is standard.",
                "needs_clarification": True
            }
        },
        {
            "user": "use default postgres on 5432 with user admin and password secret, redis on default port",
            "assistant": {
                "message": "Perfect! Generating your database and cache setup:",
                "program": {
                    "services": [
                        {
                            "name": "db",
                            "image": "postgres:16",
                            "replicas": 1,
                            "ports": [{"host": 5432, "container": 5432}],
                            "env": [
                                {"key": "POSTGRES_USER", "value": "admin"},
                                {"key": "POSTGRES_PASSWORD", "value": "secret"}
                            ]
                        },
                        {
                            "name": "cache",
                            "image": "redis:7",
                            "replicas": 1,
                            "ports": [{"host": 6379, "container": 6379}]
                        }
                    ]
                },
                "needs_clarification": False
            }
        }
    ]

    def __init__(self):
        """Initialize the agent with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=api_key)
        self.conversation_history: List[Dict[str, str]] = []
        self.current_program: Optional[Program] = None
        self.model = "gpt-4o-2024-08-06"  # Supports structured outputs

    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        """Build the message list for the API call."""
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # Add examples for few-shot learning
        for example in self.EXAMPLES:
            messages.append({"role": "user", "content": example["user"]})
            messages.append({"role": "assistant", "content": json.dumps(example["assistant"])})

        # Add conversation history
        messages.extend(self.conversation_history)

        # Add current message
        messages.append({"role": "user", "content": user_message})

        return messages

    def chat(self, user_message: str) -> ConversationResponse:
        """Send a message and get a structured response."""
        messages = self._build_messages(user_message)

        # Call OpenAI with structured output
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=ConversationResponse,
            temperature=0.7,
        )

        response = completion.choices[0].message.parsed

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({
            "role": "assistant",
            "content": json.dumps(response.model_dump())
        })

        # Update current program if provided
        if response.program:
            self.current_program = response.program

        return response

    def generate_code(self) -> Optional[str]:
        """Generate DSL code from current program."""
        if not self.current_program:
            return None

        # Validate before generating
        errors = validate_program(self.current_program)
        if errors:
            return f"Validation errors:\n" + "\n".join(f"  - {err}" for err in errors)

        return generate_dsl(self.current_program)

    def validate_with_parser(self, dsl_code: str, parser_path: str) -> tuple[bool, str]:
        """Validate DSL code using the Rust parser."""
        try:
            # Write to temp file
            temp_file = "/tmp/temp_dsl.container"
            with open(temp_file, "w") as f:
                f.write(dsl_code)

            # Run the parser
            result = subprocess.run(
                [parser_path, temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return True, "Valid DSL code!"
            else:
                return False, f"Parser error:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Parser timeout"
        except FileNotFoundError:
            return False, f"Parser not found at {parser_path}"
        except Exception as e:
            return False, f"Error running parser: {str(e)}"

    def reset(self):
        """Reset the conversation."""
        self.conversation_history = []
        self.current_program = None
