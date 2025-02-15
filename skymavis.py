import requests
import json
import yaml
import os
from google.cloud import secretmanager


def config():
    if os.path.isfile("config.yml"):
        return yaml.safe_load(open("config.yml"))
    else:
        project_id = "622634013834"
        client = secretmanager.SecretManagerServiceClient()
        secret_id = "axie_keys"
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return yaml.safe_load(response.payload.data.decode("UTF-8"))


config = config()

HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'X-API-KEY': config["api_key"]
}

ENDPOINTS = {
    "latest_block": "blocks/latest/number",
    "approve_requests": "accounts/%s/activities/search",
    "latest_transactions": "tokens/transfers?fromBlock=%from&toBlock=%to&limit=100",
}


class SkyMavis:
    url = "https://api-gateway.skymavis.com/skynet/ronin/web3/v2/"
    _config = None

    @classmethod
    def latest_block(cls):
        endpoint = f"{cls.url}/{ENDPOINTS["latest_block"]}"
        response = json.loads(
            requests.request(
                "GET", endpoint,
                headers=HEADERS, data={}
            ).text)

        return int(response.get("result").get("blockNumber"))

    @classmethod
    def check_approve_request(cls, token, address):
        latest_block = SkyMavis.latest_block()
        payload = json.dumps({
            "fromBlock": latest_block - 400000,
            "toBlock": latest_block,
            "activityTypes": [
                "Approve"
            ]
        })

        url = f"{cls.url}/{ENDPOINTS["approve_requests"]}".replace(
            "%s", address)
        response = requests.request(
            "POST",
            url,
            headers=HEADERS,
            data=payload
        )
        res = json.loads(response.text)

        for val in res.get("result").get("items"):
            if val.get("details").get("contract").get("address") == token:
                return True
        return False

    @classmethod
    def latest_transactions(cls):
        to = cls.latest_block()

        url = f"{cls.url}/{ENDPOINTS["latest_transactions"]}".replace(
            "%to", str(to)).replace("%from", str(to-4))
        response = requests.request(
            "GET",
            url,
            headers=HEADERS,
            data={}
        )
        res = json.loads(response.text)
        return res


if __name__ == '__main__':
    SkyMavis.latest_transactions()
