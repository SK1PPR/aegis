# Container-Lang DSL Conversational Agent

A terminal-based conversational AI agent that converts natural language descriptions into container-lang DSL code.

## Features

- **Conversational Interface**: Chat naturally about your infrastructure needs
- **Intelligent Code Generation**: Uses OpenAI's structured output for reliable DSL generation
- **Grammar Validation**: Automatic validation against DSL grammar rules with auto-correction
- **Interactive Refinement**: Iterate on your design through back-and-forth conversation
- **Multi-Layer Validation**: Grammar rules + optional Rust parser validation
- **Rich Terminal UI**: Beautiful syntax highlighting and formatting

## Prerequisites

- Python 3.9+
- OpenAI API key
- (Optional) container-lang Rust compiler for validation

## Installation

1. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set up your OpenAI API key**:
```bash
cp .env.example .env
# Edit .env and add your API key
```

3. **(Optional) Build the Rust parser for validation**:
```bash
cd ../container-lang
cargo build --release
cd ../nl2dsl-agent
```

## Usage

Start the conversational agent:

```bash
python main.py
```

### Commands

- `/show` - Display current generated DSL code
- `/validate` - Validate code with Rust parser
- `/save <filename>` - Save DSL code to file
- `/reset` - Start a new conversation
- `/help` - Show help
- `/quit` - Exit

### Example Conversations

**Example 1: Simple Web Server**
```
You: I need a web server
Agent: I can help you set up a web server! A few questions:
      1. Which web server? (nginx, apache, or caddy)
      2. What ports should it listen on?
      3. Do you have static files to serve?

You: nginx on port 80
Agent: Great! I'll create an nginx web server on port 80.
      Should I generate the code now?

You: yes
Agent: Here's your nginx web server configuration:
      [Displays generated DSL code]

You: /save web.container
Agent: Saved to web.container
```

**Example 2: Full Stack Application**
```
You: I need a complete web application with nginx, a node api, and postgres database

Agent: I'll help you set up a full stack application! Let me clarify a few things:

      For nginx:
      - Ports: 80/443?

      For the Node API:
      - What image? (e.g., node:20, or a custom image)
      - What port does it run on?

      For PostgreSQL:
      - Database credentials?
      - Port (default 5432)?
      - Need persistent storage?

You: nginx on 80 and 443, node:20 api on port 3000, postgres on 5432 with user admin password secret

Agent: Perfect! Generating your full stack setup:
      [Displays multi-service DSL code]

You: /validate
Agent: Valid DSL code!
      [Shows validated code]
```

**Example 3: Iterative Refinement**
```
You: postgres database

Agent: I'll set up PostgreSQL for you. Questions:
      - Port? (default 5432)
      - Credentials?
      - Data volume for persistence?

You: just use defaults for now

Agent: [Generates basic postgres setup]

You: actually, I need 3 replicas and set the user to myapp

Agent: [Updates configuration with 3 replicas and custom user]

You: /show
Agent: [Displays updated code]
```

## How It Works

1. **Natural Language Processing**: Uses OpenAI GPT-4 with structured outputs
2. **Schema Validation**: Pydantic models ensure type safety
3. **Grammar Validation**: Validates against DSL grammar rules (identifiers, ports, volumes, etc.)
4. **Auto-Correction**: LLM automatically fixes validation errors (up to 2 retries)
5. **Code Generation**: Template-based DSL code generation from validated JSON
6. **Parser Validation**: (Optional) Validates against the actual Rust parser
7. **Conversation Context**: Maintains full conversation history for iterative refinement

## Architecture

```
Natural Language Input
       ↓
OpenAI API (Structured Output)
       ↓
Pydantic Schema Validation (types)
       ↓
Grammar Validation (syntax rules)
       ↓  ← Auto-retry if invalid (up to 2x)
       ↓
DSL Code Generator
       ↓
(Optional) Rust Parser Validation
       ↓
Final DSL Code
```

## Project Structure

```
nl2dsl-agent/
├── main.py                  # CLI interface
├── agent.py                 # Core conversational agent
├── schema.py                # Pydantic schemas
├── grammar_validator.py     # Grammar validation rules
├── dsl_generator.py         # DSL code generation
├── test_grammar.py          # Grammar validation tests
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── README.md                # This file
├── SETUP.md                 # Quick setup guide
└── GRAMMAR_VALIDATION.md    # Grammar validation documentation
```

## Tips for Best Results

1. **Be Specific**: Mention ports, environment variables, and volumes when you know them
2. **Iterate**: Start simple and refine through conversation
3. **Use Commands**: Use `/show` frequently to see current state
4. **Validate Early**: Use `/validate` to catch issues before saving
5. **Ask Questions**: The agent will guide you if it needs more information

## Common Patterns

The agent knows common container patterns:

- **Web servers**: nginx, apache, caddy
- **Databases**: postgres, mysql, mongodb, redis
- **Runtimes**: node, python, java
- **Standard ports**: 80/443 (web), 5432 (postgres), 3306 (mysql), 6379 (redis)

## Troubleshooting

**"OPENAI_API_KEY not found"**
- Make sure you created `.env` file with your API key

**"Parser not found"**
- Build the Rust compiler: `cd ../container-lang && cargo build --release`
- Or skip validation and just use the generated code

**API Errors**
- Check your API key is valid
- Ensure you have internet connection
- Verify you have API credits

## Example Output

```
service web {
  image "nginx:latest"
  replicas 2
  ports 80:80,443:443
  volumes "./html:/usr/share/nginx/html"
}

service api {
  image "node:20"
  replicas 3
  ports 3000:3000
  env NODE_ENV=production
}

service db {
  image "postgres:16"
  replicas 1
  ports 5432:5432
  env POSTGRES_USER=admin,POSTGRES_PASSWORD=secret
  volumes "./data:/var/lib/postgresql/data"
}
```

## License

Same as container-lang project.
