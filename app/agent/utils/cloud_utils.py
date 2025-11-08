import google.auth
from google.cloud import secretmanager


def get_secret(secret_name):
    _, project = google.auth.default()
    if project:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(name=name)

        return response.payload.data.decode("UTF-8")
    else:
        raise Exception("Google Cloud project not found.")
