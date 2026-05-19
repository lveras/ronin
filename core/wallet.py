from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from core.config import config
import asyncio

class Wallet:
    def __init__(self):
        self.ronin_chain_id = 2020
        self.ronin_provider_url = f"https://ronin-mainnet.core.chainstack.com/{config['chainstack']}"
        self.w3 = Web3(Web3.HTTPProvider(self.ronin_provider_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if not self.w3.is_connected():
            print("Erro: Não foi possível conectar à rede Ronin.")

        self.private_key = config["key"]
        self.address = Web3.to_checksum_address(config["address"])

    def decimal_to_wei(self, valor_decimal):
        return int(valor_decimal * 10 ** 18)

    async def check_tx_status(self, tx_hash):
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.get("status") == 1:
            print(f"Transaction {tx_hash.hex()} success!")
        else:
            print(f"Transaction {tx_hash.hex()} fail!")
        return receipt

    async def send_transaction(self, tx):
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash
