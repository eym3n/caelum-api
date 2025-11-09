import os
from dotenv import load_dotenv
from google.cloud import storage
import io

from app.agent.utils.cloud_utils import get_secret

load_dotenv()

# Determine environment
ENV = os.getenv("ENV", "local")  # Default to local

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
