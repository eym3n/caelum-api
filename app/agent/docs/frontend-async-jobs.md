# Frontend Integration: Asynchronous Job Workflow

This document explains how the new asynchronous job system works across the `init` and `chat` endpoints, how to shape requests, and how to poll for real-time progress from the frontend.

## Overview

- Both `POST /v1/agent/init` and `POST /v1/agent/chat` now return immediately with a `job_id`.
- The full execution happens in the background; clients must poll `GET /v1/jobs/{job_id}`.
- Every job record contains a normalized list of events for each LangGraph node, with user-friendly `message` strings and machine-readable `data`.
- Job statuses follow `pending → running → completed` (or `failed`/`cancelled` on error).

All examples below assume the FastAPI app is mounted under `/v1`, requires a user token, and that you supply the session id via the usual `X-Session-Id` header (or the optional `session_id` field in the request body).

## Init Job

### Request

Send the init payload you previously streamed, nested under a `payload` key. Optional: pass `session_id` if you want to override the header value.

```jsonc
POST /v1/agent/init
Authorization: Bearer <token>
Content-Type: application/json
X-Session-Id: campaign-landing-42

{
  "session_id": "campaign-landing-42",
  "payload": {
    "campaign": {
      "objective": "Generate qualified signups for our beta waitlist",
      "productName": "AuroraAI Automations",
      "primaryOffer": "Join the private beta and receive 3 free automation recipes"
    },
    "audience": {
      "description": "Operations leaders at post-Series A SaaS startups",
      "personaKeywords": ["ops", "automation", "scale"],
      "uvp": "Reduce busywork with AI-driven workflows tuned for B2B SaaS teams"
    },
    "messaging": {
      "tone": "confident + helpful",
      "seoKeywords": ["workflow automation", "AI ops tooling"],
      "eventTracking": ["beta-cta", "feature-tour", "playbook-download"]
    },
    "branding": {
      "theme": "dark",
      "colorPalette": {
        "primary": "#7C3AED",
        "accent": "#FDE68A",
        "neutral": "#111827",
        "raw": "#F9FAFB"
      },
      "fonts": "General Sans for headings, Inter for body",
      "layoutPreference": "Split hero, storytelling scrollytelling",
      "sections": ["hero", "features", "stats", "pricing", "cta", "faq"]
    }
  }
}
```

### Immediate Response

```json
{
  "job_id": "b60b3566-f5c8-4a91-a920-71afbb55565d",
  "session_id": "campaign-landing-42",
  "landing_page_id": "a561aa73-08d7-49bd-9e89-052bcbed5c47"
}
```

The `landing_page_id` may be `null` if the record already exists or the database is unavailable. The job is in `pending` until the worker picks it up.

## Chat Job

### Request

```jsonc
POST /v1/agent/chat
Authorization: Bearer <token>
Content-Type: application/json
X-Session-Id: campaign-landing-42

{
  "message": "Please refine the testimonials section with more enterprise-friendly language."
}
```

### Immediate Response

```json
{
  "reply": "Chat job accepted. Poll /v1/jobs/b1d8bf52-4f3b-4dca-8d5b-5e6fa1acd2a2 for progress.",
  "job_id": "b1d8bf52-4f3b-4dca-8d5b-5e6fa1acd2a2"
}
```

Again, the real output comes from the job events you pull from `/v1/jobs/{job_id}`.

## Polling Job Status

Use the Jobs API to fetch the live state of any job.

```http
GET /v1/jobs/{job_id}
Authorization: Bearer <token>
```

### Response Shape

```jsonc
{
  "job": {
    "id": "b60b3566-f5c8-4a91-a920-71afbb55565d",
    "type": "init",
    "status": "running",
    "session_id": "random-session-id-3",
    "user_id": "edf7b05c-ad71-4a76-a5b5-d79e47c39452",
    "title": "Init request",
    "description": "Asynchronous init graph execution",
    "events": [
      {
        "id": "837e63df-68cf-47f3-8762-81d0ccb4188a",
        "node": "router",
        "timestamp": "2025-11-18T21:27:31.746000",
        "event_type": "node",
        "message": "Planning next steps...",
        "data": {}
      },
      {
        "id": "94dc6fca-df67-4290-b1e8-dfcaf83edae6",
        "node": "design_planner",
        "timestamp": "2025-11-18T21:29:09.010000",
        "event_type": "node_completed",
        "message": "Design planner generated comprehensive design guidelines.",
        "data": {
          "theme": "light",
          "color_count": 13,
          "typography_count": 3,
          "section_count": 10,
          "animation_count": 4
        }
      },
      // ...more events as the graph progresses...
      {
        "id": "1df96276-b9ac-47cf-9a68-c47b9698e0cf",
        "node": "coder",
        "timestamp": "2025-11-18T21:32:22.925000",
        "event_type": "node_completed",
        "message": "Coder completed implementation pass.",
        "data": {}
      }
    ],
    "created_at": "2025-11-18T21:27:31.585000",
    "updated_at": "2025-11-18T21:35:42.364000",
    "error_message": null
  }
}
```

- `status` moves from `pending` → `running` once the background task starts, and ends as `completed`, `failed`, or `cancelled`.
- The `events` array is ordered chronologically; new entries appear as the job runs.
- `event_type` is aligned with LangGraph events (`node`, `node_completed`, `tool`, `error`, etc.).
- `data` contains structured metadata: tool names, counts, validation details, and other per-node diagnostics.

### Polling Strategy

- Start polling immediately after receiving the `job_id`.
- Recommended interval: 1–2 seconds with exponential backoff after the job reaches a terminal state.
- Stop polling when `status` is one of `completed`, `failed`, or `cancelled`.
- On `failed`, surface `error_message` to the user and optionally offer a retry button.

### Event Consumption Tips

- Display the latest `message` per node for a timeline or activity feed UI.
- Use `data` for secondary detail panes (e.g., show how many files were created or the theme selected by the design planner).
- Tool-specific events come from `*_tools` nodes and already omit raw file contents; counts and tool metadata are safe to surface.

## End-to-End Flow Example

1. **Kick off init job**  
   - `POST /v1/agent/init` with payload + session headers.  
   - Receive `job_id`.
2. **Poll job timeline**  
   - Repeatedly call `GET /v1/jobs/{job_id}`.  
   - Update UI as new `events` arrive (`design_planner`, `designer`, `coder`, `deployment_fixer`, etc.).
3. **Detect completion**  
   - When `status === "completed"`, mark the session as ready.  
   - If `status === "failed"`, read `error_message` and the last few events to show remediation hints.
4. **Subsequent refinements**  
   - Use `POST /v1/agent/chat` for follow-up instructions.  
   - Poll the returned chat `job_id` with the same flow.

## Error Handling & Retries

- Any unhandled exception ends the job in `failed` and sets `error_message`.  
- The frontend can offer a retry by issuing a new init/chat job with the same session id.  
- Use the `deployment_fixer` events to show deployment remediation steps; the fixer logs updates, lint runs, and retry attempts explicitly.

## Appendix: Minimal Fetch Wrapper

```ts
async function runInitJob(payload: InitPayload, sessionId: string) {
  const initRes = await fetch("/v1/agent/init", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      "X-Session-Id": sessionId,
    },
    body: JSON.stringify({ session_id: sessionId, payload }),
  });

  const { job_id } = await initRes.json();

  let job;
  do {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const jobRes = await fetch(`/v1/jobs/${job_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    ({ job } = await jobRes.json());
    updateTimeline(job.events);
  } while (!["completed", "failed", "cancelled"].includes(job.status));

  return job;
}
```

Use the same poller for chat jobs—only the `type` field changes.


