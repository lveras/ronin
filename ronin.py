import os.path

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json
from datetime import datetime
from skymavis import SkyMavis
import asyncio
import yaml
from google.cloud import secretmanager


CONTRACTS = {
    "main_contract": {
        "hash": "0xa54b0184d12349cf65281c6f965a74828ddd9e8f",
        "abi_file": "main_contract.json"
    },
    "approve": {
        "hash": "0x1329661fc0531ff63fd912346e8340c000bf16f4",
        "abi_file": "approve.json"
    },
    "atia_blessing": {
        "hash": "0x9d3936dbd9a794ee31ef9f13814233d435bd806c",
        "abi_file": "atia_blessing.json"
    },
    "gacha_machine": {
        "hash": "0x3e0674b1ddc84b0cfd9d773bb2ce23fe8f445de3",
        "abi_file": "gacha_machine.json"
    },
    "axie_consumable_consumer": {
        "hash": "0xeaa3d9af9c9c218dae63922c97eeee6c3f770e15",
        "abi_file": "axie_consumable_consumer.json"
    },
    "ron_staking": {
        "hash": "0x545edb750eb8769c868429be9586f5857a768758",
        "abi_file": "ron_staking.json"
    }
}

RESTAKE_POOL = "0x9B959D27840a31988410Ee69991BCF0110D61F02"

APPROVE_SPENDER = "0xA54b0184D12349Cf65281C6F965A74828DDd9E8F"
APPROVE_AMOUNT = 115792089237316195423570985008687907853269984665640564039457584007913129639935


class Ronin:
    _contract = None
    _contract_paramns = {}
    ronin_chain_id = 2020
    _config = None
    _signature = None

    def __init__(self):
        self.ronin_provider_url = (
            f"https://ronin-mainnet.core.chainstack.com/"
            f"{self.config["chainstack"]}")

        self.w3 = Web3(Web3.HTTPProvider(self.ronin_provider_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            print("Erro: Não foi possível conectar à rede Ronin.")

        self.wallet_private_key = self.config["key"]
        self.wallet_address = Web3.to_checksum_address(self.config["address"])

    @property
    def config(self):
        if self._config:
            return self._config
        if os.path.isfile("config.yml"):
            self._config = yaml.safe_load(open("config.yml"))
        else:
            project_id = "622634013834"
            client = secretmanager.SecretManagerServiceClient()
            secret_id = "axie_keys"
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            self._config = yaml.safe_load(response.payload.data.decode("UTF-8"))
        return self._config

    @property
    def contract(self):
        if self._contract:
            return self._contract
        if self._contract_paramns:
            contract_address = Web3.to_checksum_address(
                self._contract_paramns.get("hash"))
            with open(f"abis/{self._contract_paramns.get("abi_file")}") as f:
                abi = json.loads(f.read())
            return self.w3.eth.contract(address=contract_address, abi=abi)

    @contract.setter
    def contract(self, val):
        self._contract_paramns = CONTRACTS.get(val)

    def set_contract_hash(self, hash):
        self._contract_paramns["hash"] = hash

    @staticmethod
    def decimal_to_wei(valor_decimal):
        return int(valor_decimal * 10 ** 18)

    @staticmethod
    def calcular_amount_out_min(amount_in, taxa_de_conversao):
        return int(amount_in * taxa_de_conversao)

    @staticmethod
    def get_timestamp():
        return int(datetime.now().timestamp() + 3000)

    def get_amounts(self, amount_in):
        amount_in = self.decimal_to_wei(amount_in)
        amount_out_min = self.calcular_amount_out_min(
            amount_in=amount_in, taxa_de_conversao=0.95)
        return amount_in, amount_out_min

    def format_buy_sell_transaction(self, gas, amount_in, gas_price=24, nonce=None):
        if not nonce:
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
        return {
            "from": self.wallet_address,
            "value": amount_in,
            "gas": gas,
            "maxPriorityFeePerGas": self.w3.to_wei(str(gas_price), "gwei"),
            "nonce": nonce,
            "chainId": self.ronin_chain_id
        }

    async def check_tx_status(self, tx_hash):
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.get("status") == 1:
            print(f"Transaction {tx_hash} success!")
        else:
            print(f"Transaction {tx_hash} fail!")

    async def send_transaction(self, tx):
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash

    def restake_ron(self):
        self.contract = "ron_staking"
        tx = self.contract.functions.delegateRewards(
            [RESTAKE_POOL],
            RESTAKE_POOL
        ).build_transaction(
            {
                "gas": 2000000,
                "gasPrice": self.w3.to_wei("20", "gwei"),
                "nonce": self.w3.eth.get_transaction_count(self.wallet_address),
            }
        )
        tx_hash = asyncio.run(self.send_transaction(tx=tx))
        asyncio.run(self.check_tx_status(tx_hash=tx_hash))

    def _generate_signature_locky_pounch(self, expiry):
        recipient = self.wallet_address
        chests = [(0, 10)]
        chests_bytes = [(chest[0].to_bytes(32, 'big'), chest[1].to_bytes(32, 'big')) for chest in chests]
        slip_owner_nonce = 60
        slip_owner = self.wallet_address
        slip_amount = 10

        message = self.w3.solidity_keccak(
            ["bytes"],
            [
                self.w3.solidity_keccak(
                    ["bytes"],
                    [
                        self.w3.solidity_keccak(
                            ["bytes"],
                            [b"Chest[]"] + [
                                self.w3.solidity_keccak(
                                    ["bytes"],
                                    [chest[0], chest[1]],
                                )
                                for chest in chests_bytes
                            ],
                        ),
                    ]
                    + [
                        self.w3.solidity_keccak(["address"], [recipient]),
                        self.w3.solidity_keccak(["address"], [slip_owner]),
                        slip_owner_nonce.to_bytes(32, "big"),
                        expiry.to_bytes(32, "big"),
                        slip_amount.to_bytes(32, "big"),
                    ],
                ),
            ],
        )

        account = self.w3.eth.account.from_key(self.wallet_private_key)
        signature = account.sign_hash(message)
        signature_hex = signature.signature.hex()

        return (
            recipient,
            chests,
            slip_owner,
            slip_owner_nonce,
            expiry,
            slip_amount,
            signature_hex,
        )

    def open_lucky_pounch(self):
        self.contract = "gacha_machine"
        expiry = self.get_timestamp()
        (
            recipient,
            chests,
            slip_owner,
            slip_owner_nonce,
            expiry,
            slip_amount,
            signature_hex,
        ) = self._generate_signature_locky_pounch(expiry=expiry)

        tx = self.contract.functions.roll(
            chests, recipient, slip_owner, slip_owner_nonce, expiry, slip_amount, signature_hex
        ).build_transaction(
            {
                "from": self.wallet_address,
                "gas": 2000000,
                "gasPrice": self.w3.to_wei("20", "gwei"),
                "nonce": self.w3.eth.get_transaction_count(self.wallet_address),
            }
        )

        tx_hash = asyncio.run(self.send_transaction(tx=tx))
        asyncio.run(self.check_tx_status(tx_hash=tx_hash))

    def use_lucky_pounch(self, axie_id: int):
        self.contract = "axie_consumable_consumer"
        tx = self.contract.functions.consume(axie_id, 1, 1).build_transaction(
            {
                "from": self.wallet_address,
                "gas": 2000000,
                "gasPrice": self.w3.to_wei("20", "gwei"),
                "nonce": self.w3.eth.get_transaction_count(self.wallet_address),
            }
        )
        tx_hash = asyncio.run(self.send_transaction(tx=tx))
        asyncio.run(self.check_tx_status(tx_hash=tx_hash))

    def atia_blessing(self):
        self.contract = "atia_blessing"
        tx = self.contract.functions.activateStreak(
            self.wallet_address).build_transaction(
            {
                "gas": 2000000,
                "gasPrice": self.w3.to_wei("20", "gwei"),
                "nonce": self.w3.eth.get_transaction_count(self.wallet_address)
            }
        )
        tx_hash = asyncio.run(self.send_transaction(tx=tx))
        asyncio.run(self.check_tx_status(tx_hash=tx_hash))

    async def buy_tokens(self, token, amount_in, gas, gas_price, nonce=None, *args, **kwargs):
        self.contract = "main_contract"
        amount_in, amount_out_min = self.get_amounts(amount_in)
        token = Web3.to_checksum_address(token)
        tx = self.contract.functions.buyTokensWithETH(
            token, amount_in, amount_out_min, self.wallet_address, self.get_timestamp(), b""
        ).build_transaction(
            self.format_buy_sell_transaction(
                gas=gas, amount_in=amount_in,
                gas_price=gas_price, nonce=nonce
            ))
        tx_hash = await self.send_transaction(tx=tx)
        print(f"Transaction {tx_hash.hex()} to buy has sent.")
        return tx_hash

    async def sell_tokens(self, token, amount_in, gas, gas_price, nonce=None, *args, **kwargs):
        self.contract = "main_contract"
        amount_in, amount_out_min = self.get_amounts(amount_in)
        token = Web3.to_checksum_address(token)
        tx = self.contract.functions.sellTokensForETH(
            token, amount_in, 0, self.wallet_address, self.get_timestamp(), b""
        ).build_transaction(
            self.format_buy_sell_transaction(
                gas=gas, amount_in=0,
                gas_price=gas_price, nonce=nonce
            ))
        tx_hash = await self.send_transaction(tx=tx)
        print(f"Transaction {tx_hash.hex()} to sell has sent.")
        return tx_hash

    async def approve(self, token: str, nonce=None):
        if not nonce:
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
        if SkyMavis.check_approve_request(token=token, address=self.wallet_address):
            print("Transaction Approval is not necessary")
            return
        self.contract = "approve"
        self.set_contract_hash(token)
        tx = self.contract.functions.approve(
            APPROVE_SPENDER, APPROVE_AMOUNT
        ).build_transaction({"nonce": nonce})
        return await self.send_transaction(tx=tx)

    async def check_rajada_status(self, tx_hashs: list):
        tasks = [self.check_tx_status(tx_hash=tx_hash) for tx_hash in tx_hashs]
        await asyncio.gather(*tasks)

    async def _rajada(self, method, tiros, token, amount_in, gas, gas_price):
        tasks = []
        nonce = self.w3.eth.get_transaction_count(self.wallet_address)

        for i in range(0, tiros):
            tasks.append(
                asyncio.create_task(getattr(self, f"{method}_tokens")(
                    token=token, amount_in=amount_in, gas=gas,
                    gas_price=gas_price, number=i,
                    nonce=nonce+i)))

        tx_hashs = await asyncio.gather(*tasks)
        await self.approve(token=token, nonce=nonce + i + 1)
        await self.check_rajada_status([tx.hex() for tx in tx_hashs])

    def rajada(self, method, tiros, token, amount_in, gas, gas_price):
        asyncio.run(self._rajada(method, tiros, token, amount_in, gas, gas_price))


if __name__ == '__main__':
    ronin = Ronin()
    # ronin.rajada(
    #     method="buy",
    #     tiros=1,
    #     token="0x94d2f9ff5d5717cceb65bcfc80111f09a6d81c26",
    #     amount_in=0.001,
    #     gas=2000000,
    #     gas_price=20
    # )

    ronin.atia_blessing()
