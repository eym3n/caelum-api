# LangGraph App Builder API

A FastAPI-based application powered by LangGraph and OpenAI for building interactive AI agents with **Next.js + React + TypeScript + Tailwind** code generation capabilities.

## Features

- ⚛️ **Next.js App Generation** - Full-stack React apps with TypeScript and Tailwind CSS
- 🤖 AI-powered code generation and planning
- 🔄 Multi-node agent workflow (Router, Planner, Coder, Clarifier)
- 🛠️ File manipulation tools (create, read, update, delete lines)
- 📦 Command execution tools (npm install, run dev server, init Next.js app)
- 💾 Session-specific project directories (automatically cleared on new chat)
- 💬 Streaming chat responses with real-time feedback
- 📝 Session management and conversation history
- 🚀 Production-ready with Docker support

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm (for Next.js app generation)
- uv (recommended) or pip
- Docker & Docker Compose (for containerized deployment)
- OpenAI API key (for GPT models)

## Quick Start

### Local Development

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/langgraph-app-builder/api
   ```

2. **Create a `.env` file with your API keys:**
   ```bash
   cat > .env << EOF
   OPENAI_API_KEY=your_openai_api_key_here
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
  "message": "Create a dashboard app with Next.js"
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
    "message": "Create a todo app with Next.js and Tailwind"
}'
```

**Response (SSE):**
```
data: {"type": "message", "node": "router", "text": "..."}

data: {"type": "message", "node": "planner", "text": "1. Initialize Next.js app\n2. Create TodoList component\n3. Style with Tailwind"}

data: {"type": "message", "node": "tools", "text": "Initializing Next.js app with TypeScript and Tailwind..."}

data: {"type": "message", "node": "coder", "text": "Creating the TodoList component..."}

data: {"type": "message", "node": "tools", "text": "Created src/components/TodoList.tsx (+45)"}

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
      "name": "package.json",
      "size": 456,
      "content": "{...}" // only if include_content=true
    },
    {
      "name": "src/app/page.tsx",
      "size": 1234,
      "content": null
    },
    {
      "name": "src/components/TodoList.tsx",
      "size": 2341,
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
- `.tsx`, `.ts` → `text/plain` (TypeScript)
- `.jsx`, `.js` → `application/javascript`
- `.json` → `application/json`
- `.css` → `text/css`
- `.html` → `text/html`
- Others → `text/plain`

**Example:**
```bash
curl --location 'http://localhost:8080/v1/agent/files/src/app/page.tsx' \
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
│   │   ├── tools/
│   │   │   ├── files.py     # File manipulation tools
│   │   │   └── commands.py  # Command execution tools (npm, Next.js init)
│   │   ├── graph.py         # LangGraph workflow definition
│   │   ├── state.py         # State management
│   │   └── prompts.py       # System prompts (Next.js-specific)
│   ├── routers/
│   │   └── agent.py         # FastAPI routes
│   ├── deps.py              # Dependencies
│   └── main.py              # FastAPI application
├── scripts/
│   ├── init_app.sh          # Initialize Next.js app
│   ├── install.sh           # Run npm install
│   ├── run_app.sh           # Start dev server
│   └── run_npm_command.sh   # Run arbitrary npm commands
├── __out__/                 # Session-specific Next.js projects
├── Dockerfile
├── pyproject.toml
└── README.md
```

## File System & Next.js Projects

The application uses a **session-specific file system** that stores complete Next.js projects in dedicated directories. This means:

- ⚛️ **Full Next.js Projects** - Each session creates a complete Next.js app with proper structure
- ✅ **Session isolation** - Each session has its own subdirectory under `__out__/`
- ✅ **Auto-cleanup** - Session directory is cleared automatically when starting a new chat
- ✅ **Direct access** - Projects can be accessed directly from the `__out__/{session-id}/` directory
- ✅ **Runnable apps** - Generated Next.js apps can be run locally with `npm run dev`
- ✅ **Persistence** - Projects persist on disk throughout the conversation session
- ✅ **Easy debugging** - All source files are accessible for inspection and modification

### How It Works

1. Each session gets its own directory: `__out__/{session-id}/`
2. On the first message of a new chat, the session directory is automatically cleared
3. The agent initializes a Next.js app using `create-next-app` with TypeScript, Tailwind, and App Router
4. All file operations (create, read, update, delete) work with files in the Next.js project
5. Command tools allow running npm commands and starting the dev server
6. Tools use `InjectedToolArg` to get the session_id from the request config
7. Files can be retrieved via the `/v1/agent/files` endpoints or directly from disk

### Running Generated Apps

Once the agent creates a Next.js app, you can run it locally:

```bash
cd __out__/{your-session-id}
npm run dev
```

The app will be available at `http://localhost:3000`

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
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `LOG_LEVEL` | Logging level | `INFO` |

### Agent Configuration

The agent uses the following OpenAI models:
- **Router**: `gpt-4o-mini` (for intent classification)
- **Planner**: `gpt-4.1` (for strategic planning with file access)
- **Coder**: `gpt-5-mini` (with file + command tools for Next.js development)
- **Clarifier**: `gpt-4.1-mini-2025-04-14` (with file reading tools)

### Command Tools

The agent has access to shell scripts for managing Next.js projects:

| Tool | Description | Timeout |
|------|-------------|---------|
| `init_nextjs_app` | Initialize a new Next.js app with TypeScript & Tailwind | 20s |
| `install_dependencies` | Run `npm install` in the project directory | 20s |
| `run_dev_server` | Start the Next.js dev server (`npm run dev`) | - |
| `run_npm_command` | Execute any npm command (e.g., install packages, build) | 20s |

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

