# Landing Pages API Documentation

Complete system for managing user landing pages created by the LangGraph agent system.

## Overview

Landing pages are **automatically created and managed by the agent system**, not manually through REST API. When a user calls `/v1/agent/init` to start a new landing page generation, the system:

1. Creates a landing page record with status `pending`
2. Starts the LangGraph agent workflow
3. Updates status to `generating` when agents start working
4. Updates status to `generated` (with deployment URL) when deployment succeeds
5. Updates status to `failed` if deployment or generation fails

## Features

- ✅ Automatic creation via `/v1/agent/init` endpoint
- ✅ Track status (pending, generating, generated, failed)
- ✅ Store deployment URLs
- ✅ User authentication and authorization
- ✅ Pagination support
- ✅ Status filtering
- ✅ Automatic timestamps
- ✅ Integrated with LangGraph multi-agent system

## Database Schema

### Landing Pages Collection

```javascript
{
  "_id": "uuid",                          // Unique landing page ID
  "user_id": "uuid",                      // Owner user ID
  "session_id": "session-123",            // LangGraph session ID
  "status": "generated",                  // pending | generating | generated | failed
  "preview_url": null,                    // Preview URL (reserved for future use)
  "deployment_url": "https://session-123.vercel.app",  // Vercel deployment URL (format: {session_id}.vercel.app)
  "created_at": ISODate("2024-01-01"),   // Creation timestamp
  "updated_at": ISODate("2024-01-01")    // Last update timestamp
}
```

**URL Format:**
- Deployment URLs follow the pattern: `https://{session_id}.vercel.app`
- Example: session ID `abc123` → `https://abc123.vercel.app`

### Indexes

- `user_id` - For efficient user queries
- `session_id` (unique) - For session lookups
- `status` - For status filtering
- `(user_id, status)` - Compound index for user + status queries
- `created_at` - For sorting by date

## API Endpoints

All landing page viewing endpoints require JWT authentication and are prefixed with `/v1/landing-pages`

**Note:** Landing pages are created automatically via `/v1/agent/init`, not through a direct creation endpoint.

### 1. Start Landing Page Generation

**POST** `/v1/agent/init/stream` (requires authentication)

Start a new landing page generation. This endpoint automatically creates a landing page record and starts the agent workflow.

```bash
curl -X POST "http://localhost:8080/v1/agent/init/stream" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Session-Id: my-session-123" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "campaign": {
        "objective": "Generate leads",
        "productName": "My Product"
      }
    }
  }'
```

The system will:
1. Create a landing page record with status `pending`
2. Start the agent workflow (router → designer → coder → deployer)
3. Update status to `generating` when work begins
4. Update status to `generated` (with deployment URL) on success
5. Stream agent progress back to client

### 2. List User's Landing Pages

**GET** `/v1/landing-pages/`

Get all landing pages for the authenticated user with pagination.

**Query Parameters:**
- `page` (optional, default: 1) - Page number
- `page_size` (optional, default: 50, max: 100) - Items per page
- `status_filter` (optional) - Filter by status: `pending`, `generating`, `generated`, `failed`

```bash
curl -X GET "http://localhost:8080/v1/landing-pages/?page=1&page_size=20&status_filter=generated" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user-uuid",
      "session_id": "my-session-123",
      "status": "generated",
      "preview_url": "http://localhost:3000",
      "deployment_url": "https://my-app.vercel.app",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:01:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 3. Get Landing Page by ID

**GET** `/v1/landing-pages/{landing_page_id}`

Get a specific landing page by its ID.

```bash
curl -X GET "http://localhost:8080/v1/landing-pages/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid",
  "session_id": "my-session-123",
  "status": "generated",
  "preview_url": "http://localhost:3000",
  "deployment_url": "https://my-app.vercel.app",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:01:00Z"
}
```

### 4. Get Landing Page by Session ID

**GET** `/v1/landing-pages/session/{session_id}`

Get a landing page by its session ID.

```bash
curl -X GET "http://localhost:8080/v1/landing-pages/session/my-session-123" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:** Same as Get by ID

### 5. Update Landing Page

**PATCH** `/v1/landing-pages/{landing_page_id}`

Update a landing page's status and URLs.

```bash
curl -X PATCH "http://localhost:8080/v1/landing-pages/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "generated",
    "preview_url": "http://localhost:3000",
    "deployment_url": "https://my-app.vercel.app"
  }'
```

**Request Body:** (all fields optional)
```json
{
  "status": "generated",
  "preview_url": "http://localhost:3000",
  "deployment_url": "https://my-app.vercel.app"
}
```

**Response:** Updated landing page object

### 6. Delete Landing Page

**DELETE** `/v1/landing-pages/{landing_page_id}`

Delete a landing page (only if owned by the user).

```bash
curl -X DELETE "http://localhost:8080/v1/landing-pages/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:** `204 No Content`

## Status Flow

Landing pages go through the following status flow:

```
pending → generating → generated
                    ↓
                  failed
```

- **pending**: Initial state, waiting to be processed
- **generating**: Currently being generated by the agent
- **generated**: Successfully generated and deployed
- **failed**: Generation or deployment failed

## Python Utility Functions

The `app/utils/landing_pages.py` module provides utility functions for internal use:

### `create_landing_page(user_id, landing_page_data)`
Create a new landing page for a user.

### `get_landing_page_by_id(landing_page_id)`
Get a landing page by its ID.

### `get_landing_page_by_session_id(session_id)`
Get a landing page by its session ID.

### `get_user_landing_pages(user_id, skip, limit, status_filter)`
Get all landing pages for a user with pagination and filtering.

### `update_landing_page(landing_page_id, update_data)`
Update a landing page.

### `delete_landing_page(landing_page_id, user_id)`
Delete a landing page (with authorization check).

### `update_landing_page_status(session_id, status, preview_url, deployment_url)`
Convenience function to update status by session ID.

## Agent Integration (Automatic)

Landing pages are automatically managed by the LangGraph agent system:

### 1. Creation (`/v1/agent/init`)
When a user calls `/init/stream` with authentication:
- Landing page record is created with status `pending`
- Agent workflow starts
- Session ID is passed to all agent nodes

### 2. Status Updates (Agent Nodes)

**Router Node** (`app/agent/nodes/router.py`):
```python
# Sets status to "generating" when design work starts
update_landing_page_status(
    session_id=session_id,
    status=LandingPageStatus.GENERATING
)
```

**Deployer Node** (`app/agent/nodes/deployer.py`):
```python
# On success: construct URL using predictable Vercel format
# Format: https://{session_id}.vercel.app
deployment_url = f"https://{session_id}.vercel.app"

update_landing_page_status(
    session_id=session_id,
    status=LandingPageStatus.GENERATED,
    deployment_url=deployment_url
)

# On failure: set status to "failed"
update_landing_page_status(
    session_id=session_id,
    status=LandingPageStatus.FAILED
)
```

**Note:** Vercel deployment URLs follow the predictable format `https://{session_id}.vercel.app`, so the URL is constructed rather than parsed from output.

### Agent Flow with Status Updates

```
User calls /init (authenticated)
  ↓
Create landing page (status: pending)
  ↓
Router node → Set status: generating
  ↓
Designer → Coder → Deployer nodes
  ↓
Deployer succeeds → Set status: generated (with URL)
OR
Deployer fails → Set status: failed
```

## Authorization

All endpoints require:
1. Valid JWT access token in Authorization header
2. User can only access their own landing pages
3. Attempts to access other users' landing pages return `403 Forbidden`

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to access this landing page"
}
```

### 404 Not Found
```json
{
  "detail": "Landing page not found"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Database connection unavailable"
}
```

## Testing with cURL

### Complete Workflow

```bash
# 1. Register a user
curl -X POST "http://localhost:8080/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# 2. Login
ACCESS_TOKEN=$(curl -X POST "http://localhost:8080/v1/auth/login" \
  -d "email=test@example.com&password=password123" | jq -r '.access_token')

# 3. Start a landing page generation (creates landing page automatically)
curl -X POST "http://localhost:8080/v1/agent/init/stream" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Session-Id: test-session-1" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "campaign": {
        "objective": "Generate leads",
        "productName": "My Product",
        "primaryOffer": "Free trial"
      },
      "audience": {
        "description": "Tech-savvy entrepreneurs"
      }
    }
  }'
# This endpoint streams the agent's progress
# Landing page is created automatically with status "pending"
# Status updates to "generating" when agents start work
# Status updates to "generated" when deployment succeeds

# 4. List all your landing pages
curl -X GET "http://localhost:8080/v1/landing-pages/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 5. Get specific landing page by session ID
curl -X GET "http://localhost:8080/v1/landing-pages/session/test-session-1" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 6. Filter by status
curl -X GET "http://localhost:8080/v1/landing-pages/?status_filter=generated" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Environment Variables

Add to your `.env` file:

```bash
# MongoDB Landing Pages Collection
MONGODB_LANDING_PAGES_COLLECTION=landing_pages
```

The default value is `landing_pages` if not specified.

