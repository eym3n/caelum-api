# Authentication System

A complete JWT-based authentication system with MongoDB for user management.

## Features

- ✅ User registration with email and password
- ✅ JWT-based authentication (access & refresh tokens)
- ✅ Password hashing with bcrypt
- ✅ Protected routes with FastAPI dependencies
- ✅ MongoDB for user storage
- ✅ Token refresh mechanism
- ✅ User roles (regular users and superusers)

## Setup

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .

# If you encounter any bcrypt-related errors, reinstall bcrypt:
pip uninstall bcrypt passlib -y && pip install bcrypt>=4.2.0
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Important environment variables:
- `MONGODB_URI`: MongoDB connection string (default: `mongodb://localhost:27017`)
- `JWT_SECRET_KEY`: Secret key for JWT signing (⚠️ **Change this in production!**)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Access token lifetime (default: 30 minutes)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token lifetime (default: 7 days)

### 3. Start MongoDB

Make sure MongoDB is running:

```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or using local MongoDB
mongod
```

### 4. Run the Application

```bash
python -m app.main
# or
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8080`

## API Endpoints

### Authentication Endpoints

All auth endpoints are prefixed with `/v1/auth`

#### 1. Register a New User

**POST** `/v1/auth/register`

```bash
curl -X POST "http://localhost:8080/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

Response:
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### 2. Login

**POST** `/v1/auth/login`

```bash
curl -X POST "http://localhost:8080/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=user@example.com&password=securepassword123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 3. Get Current User

**GET** `/v1/auth/me`

```bash
curl -X GET "http://localhost:8080/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### 4. Refresh Access Token

**POST** `/v1/auth/refresh`

```bash
curl -X POST "http://localhost:8080/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

Response:
```json
{
  "access_token": "NEW_ACCESS_TOKEN",
  "refresh_token": "NEW_REFRESH_TOKEN",
  "token_type": "bearer"
}
```

#### 5. Test Protected Endpoint

**GET** `/v1/auth/test-protected`

```bash
curl -X GET "http://localhost:8080/v1/auth/test-protected" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Protecting Your Routes

### Using the Authentication Dependencies

```python
from fastapi import APIRouter, Depends
from app.deps import get_current_user, get_current_superuser
from app.models.user import User

router = APIRouter()

# Require any authenticated user
@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.email}!"}

# Require superuser only
@router.get("/admin")
async def admin_route(current_user: User = Depends(get_current_superuser)):
    return {"message": "Admin access granted"}
```

## Security Best Practices

1. **Change JWT Secret Key**: Always use a strong, random secret key in production
   ```bash
   # Generate a secure secret key
   openssl rand -hex 32
   ```

2. **Use HTTPS**: Always use HTTPS in production to protect tokens in transit

3. **Token Expiration**: Keep access tokens short-lived (15-30 minutes)

4. **Store Tokens Securely**: 
   - Never store tokens in localStorage (vulnerable to XSS)
   - Use httpOnly cookies for web applications
   - Use secure storage on mobile apps

5. **Password Requirements**: Enforce strong password policies (minimum 8 characters)

6. **Rate Limiting**: Implement rate limiting on authentication endpoints

## Database Schema

### Users Collection

```javascript
{
  "_id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "hashed_password": "$2b$12$...",
  "is_active": true,
  "is_superuser": false,
  "created_at": ISODate("2024-01-01T00:00:00Z"),
  "updated_at": ISODate("2024-01-01T00:00:00Z")
}
```

Indexes:
- `email` (unique)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Client App                         │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP + JWT Bearer Token
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Application                   │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Auth Router (/v1/auth)                           │ │
│  │  - /register, /login, /refresh, /me               │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Auth Dependencies (deps.py)                       │ │
│  │  - get_current_user                                │ │
│  │  - get_current_superuser                           │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  JWT Utils (utils/jwt.py)                          │ │
│  │  - create_access_token                             │ │
│  │  - create_refresh_token                            │ │
│  │  - verify_token                                    │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Security Utils (utils/security.py)                │ │
│  │  - get_password_hash                               │ │
│  │  - verify_password                                 │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          │ pymongo
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    MongoDB Database                      │
│  - users collection                                      │
└─────────────────────────────────────────────────────────┘
```

## Troubleshooting

### MongoDB Connection Issues

If you see "Database connection unavailable":
1. Check MongoDB is running: `mongosh` or `mongo`
2. Verify `MONGODB_URI` in `.env`
3. Check network/firewall settings

### Token Validation Errors

If you get "Could not validate credentials":
1. Check token hasn't expired
2. Verify `JWT_SECRET_KEY` matches the one used to create the token
3. Ensure you're sending the token in the `Authorization: Bearer <token>` header

### Import Errors

If you see import errors after setup:
1. Run `uv sync` or `pip install -e .`
2. Check all dependencies are installed
3. Ensure you're using Python 3.11+

## Testing

You can test the authentication system using the FastAPI interactive docs:

1. Start the server
2. Go to `http://localhost:8080/docs`
3. Test the endpoints interactively

Or use the provided curl commands above.

## Next Steps

- [ ] Add email verification
- [ ] Add password reset functionality
- [ ] Add OAuth2 providers (Google, GitHub, etc.)
- [ ] Add rate limiting
- [ ] Add user profile management endpoints
- [ ] Add audit logging for security events

