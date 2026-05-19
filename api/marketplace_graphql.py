from curl_cffi import requests
from core.config import config


# Fragments reutilizáveis para as queries GraphQL
AXIE_BRIEF_FRAGMENT = """
fragment AxieBrief on Axie {
  id
  name
  stage
  class
  breedCount
  image
  title
  genes
  newGenes
  battleInfo {
    banned
    __typename
  }
  order {
    id
    currentPrice
    currentPriceUsd
    basePrice
    endedPrice
    maker
    expiredAt
    __typename
  }
  parts {
    id
    name
    class
    type
    specialGenes
    __typename
  }
  stats {
    hp
    speed
    skill
    morale
    __typename
  }
  __typename
}
"""

AXIE_DETAIL_FRAGMENT = """
fragment AxieDetail on Axie {
  id
  name
  stage
  class
  breedCount
  image
  title
  genes
  newGenes
  owner
  birthDate
  bodyShape
  sireId
  matronId
  figure {
    atlas
    model
    image
    __typename
  }
  battleInfo {
    banned
    banUntil
    level
    __typename
  }
  order {
    id
    currentPrice
    currentPriceUsd
    basePrice
    endedPrice
    maker
    expiredAt
    __typename
  }
  parts {
    id
    name
    class
    type
    specialGenes
    __typename
  }
  stats {
    hp
    speed
    skill
    morale
    __typename
  }
  ownerProfile {
    name
    __typename
  }
  transferHistory {
    total
    results {
      from
      to
      txHash
      timestamp
      withPrice
      withPriceUsd
      fromProfile {
        name
        __typename
      }
      toProfile {
        name
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}
"""



class MarketplaceGraphQL:
    """Cliente GraphQL para o Marketplace do Axie Infinity.

    Responsável por consultas de leitura: buscar axies à venda,
    histórico de vendas, detalhes de um axie específico, etc.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.get("api_key")
        # Usamos o endpoint público oficial por padrão, pois não exige API Key e
        # contorna limitações de chaves de teste antigas/expiradas usando curl_cffi.
        if self.api_key and not self.api_key.startswith("k5o"):
            self.url = "https://api-gateway.skymavis.com/graphql/axie-marketplace"
            self.headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
                "X-API-KEY": self.api_key,
            }
            self.use_gateway = True
        else:
            self.url = "https://graphql-gateway.axieinfinity.com/graphql"
            self.headers = {
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Content-Type": "application/json",
                "Origin": "https://app.axieinfinity.com",
                "Referer": "https://app.axieinfinity.com/"
            }
            self.use_gateway = False

    def _execute_query(self, operation_name: str, query: str, variables: dict = None):
        """Executa uma query GraphQL e retorna o JSON de resposta."""
        payload = {
            "operationName": operation_name,
            "query": query,
            "variables": variables or {},
        }

        if self.use_gateway:
            response = requests.post(self.url, headers=self.headers, json=payload)
            if response.status_code in (401, 403):
                raise PermissionError(
                    f"Acesso negado ({response.status_code}). Verifique se a sua API Key "
                    "está correta no config.yml ou no GCP Secret Manager."
                )
        else:
            response = requests.post(self.url, headers=self.headers, json=payload, impersonate="chrome")

        # Se a requisição retornar erros em JSON (por exemplo, HTTP 400 por erro de validação GraphQL),
        # tentamos capturar a mensagem de erro do GraphQL antes de lançar a exceção de HTTP.
        try:
            data = response.json()
            if "errors" in data:
                raise Exception(f"GraphQL Error: {data['errors']}")
        except ValueError:
            # Caso o corpo não seja um JSON válido, deixamos seguir para o raise_for_status()
            data = {}

        response.raise_for_status()
        return data.get("data")

    # ─── 1. Buscar Axies à Venda ───────────────────────────────────

    def get_axies_for_sale(
        self,
        size: int = 20,
        offset: int = 0,
        sort: str = "PriceAsc",
        classes: list = None,
        parts: list = None,
        breed_count: list = None,
        min_price: str = None,
        max_price: str = None,
    ) -> dict:
        """Busca axies listados à venda no marketplace.

        Args:
            size: Quantidade de resultados (max 100).
            offset: Offset para paginação.
            sort: Ordenação (PriceAsc, PriceDesc, Latest, IdAsc, IdDesc).
            classes: Lista de classes para filtrar (ex: ["Beast", "Aquatic"]).
            parts: Lista de IDs de partes para filtrar.
            breed_count: Lista de breed counts aceitos (ex: [0, 1, 2]).
            min_price: Preço mínimo em wei (string).
            max_price: Preço máximo em wei (string).

        Returns:
            Dict com 'total' e 'results' (lista de axies).
        """
        query = (
            AXIE_BRIEF_FRAGMENT
            + """
        query GetAxieBriefList(
            $auctionType: AuctionType,
            $criteria: AxieSearchCriteria,
            $from: Int,
            $sort: SortBy,
            $size: Int
        ) {
            axies(
                auctionType: $auctionType,
                criteria: $criteria,
                from: $from,
                sort: $sort,
                size: $size
            ) {
                total
                results {
                    ...AxieBrief
                }
            }
        }
        """
        )

        criteria = {}
        if classes:
            criteria["classes"] = classes
        if parts:
            criteria["parts"] = parts
        if breed_count is not None:
            criteria["breedCount"] = breed_count
        variables = {
            "from": offset,
            "size": min(size, 100),
            "sort": sort,
            "auctionType": "Sale",
            "criteria": criteria if criteria else None,
        }

        data = self._execute_query("GetAxieBriefList", query, variables)
        result = data.get("axies", {})

        # Filtro de preço local/client-side (para evitar erros de validação no schema da API)
        if (min_price or max_price) and "results" in result:
            filtered_results = []
            for axie in result["results"]:
                order = axie.get("order") or {}
                price_wei = int(order.get("currentPrice", 0))
                if min_price and price_wei < int(min_price):
                    continue
                if max_price and price_wei > int(max_price):
                    continue
                filtered_results.append(axie)
            result["results"] = filtered_results

        return result

    # ─── 2. Buscar Detalhes e Histórico de um Axie ─────────────────

    def get_axie_detail(self, axie_id: str) -> dict:
        """Busca detalhes completos de um axie, incluindo histórico de transferências.

        Args:
            axie_id: ID do axie.

        Returns:
            Dict com todos os dados do axie.
        """
        query = (
            AXIE_DETAIL_FRAGMENT
            + """
        query GetAxieDetail($axieId: ID!) {
            axie(axieId: $axieId) {
                ...AxieDetail
            }
        }
        """
        )

        variables = {"axieId": str(axie_id)}
        data = self._execute_query("GetAxieDetail", query, variables)
        return data.get("axie", {})

    # ─── 3. Buscar Histórico de Vendas (Recently Sold) ─────────────

    def get_recently_sold(
        self,
        size: int = 20,
        offset: int = 0,
        classes: list = None,
        sort: str = "Latest",
    ) -> dict:
        """Busca axies recentemente vendidos no marketplace.

        Args:
            size: Quantidade de resultados.
            offset: Offset para paginação.
            classes: Filtrar por classes.
            sort: Ordenação.

        Returns:
            Dict com 'total' e 'results'.
        """
        query = (
            AXIE_BRIEF_FRAGMENT
            + """
        query GetAxieLatest(
            $auctionType: AuctionType,
            $criteria: AxieSearchCriteria,
            $from: Int,
            $sort: SortBy,
            $size: Int
        ) {
            axies(
                auctionType: $auctionType,
                criteria: $criteria,
                from: $from,
                sort: $sort,
                size: $size
            ) {
                total
                results {
                    ...AxieBrief
                }
            }
        }
        """
        )

        criteria = {}
        if classes:
            criteria["classes"] = classes

        variables = {
            "from": offset,
            "size": min(size, 100),
            "sort": sort,
            "auctionType": "All",
            "criteria": criteria if criteria else None,
        }

        data = self._execute_query("GetAxieLatest", query, variables)
        return data.get("axies", {})

    def get_axie_transfer_history(self, axie_id: str) -> list:
        """Busca o histórico de transferências (vendas) de um axie específico.

        Retorna a lista de transferências com preço, endereços e timestamps.
        """
        detail = self.get_axie_detail(axie_id)
        history = detail.get("transferHistory", {})
        return history.get("results", [])

    # ─── 4. Buscar Axies de um Dono ────────────────────────────────

    def get_axies_by_owner(
        self,
        owner: str,
        size: int = 100,
        offset: int = 0,
    ) -> dict:
        """Lista todos os axies de uma carteira específica.

        Args:
            owner: Endereço da carteira (formato ronin ou 0x).
            size: Quantidade de resultados.
            offset: Offset para paginação.

        Returns:
            Dict com 'total' e 'results'.
        """
        # Normaliza endereço ronin -> 0x
        if owner.startswith("ronin:"):
            owner = "0x" + owner[6:]

        query = (
            AXIE_BRIEF_FRAGMENT
            + """
        query GetAxieBriefList(
            $auctionType: AuctionType,
            $criteria: AxieSearchCriteria,
            $from: Int,
            $sort: SortBy,
            $size: Int,
            $owner: String
        ) {
            axies(
                auctionType: $auctionType,
                criteria: $criteria,
                from: $from,
                sort: $sort,
                size: $size,
                owner: $owner
            ) {
                total
                results {
                    ...AxieBrief
                }
            }
        }
        """
        )

        variables = {
            "from": offset,
            "size": min(size, 100),
            "sort": "IdDesc",
            "auctionType": "All",
            "owner": owner,
        }

        data = self._execute_query("GetAxieBriefList", query, variables)
        return data.get("axies", {})
