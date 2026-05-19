from curl_cffi import requests
import json

url = "https://graphql-gateway.axieinfinity.com/graphql"
headers = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://app.axieinfinity.com",
    "Referer": "https://app.axieinfinity.com/"
}

query = {
    "operationName": "GetAxieLatest",
    "variables": {
        "from": 0,
        "size": 10,
        "sort": "Latest",
        "auctionType": "Sale"
    },
    "query": """
    query GetAxieLatest($auctionType: AuctionType, $from: Int, $sort: SortBy, $size: Int) {
        axies(auctionType: $auctionType, from: $from, sort: $sort, size: $size) {
            total
            results {
                id
                name
                class
                order {
                    id
                    currentPrice
                    currentPriceUsd
                    basePrice
                    endedPrice
                    maker
                    expiredAt
                }
            }
        }
    }
    """
}

print("=== BUSCANDO OS 10 ÚLTIMOS AXIES LISTADOS PARA VENDA ===")
r = requests.post(url, headers=headers, json=query, impersonate="chrome")

if r.status_code != 200:
    print(f"Erro na requisição: {r.status_code}")
    print(r.text[:500])
    exit(1)

data = r.json()
if "errors" in data:
    print("Erro do GraphQL:")
    print(json.dumps(data["errors"], indent=2))
    exit(1)

axies = data.get("data", {}).get("axies", {}).get("results", [])
total = data.get("data", {}).get("axies", {}).get("total", 0)

print(f"Total de Axies à venda atualmente: {total}\n")
print(f"{'ID':<12} | {'Nome':<30} | {'Classe':<10} | {'Preço (ETH)':<12} | {'Preço (USD)':<10}")
print("-" * 85)

for axie in axies:
    axie_id = axie.get("id")
    name = axie.get("name", "Sem Nome")
    if len(name) > 30:
        name = name[:27] + "..."
    class_name = axie.get("class", "Desconhecida")
    
    order = axie.get("order") or {}
    price_wei = int(order.get("currentPrice", 0))
    price_eth = price_wei / 1e18
    price_usd = float(order.get("currentPriceUsd", 0))
    
    print(f"#{axie_id:<11} | {name:<30} | {class_name:<10} | {price_eth:<12.6f} | ${price_usd:<9.2f}")
