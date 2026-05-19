import json
import time
from web3 import Web3
from eth_account.messages import encode_typed_data as encode_structured_data
from core.wallet import Wallet
from core.config import config
from api.marketplace_graphql import MarketplaceGraphQL
import requests


# Endereço do Marketplace Gateway V2 na Ronin Mainnet
MARKETPLACE_GATEWAY = "0xfff9ce5f71ca6178d3beecedb61e7eff1602950e"

# Endereço do contrato Axie NFT (ERC-721)
AXIE_CONTRACT = "0x32950db2a7164aE833121501C797D79E7B79d74C"

# WETH na Ronin (token de pagamento padrão no marketplace)
WETH_CONTRACT = "0xc99a6A985eD2Cac1ef41640596C5A5f9F4E19Ef5"

# EIP-712 Domain para ordens do Marketplace
MARKETPLACE_DOMAIN = {
    "name": "MarketGateway",
    "version": "1",
    "chainId": 2020,
    "verifyingContract": MARKETPLACE_GATEWAY,
}

# Tipos EIP-712 para assinatura de ordens
ORDER_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "Asset": [
        {"name": "erc", "type": "uint8"},
        {"name": "addr", "type": "address"},
        {"name": "id", "type": "uint256"},
        {"name": "quantity", "type": "uint256"},
    ],
    "Order": [
        {"name": "maker", "type": "address"},
        {"name": "kind", "type": "uint8"},
        {"name": "assets", "type": "Asset[]"},
        {"name": "expiredAt", "type": "uint256"},
        {"name": "paymentToken", "type": "uint256"},
        {"name": "startedPrice", "type": "uint256"},
        {"name": "endedPrice", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
    ],
}


class ExchangeContract:
    """Contrato de troca do Marketplace do Axie Infinity.

    Responsável por:
    - Comprar axies (settleOrder via interactWith)
    - Listar axies à venda (assinatura EIP-712 + POST na API)
    - Fazer propostas (offers) em axies
    """

    def __init__(self, wallet: Wallet):
        self.wallet = wallet
        self.w3 = wallet.w3
        self.marketplace_graphql = MarketplaceGraphQL()

        # Carrega ABI do Gateway
        with open("abis/marketplace_gateway.json", "r") as f:
            gateway_abi = json.load(f)
        self.gateway_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(MARKETPLACE_GATEWAY),
            abi=gateway_abi,
        )

        # Carrega ABI do OrderExchange (para encode do settleOrder)
        with open("abis/order_exchange.json", "r") as f:
            self.order_exchange_abi = json.load(f)
        self.order_exchange_contract = self.w3.eth.contract(abi=self.order_exchange_abi)

    # ─── COMPRAR AXIE ──────────────────────────────────────────────

    def buy_axie(self, axie_id: str, price_wei: int, seller: str, order_nonce: int,
                 expired_at: int, started_price: int, ended_price: int,
                 signature: str) -> str:
        """Compra um axie chamando settleOrder via interactWith no Gateway.

        Args:
            axie_id: ID do axie a comprar.
            price_wei: Preço atual em wei.
            seller: Endereço do vendedor.
            order_nonce: Nonce da ordem.
            expired_at: Timestamp de expiração da ordem.
            started_price: Preço inicial da listagem em wei.
            ended_price: Preço final da listagem em wei.
            signature: Assinatura EIP-712 do vendedor (hex string).

        Returns:
            Hash da transação (hex string).
        """
        # Monta a estrutura da ordem
        order = (
            Web3.to_checksum_address(seller),   # maker
            1,                                   # kind: 1 = Sell
            [
                (
                    1,                           # erc: 1 = ERC721
                    Web3.to_checksum_address(AXIE_CONTRACT),
                    int(axie_id),                # token id
                    0,                           # quantity (0 para ERC721)
                )
            ],
            expired_at,
            0,                                   # paymentToken: 0 = WETH
            started_price,
            ended_price,
            order_nonce,
        )

        # Converte assinatura hex para bytes
        sig_bytes = bytes.fromhex(signature.replace("0x", ""))

        # Encoda a chamada settleOrder
        settle_data = self.order_exchange_contract.encode_abi(
            fn_name="settleOrder",
            args=[
                price_wei,     # _settlePrice
                0,             # _referralPct
                "0x0000000000000000000000000000000000000000",  # _referralAddr
                sig_bytes,     # _signature
                order,         # _order tuple
            ],
        )

        # Chama interactWith no Gateway
        tx = self.gateway_contract.functions.interactWith(
            "ORDER_EXCHANGE",
            bytes.fromhex(settle_data[2:]),  # remove 0x prefix
        ).build_transaction(
            {
                "from": self.wallet.address,
                "gas": 500000,
                "gasPrice": self.w3.to_wei("20", "gwei"),
                "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
                "value": 0,
            }
        )

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"[BUY] Transação enviada: {tx_hash.hex()}")
        return tx_hash.hex()

    # ─── LISTAR AXIE À VENDA ──────────────────────────────────────

    def _sign_order(self, order_data: dict) -> str:
        """Assina uma ordem usando EIP-712.

        Args:
            order_data: Dict com os campos da ordem (maker, kind, assets, etc).

        Returns:
            Assinatura hex.
        """
        typed_data = {
            "types": ORDER_TYPES,
            "primaryType": "Order",
            "domain": MARKETPLACE_DOMAIN,
            "message": order_data,
        }

        encoded = encode_structured_data(primitive=typed_data)
        signed = self.w3.eth.account.sign_message(encoded, self.wallet.private_key)
        return signed.signature.hex()

    def list_axie(
        self,
        axie_id: str,
        base_price_wei: int,
        ended_price_wei: int = None,
        duration_days: int = 180,
    ) -> str:
        """Lista um axie à venda no marketplace.

        Gera uma assinatura EIP-712 e envia a ordem para a API.

        Args:
            axie_id: ID do axie.
            base_price_wei: Preço inicial em wei.
            ended_price_wei: Preço final em wei (para leilão decrescente). Se None, igual ao base.
            duration_days: Duração da listagem em dias.

        Returns:
            Assinatura da ordem (hex).
        """
        if ended_price_wei is None:
            ended_price_wei = base_price_wei

        expired_at = int(time.time()) + (duration_days * 86400)
        nonce = self.w3.eth.get_transaction_count(self.wallet.address)

        order_data = {
            "maker": self.wallet.address,
            "kind": 1,  # Sell
            "assets": [
                {
                    "erc": 1,  # ERC721
                    "addr": Web3.to_checksum_address(AXIE_CONTRACT),
                    "id": int(axie_id),
                    "quantity": 0,
                }
            ],
            "expiredAt": expired_at,
            "paymentToken": 0,
            "startedPrice": base_price_wei,
            "endedPrice": ended_price_wei,
            "nonce": nonce,
        }

        signature = self._sign_order(order_data)
        print(f"[LIST] Axie #{axie_id} listado. Preço: {base_price_wei} wei. Signature: {signature[:20]}...")
        return signature

    # ─── FAZER PROPOSTA (OFFER) ───────────────────────────────────

    def make_offer(
        self,
        axie_id: str,
        offer_price_wei: int,
        duration_days: int = 7,
    ) -> str:
        """Faz uma proposta (offer) em um axie.

        Gera uma assinatura EIP-712 representando uma ordem de compra.

        Args:
            axie_id: ID do axie.
            offer_price_wei: Valor da proposta em wei.
            duration_days: Validade da proposta em dias.

        Returns:
            Assinatura da proposta (hex).
        """
        expired_at = int(time.time()) + (duration_days * 86400)
        nonce = self.w3.eth.get_transaction_count(self.wallet.address)

        order_data = {
            "maker": self.wallet.address,
            "kind": 0,  # Buy (Offer)
            "assets": [
                {
                    "erc": 1,
                    "addr": Web3.to_checksum_address(AXIE_CONTRACT),
                    "id": int(axie_id),
                    "quantity": 0,
                }
            ],
            "expiredAt": expired_at,
            "paymentToken": 0,
            "startedPrice": offer_price_wei,
            "endedPrice": offer_price_wei,
            "nonce": nonce,
        }

        signature = self._sign_order(order_data)
        print(f"[OFFER] Proposta de {offer_price_wei} wei no Axie #{axie_id}. Signature: {signature[:20]}...")
        return signature
