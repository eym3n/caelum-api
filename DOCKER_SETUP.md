# Docker Setup Guide

## Services

### API Service
- **Image**: Custom built from Dockerfile
- **Port**: 8080
- **Volumes**: 
  - `./app` mounted for live reload
  - `./__out__` for output files

### MongoDB Service
- **Image**: mongo:7.0
- **Port**: 27017
- **Volume**: `mongodb_data` for persistent storage
- **Logging**: Disabled (no console logs)

## Environment Variables

Create a `.env` file in the project root with:

```bash
# Environment
ENV=local
APP_ENV=local
LOG_LEVEL=INFO

# MongoDB Configuration
MONGODB_URI=mongodb://db:27017
MONGODB_DB_NAME=langgraph_app
MONGODB_USERS_COLLECTION=users
MONGODB_LANDING_PAGES_COLLECTION=landing_pages

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# AI API Keys
OPENAI_API_KEY=your-openai-api-key
GROQ_API_KEY=your-groq-api-key
GOOGLE_API_KEY=your-google-api-key

# Vercel Deployment
VERCEL_TOKEN=your-vercel-token

# Google Cloud Storage (optional)
GS_BUCKET_NAME=builder-agent

# Storage
OUTPUT_PATH=./storage
```

## Quick Start

### 1. Start Services

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 2. Stop Services

```bash
# Stop services
docker-compose down

# Stop and remove volumes (delete data)
docker-compose down -v
```

### 3. View Logs

```bash
# View all logs
docker-compose logs -f

# View API logs only
docker-compose logs -f api

# MongoDB logs are disabled by default
```

### 4. Restart Services

```bash
# Restart all services
docker-compose restart

# Restart API only
docker-compose restart api
```

## MongoDB Management

### Access MongoDB Shell

```bash
# Via Docker
docker-compose exec db mongosh

# Or directly if MongoDB client is installed
mongosh mongodb://localhost:27017
```

### MongoDB Express (Web UI)

Uncomment the `mongo-express` service in `docker-compose.yml` to enable web UI:

```yaml
mongo-express:
  image: mongo-express:latest
  restart: unless-stopped
  environment:
    ME_CONFIG_MONGODB_URL: mongodb://db:27017/
    ME_CONFIG_BASICAUTH_USERNAME: ${MONGO_EXPRESS_USER:-admin}
    ME_CONFIG_BASICAUTH_PASSWORD: ${MONGO_EXPRESS_PASSWORD:-admin123}
  ports:
    - "8081:8081"
  depends_on:
    - db
  networks:
    - backend
```

Then access at: http://localhost:8081

### View Collections

```bash
# Connect to MongoDB
docker-compose exec db mongosh

# Switch to your database
use langgraph_app

# List collections
show collections

# View users
db.users.find().pretty()

# View landing pages
db.landing_pages.find().pretty()

# Count documents
db.users.countDocuments()
db.landing_pages.countDocuments()
```

### Backup and Restore

```bash
# Backup
docker-compose exec db mongodump --out=/data/backup

# Restore
docker-compose exec db mongorestore /data/backup
```

## Troubleshooting

### API Can't Connect to MongoDB

1. Check if MongoDB is healthy:
   ```bash
   docker-compose ps
   ```

2. Check MongoDB logs (temporarily enable logging):
   ```bash
   # Remove logging: driver: "none" from docker-compose.yml
   docker-compose restart db
   docker-compose logs db
   ```

3. Verify connection string:
   ```bash
   docker-compose exec api printenv MONGODB_URI
   ```

### Reset Everything

```bash
# Stop everything and remove volumes
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Start fresh
docker-compose up --build
```

### Check MongoDB Health

```bash
# Check health status
docker-compose exec db mongosh --eval "db.adminCommand('ping')"

# Should return: { ok: 1 }
```

## Development Workflow

### Hot Reload

The API service has the `./app` directory mounted, so code changes will trigger automatic reload (if using uvicorn with `--reload`).

### Installing Dependencies

```bash
# Rebuild after adding dependencies to pyproject.toml
docker-compose build api
docker-compose up api
```

### Running Tests

```bash
# Run tests inside container
docker-compose exec api pytest

# Or run specific test file
docker-compose exec api pytest tests/test_auth.py
```

## Security Notes

### Production Setup

For production, you should:

1. **Enable MongoDB Authentication**:
   ```yaml
   environment:
     MONGO_INITDB_ROOT_USERNAME: admin
     MONGO_INITDB_ROOT_PASSWORD: strong-password
   ```

2. **Update MONGODB_URI**:
   ```
   MONGODB_URI=mongodb://admin:strong-password@db:27017
   ```

3. **Change JWT Secret**:
   ```bash
   # Generate a secure secret
   openssl rand -hex 32
   ```

4. **Don't expose MongoDB port** (remove `ports` from db service)

5. **Use strong passwords** for all services

6. **Enable HTTPS** with reverse proxy (nginx/traefik)

## Port Reference

- **8080**: API Service
- **27017**: MongoDB (exposed for local tools)
- **8081**: MongoDB Express (optional, commented out)

## Volume Reference

- **mongodb_data**: Persistent MongoDB data storage
- **./app**: API source code (mounted for hot reload)
- **./__out__**: API output files

