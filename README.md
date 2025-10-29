# LangGraph App Builder API

A FastAPI-based application powered by LangGraph and Groq for building interactive AI agents with code generation capabilities.

## Features

- 🤖 AI-powered code generation and planning
- 🔄 Multi-node agent workflow (Router, Planner, Coder, Clarifier)
- 🛠️ File manipulation tools (create, read, update, delete)
- 💾 Session-specific file directories (automatically cleared on new chat)
- 💬 Streaming chat responses
- 📝 Session management and conversation history
- 🚀 Production-ready with Docker support

## Prerequisites

- Python 3.11+
- uv (recommended) or pip
- Docker & Docker Compose (for containerized deployment)
- Groq API key

## Quick Start

### Local Development

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/langgraph-app-builder/api
   ```

2. **Create a `.env` file with your API keys:**
   ```bash
   cat > .env << EOF
   GROQ_API_KEY=your_groq_api_key_here
   LOG_LEVEL=INFO
   EOF
   ```

3. **Install dependencies with uv:**
   ```bash
   uv sync
   ```

4. **Run the application:**
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

5. **Access the API:**
   - API: http://localhost:8080
   - Health check: http://localhost:8080/health
   - API docs: http://localhost:8080/docs

### Docker Deployment

#### Option 1: Using Docker Compose (Recommended)

1. **Create a `.env` file** (see Quick Start step 2)

2. **Build and run:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the service:**
   ```bash
   docker-compose down
   ```

#### Option 2: Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t langgraph-api .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name langgraph-api \
     -p 8080:8080 \
     -e GROQ_API_KEY=your_api_key_here \
     -v $(pwd)/output:/app/__out__ \
     langgraph-api
   ```

3. **View logs:**
   ```bash
   docker logs -f langgraph-api
   ```

## API Endpoints

### Chat Endpoints

#### POST `/v1/agent/chat`
Non-streaming chat endpoint.

**Request:**
```json
{
  "message": "Create a simple HTML page"
}
```

**Headers:**
```
x-session-id: your-session-id
```

**Response:**
```json
{
  "reply": "I'll create that for you..."
}
```

#### POST `/v1/agent/chat/stream`
Streaming chat endpoint using Server-Sent Events (SSE).

**Request:**
```bash
curl --location 'http://localhost:8080/v1/agent/chat/stream' \
--header 'Content-Type: application/json' \
--header 'x-session-id: test-session' \
--data '{
    "message": "Create a simple HTML page"
}'
```

**Response (SSE):**
```
data: {"type": "message", "node": "router", "text": "..."}

data: {"type": "message", "node": "planner", "text": "- Create index.html\n- Add basic structure"}

data: {"type": "message", "node": "coder", "text": "Creating the HTML file..."}

data: {"type": "done"}
```

#### GET `/v1/agent/chat/history`
Get conversation history for a session.

**Headers:**
```
x-session-id: your-session-id
```

**Response:**
```json
{
  "session_id": "test-session",
  "messages": [
    {
      "role": "human",
      "content": "Create a simple HTML page",
      "id": "...",
      "tools_used": null,
      "tool_response": null
    },
    {
      "role": "ai",
      "content": "I'll create that for you...",
      "id": "...",
      "tools_used": ["create_file"],
      "tool_response": {...}
    }
  ]
}
```

### File Management Endpoints

#### GET `/v1/agent/files`
Get list of all files in the session's output directory.

**Headers:**
```
x-session-id: your-session-id
```

**Query Parameters:**
- `include_content` (optional, boolean): If true, includes file contents in response

**Response:**
```json
{
  "session_id": "test-session",
  "files": [
    {
      "name": "index.html",
      "size": 1234,
      "content": "<!DOCTYPE html>..." // only if include_content=true
    },
    {
      "name": "styles.css",
      "size": 567,
      "content": null
    }
  ]
}
```

#### GET `/v1/agent/files/{filename}`
Get a specific file's content.

**Headers:**
```
x-session-id: your-session-id
```

**Response:**
Returns the file content with appropriate content-type header:
- `.html` → `text/html`
- `.css` → `text/css`
- `.js` → `application/javascript`
- `.json` → `application/json`
- Others → `text/plain`

**Example:**
```bash
curl --location 'http://localhost:8080/v1/agent/files/index.html' \
--header 'x-session-id: test-session'
```

### Health Endpoints

- `GET /health` - Basic health check
- `GET /health/db` - Database health check (if configured)

## Project Structure

```
api/
├── app/
│   ├── agent/
│   │   ├── nodes/           # Agent nodes (router, planner, coder, clarify)
│   │   ├── tools/           # File manipulation tools
│   │   ├── graph.py         # LangGraph workflow definition
│   │   ├── state.py         # State management
│   │   └── prompts.py       # System prompts
│   ├── routers/
│   │   └── agent.py         # FastAPI routes
│   ├── deps.py              # Dependencies
│   └── main.py              # FastAPI application
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## File System

The application uses a **session-specific file system** that stores all generated files in dedicated directories. This means:

- ✅ **Session isolation** - Each session has its own subdirectory under `__out__/`
- ✅ **Auto-cleanup** - Session directory is cleared automatically when starting a new chat
- ✅ **Direct access** - Files can be accessed directly from the `__out__/{session-id}/` directory
- ✅ **Persistence** - Files persist on disk throughout the conversation session
- ✅ **Easy debugging** - Generated files are accessible for inspection

### How It Works

1. Each session gets its own directory: `__out__/{session-id}/`
2. On the first message of a new chat, the session directory is automatically cleared
3. All file operations (create, read, update, delete) work with files on disk
4. Tools use `InjectedToolArg` to get the session_id from the request config
5. Files can be retrieved via the `/v1/agent/files` endpoints or directly from disk

### Accessing Generated Files

**List all files:**
```bash
curl 'http://localhost:8080/v1/agent/files' \
  -H 'x-session-id: your-session'
```

**Get a specific file:**
```bash
curl 'http://localhost:8080/v1/agent/files/index.html' \
  -H 'x-session-id: your-session'
```

**Get all files with content:**
```bash
curl 'http://localhost:8080/v1/agent/files?include_content=true' \
  -H 'x-session-id: your-session'
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key (required) | - |
| `OPENAI_API_KEY` | OpenAI API key (optional) | - |
| `LOG_LEVEL` | Logging level | `INFO` |

### Agent Configuration

The agent uses the following LLM models:
- **Router**: `llama-3.3-70b-versatile`
- **Planner**: `llama-3.3-70b-versatile`
- **Coder**: `llama-3.3-70b-versatile` (with tool binding)
- **Clarifier**: `llama-3.3-70b-versatile`

## Development

### Running Tests
```bash
uv run pytest
```

### Code Formatting
```bash
uv run black .
uv run isort .
```

### Type Checking
```bash
uv run mypy .
```

## Troubleshooting

### Common Issues

1. **"Tool choice is required, but model did not call a tool"**
   - Make sure you're using models optimized for tool calling
   - Check that your prompts are clear and specific

2. **Empty streaming responses**
   - Verify that your nodes are returning the correct state fields
   - Check that the streaming endpoint handles all node response types

3. **Permission denied for `__out__` directory**
   - Ensure the directory has proper permissions: `chmod 777 __out__`
   - In Docker, the volume mount should have correct permissions

## License

MIT

## Support

For issues and questions, please open an issue on the repository.

