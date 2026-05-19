import os
import yaml
from google.cloud import secretmanager

def get_config():
    local_config = {}
    if os.path.isfile("config.yml"):
        with open("config.yml", "r", encoding="utf-8") as f:
            local_config = yaml.safe_load(f) or {}

    if "key" in local_config and "api_key" in local_config:
        return local_config

    project_id = local_config.get("project_id") or os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        raise ValueError("O 'project_id' precisa estar no config.yml ou na variável de ambiente GCP_PROJECT_ID")

    client = secretmanager.SecretManagerServiceClient()
    secret_id = "axie_keys"
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return yaml.safe_load(response.payload.data.decode("UTF-8"))

config = get_config()
