import os
from dotenv import load_dotenv
from google.cloud import storage
import io

from app.agent.utils.cloud_utils import get_secret

load_dotenv()

# Determine environment
ENV = os.getenv("ENV", "local")  # Default to local

print(f"Loading configuration for ENV: {ENV}")

if ENV == "local":
    load_dotenv()
elif ENV == "testing" and os.getenv("TRAVIS"):
    # Travis CI: Do nothing, use predefined env variables from .travis.yml
    pass
# else:
#     # Fetch `.env`-formatted secret from the dummy function
#     secret_data = get_secret("CAELLUM_API_SETTINGS")

#     # Load the secret variables into the environment
#     env_buffer = io.StringIO(secret_data)  # Convert string to file-like object
#     load_dotenv(stream=env_buffer, override=True)  # Load environment variables


class Config:
    PROJECT_NAME = "Caellum"
    DEBUG = ENV in ["local", "development"]  # Enable debug only in dev & local

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

    GCS_CLIENT = storage.Client() if ENV != "local" else None
    GS_BUCKET_NAME = os.getenv("GS_BUCKET_NAME", "builder-agent")

    OUTPUT_PATH = "./storage" if ENV in ["local", "testing"] else "/mnt/storage"

    # MongoDB settings
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "langgraph_app")
    MONGODB_USERS_COLLECTION = os.getenv("MONGODB_USERS_COLLECTION", "users")
    MONGODB_LANDING_PAGES_COLLECTION = os.getenv(
        "MONGODB_LANDING_PAGES_COLLECTION", "landing_pages"
    )
    MONGODB_JOBS_COLLECTION = os.getenv("MONGODB_JOBS_COLLECTION", "jobs")

    # JWT settings
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "your-secret-key-change-this-in-production"
    )
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_DAYS", "30"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "45")
    )
