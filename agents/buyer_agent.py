"""Agente de compra automatizada de Axies.

Este agente busca axies à venda no marketplace com filtros configuráveis
e pode executar compras automaticamente quando encontra oportunidades.

Uso:
    uv run python -m agents.buyer_agent
"""

from core.wallet import Wallet
from core.config import config
from api.marketplace_graphql import MarketplaceGraphQL
from contracts.exchange import ExchangeContract


class BuyerAgent:
    """Agente responsável por buscar e comprar axies no marketplace."""

    def __init__(self):
        self.wallet = Wallet()
        self.api = MarketplaceGraphQL()
        self.exchange = ExchangeContract(wallet=self.wallet)

    def search_cheap_axies(
        self,
        max_price_eth: float = 0.01,
        classes: list = None,
        size: int = 10,
    ) -> list:
        """Busca axies baratos no marketplace.

        Args:
            max_price_eth: Preço máximo em ETH.
            classes: Classes desejadas (ex: ["Beast", "Aquatic"]).
            size: Quantidade de resultados.

        Returns:
            Lista de axies encontrados.
        """
        max_price_wei = str(int(max_price_eth * 10**18))

        result = self.api.get_axies_for_sale(
            size=size,
            sort="PriceAsc",
            classes=classes,
            max_price=max_price_wei,
        )

        axies = result.get("results", [])
        print(f"Encontrados {len(axies)} axies abaixo de {max_price_eth} ETH")

        for axie in axies:
            order = axie.get("order") or {}
            price_usd = order.get("currentPriceUsd", "N/A")
            print(f"  Axie #{axie['id']} | Classe: {axie.get('class')} | "
                  f"Preço: ${price_usd} | Breeds: {axie.get('breedCount')}")

        return axies

    def check_axie_history(self, axie_id: str) -> dict:
        """Analisa o histórico de um axie antes de comprar.

        Returns:
            Dict com detalhes completos do axie incluindo transferências.
        """
        detail = self.api.get_axie_detail(axie_id)

        history = detail.get("transferHistory", {}).get("results", [])
        print(f"\nAxie #{axie_id} - Histórico de {len(history)} transferência(s):")
        for transfer in history[:5]:
            price = transfer.get("withPriceUsd", "sem preço")
            print(f"  {transfer.get('timestamp')} | "
                  f"De: {transfer.get('from', '')[:10]}... | "
                  f"Para: {transfer.get('to', '')[:10]}... | "
                  f"Preço: ${price}")

        return detail

    def list_my_axies(self) -> list:
        """Lista todos os axies da carteira configurada."""
        result = self.api.get_axies_by_owner(owner=self.wallet.address)
        axies = result.get("results", [])
        print(f"\nVocê possui {result.get('total', 0)} axie(s):")

        for axie in axies:
            order = axie.get("order")
            status = "À VENDA" if order else "Guardado"
            print(f"  Axie #{axie['id']} | {axie.get('class')} | {status}")

        return axies


if __name__ == "__main__":
    agent = BuyerAgent()

    # Exemplo: buscar axies baratos
    axies = agent.search_cheap_axies(max_price_eth=0.005, size=5)

    # Exemplo: ver detalhes do primeiro resultado
    if axies:
        agent.check_axie_history(axies[0]["id"])
