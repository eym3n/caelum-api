# syntax=docker/dockerfile:1.7

# Multi-stage build for FastAPI + Uvicorn app defined in app/main.py
# Uses Python 3.12 slim image for smaller footprint. Adjust if specific version needed.

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
		PYTHONUNBUFFERED=1 \
		PIP_NO_CACHE_DIR=off \
		PIP_DISABLE_PIP_VERSION_CHECK=on \
		PIP_ROOT_USER_ACTION=ignore

# System deps (add build-essential if wheels fail)
RUN apt-get update && apt-get install -y --no-install-recommends \
		curl ca-certificates build-essential gnupg && \
		rm -rf /var/lib/apt/lists/*

# Install Node.js (for create-next-app, npm, npx). Using NodeSource setup for latest LTS (20.x)
RUN set -eux; \
	export NODE_MAJOR=20; \
	apt-get update; \
	apt-get install -y ca-certificates curl gnupg; \
	mkdir -p /etc/apt/keyrings; \
	curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg; \
	echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" > /etc/apt/sources.list.d/nodesource.list; \
	apt-get update; \
	apt-get install -y nodejs; \
	node -v; npm -v; \
	rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Separate layer for dependency metadata for better caching.
COPY pyproject.toml ./
# If you have a lock file (e.g., uv.lock or requirements.txt generated) copy it here for reproducible builds.

# Install build backend if needed (PEP 517). We use pip directly; consider uv or poetry if available.
RUN pip install --upgrade pip && pip wheel --no-deps . -w /tmp/wheels || true
RUN pip install .

# Copy application source plus supporting scripts/templates.
COPY app ./app
COPY scripts ./scripts
COPY template ./template
COPY entrypoint.sh ./entrypoint.sh

# Ensure scripts are executable
RUN chmod +x entrypoint.sh && \
	find scripts -type f -name '*.sh' -exec chmod +x {} +

# Expose app port (FastAPI served by uvicorn) - matches uvicorn.run port=8080
EXPOSE 8080

# Healthcheck hitting /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
	CMD curl -fsS http://127.0.0.1:8080/health || exit 1

# Default environment can be overridden at runtime
ENV APP_ENV=production \
	ENV=production

# Ensure entrypoint script is executable (helpful for local context before build)
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

# Create storage directory (used for session outputs) at build time; can be mounted/overridden
RUN mkdir -p /mnt/storage || true

# Development notes:
#   For local iterative dev you can mount the source and override CMD with --reload.
#   docker run -p 8080:8080 -v $(pwd)/app:/app/app <image> python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

