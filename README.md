# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Development Workflow

### Code Formatting

This project uses [Black](https://black.readthedocs.io/) for consistent Python code formatting with a line length of 88 characters.

**Check formatting:**
```bash
./format.sh check
```

**Apply formatting:**
```bash
./format.sh format
```

**Show formatting diff:**
```bash
./format.sh diff
```

### Pre-commit Hooks

Pre-commit hooks are configured to automatically format code and run checks before each commit:

**Install hooks** (one-time setup):
```bash
uv run pre-commit install
```

Once installed, the hooks will automatically run on `git commit` and:
- Format Python code with Black
- Remove trailing whitespace
- Fix end-of-file newlines
- Validate YAML files
- Check for large files
- Detect merge conflicts

### Quality Checks

Run comprehensive quality checks (formatting + tests):
```bash
./quality-check.sh
```

This script:
1. Checks code formatting with Black
2. Runs the full test suite with pytest

Use this before pushing code or in CI/CD pipelines.
