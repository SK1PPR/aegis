# Quick Setup Guide

## Step 1: Build the Rust Parser (Optional, for validation)

```bash
cd ../container-lang
cargo build --release
cd ../nl2dsl-agent
```

## Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Configure OpenAI API Key

```bash
cp .env.example .env
```

Then edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
```

## Step 4: Run the Agent

```bash
python main.py
```

## Quick Test

Once running, try:
```
You: I need nginx web server on port 80
Agent: [will respond and ask if you want to generate]
You: yes, generate it
Agent: [will show DSL code]
You: /show
You: /save test.container
```

That's it! Enjoy building your containers with natural language!
