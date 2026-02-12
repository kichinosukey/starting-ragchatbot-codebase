# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval-Augmented Generation) chatbot system that answers questions about course materials. It uses ChromaDB for vector storage, Anthropic's Claude API for intelligent responses via tool calling, and provides a web-based chat interface.

## Development Commands

### Start the application
```bash
./run.sh
```
Or manually:
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Install/sync dependencies
```bash
uv sync
```

### Environment setup
Create `.env` file in project root:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture

### Core Data Flow: Tool-Based RAG Pattern

This system uses a **tool-calling architecture** where Claude decides when to search:

1. **User Query** → Frontend (`script.js`) sends POST to `/api/query`
2. **Session Management** → `SessionManager` creates/retrieves session with conversation history (limited to last 2 exchanges)
3. **RAG Orchestration** → `RAGSystem.query()` passes query + history to `AIGenerator`
4. **Claude Decision Point** → Claude receives query with `search_course_content` tool definition and decides:
   - **General knowledge question** → Answers directly without searching
   - **Course-specific question** → Calls `search_course_content` tool with optional `course_name` and `lesson_number` filters
5. **Tool Execution** (if needed) → `ToolManager` → `CourseSearchTool` → `VectorStore.search()`
6. **Vector Search** → ChromaDB semantic search on embeddings with metadata filtering
7. **Claude Synthesis** → Second API call with tool results, Claude generates final answer
8. **Response + Sources** → Frontend displays answer with collapsible sources section

**Key Insight**: This is NOT a traditional "always search, then generate" RAG. Claude autonomously decides IF and WHEN to search based on the question type.

### Component Responsibilities

**Backend (`/backend`):**
- `app.py` - FastAPI server with 3 endpoints: `/api/query`, `/api/courses`, static file serving
- `rag_system.py` - Main orchestrator connecting all components
- `ai_generator.py` - Claude API wrapper with tool execution handler
- `search_tools.py` - Tool definitions (abstract `Tool` base class, `CourseSearchTool`, `ToolManager`)
- `vector_store.py` - ChromaDB wrapper with TWO collections:
  - `course_catalog`: Course metadata for semantic course name resolution
  - `course_content`: Text chunks with embeddings for semantic search
- `document_processor.py` - Parses course documents, chunks text with sentence-aware splitting
- `session_manager.py` - Per-session conversation history (limited to `MAX_HISTORY` exchanges)
- `models.py` - Pydantic models (`Course`, `Lesson`, `CourseChunk`)
- `config.py` - Configuration dataclass with all settings

**Frontend (`/frontend`):**
- Vanilla JavaScript (no framework)
- `script.js` handles API calls, maintains `currentSessionId` for multi-turn conversations
- `marked.js` for markdown rendering in assistant responses

### Document Processing Pipeline

Course documents in `/docs` are processed on server startup:

1. **File Reading** → UTF-8 encoding with fallback
2. **Metadata Extraction** → Parses first 3-4 lines for:
   ```
   Course Title: [title]
   Course Link: [url]
   Course Instructor: [name]
   ```
3. **Lesson Parsing** → Regex match on `Lesson \d+: [title]` markers
4. **Text Chunking** → Smart sentence-based splitting:
   - Chunk size: 800 chars (configurable via `config.CHUNK_SIZE`)
   - Overlap: 100 chars (configurable via `config.CHUNK_OVERLAP`)
   - Regex handles abbreviations (doesn't split on "Dr.", "U.S.A.", etc.)
5. **Context Enrichment** → Prepends course/lesson context to chunks:
   - First chunk: `"Lesson {N} content: {text}"`
   - Subsequent: `"Course {title} Lesson {N} content: {text}"`
6. **Storage** → Embeds with `all-MiniLM-L6-v2` (384-dim vectors) and stores in ChromaDB

### Vector Search Strategy

**Two-Collection Pattern:**
- `course_catalog`: Enables fuzzy course name matching (e.g., "computer" → "Building Towards Computer Use with Anthropic")
- `course_content`: Stores actual content chunks with metadata for filtering

**Search Process:**
1. If `course_name` provided → Resolve to exact course title via semantic search on `course_catalog`
2. Build ChromaDB filter from `course_title` and/or `lesson_number`
3. Semantic search on `course_content` collection with filters applied
4. Return top N results (default: 5 via `config.MAX_RESULTS`)

**Metadata Filtering:**
- Filter by exact course title: `{"course_title": "..."}`
- Filter by lesson number: `{"lesson_number": 3}`
- Combined: `{"$and": [{"course_title": "..."}, {"lesson_number": 3}]}`

### Configuration System

All settings live in `backend/config.py` as a dataclass:
- `ANTHROPIC_MODEL`: Default is `"claude-sonnet-4-20250514"`
- `CHUNK_SIZE`: 800 characters
- `CHUNK_OVERLAP`: 100 characters
- `MAX_RESULTS`: 5 search results
- `MAX_HISTORY`: 2 conversation exchanges (prevents context bloat)
- `CHROMA_PATH`: `"./chroma_db"` (persistent storage)

To modify behavior, edit these constants rather than hardcoding values.

### Session Management Pattern

Each user gets isolated conversation context:
- Sessions created on first query, ID returned to frontend
- Frontend includes `session_id` in subsequent requests
- History limited to last `MAX_HISTORY` exchanges (default: 2)
- History injected into Claude's system prompt as context
- Prevents token bloat in long conversations while maintaining continuity

### Tool System Extensibility

To add new tools:
1. Create class inheriting from `Tool` (abstract base class in `search_tools.py`)
2. Implement `get_tool_definition()` → Returns Anthropic tool schema
3. Implement `execute(**kwargs)` → Performs tool action
4. Register with `ToolManager.register_tool(tool)`
5. Claude automatically receives tool in definitions and can call it

Current tools: `CourseSearchTool` (semantic search with course/lesson filters)

### Important Patterns

**Startup Document Loading:**
- `app.py` startup event loads all `.txt`, `.pdf`, `.docx` files from `../docs`
- Checks existing courses in ChromaDB to avoid duplicates
- Only processes new courses (compares by `course.title`)

**Source Attribution:**
- `CourseSearchTool` tracks sources in `self.last_sources` during formatting
- `ToolManager.get_last_sources()` retrieves sources after generation
- Sources reset after each query to prevent leakage between requests

**Error Handling:**
- Empty search results: Tool returns "No relevant content found..." string
- Course name not found: "No course found matching '...'"
- ChromaDB errors caught and returned as `SearchResults.empty(error_msg)`

## Code Quality Tools

### Black Formatter

This project uses Black for automatic Python code formatting with the following configuration:

**Settings (`pyproject.toml`):**
- Line length: 88 characters (Black's default)
- Target version: Python 3.13
- Excluded directories: `.eggs`, `.git`, `.mypy_cache`, `.venv`, `venv`, `chroma_db`, `__pycache__`

**Usage:**
- `./format.sh check` - Check formatting without making changes
- `./format.sh format` - Apply Black formatting to all Python files
- `./format.sh diff` - Show detailed diff of formatting changes

All Python files in `backend/` and `main.py` are formatted with Black.

### Pre-commit Hooks

Pre-commit hooks run automatically before each `git commit`:

**Configured hooks (`.pre-commit-config.yaml`):**
1. **Black formatter** - Ensures all Python code follows formatting standards
2. **Trailing whitespace** - Removes trailing whitespace (excludes .md files)
3. **End-of-file fixer** - Ensures files end with a newline
4. **YAML validation** - Checks YAML files for syntax errors
5. **Large file check** - Prevents accidentally committing large files
6. **Merge conflict detection** - Detects unresolved merge conflict markers

**Installation:**
```bash
uv run pre-commit install
```

Once installed, hooks run automatically on `git commit`. To bypass hooks (use sparingly):
```bash
git commit --no-verify
```

### Quality Gate Script

`./quality-check.sh` runs comprehensive checks for CI/CD or pre-push validation:

1. Black formatting check (fails if not formatted)
2. Pytest test suite

This ensures code quality before merging or deploying.

### Development Workflow

**Before committing:**
1. Pre-commit hooks automatically format code and run checks
2. If hooks fail, fix issues and re-stage files
3. Commit proceeds once all hooks pass

**Manual formatting (if needed):**
```bash
./format.sh format
git add -u
git commit -m "Your message"
```

**Pre-push validation:**
```bash
./quality-check.sh  # Ensures formatting + tests pass
```

## Key Files to Understand

When modifying behavior, these are the critical files:

- `backend/rag_system.py` - Entry point for all queries, connects all components
- `backend/ai_generator.py` - Contains system prompt and tool execution logic
- `backend/vector_store.py` - Two-collection pattern and search implementation
- `backend/search_tools.py` - Tool definitions that Claude can call
- `backend/config.py` - All configurable parameters

## Adding New Course Documents

Place files in `/docs` directory with this format:
```
Course Title: [Your Course Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Lesson Title]
Lesson Link: [URL]
[Lesson content...]

Lesson 1: [Next Lesson]
[Content...]
```

Restart server to process new documents. They'll be chunked, embedded, and added to ChromaDB automatically.
