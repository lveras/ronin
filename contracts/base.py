import json
from core.wallet import Wallet

class BaseContract:
    def __init__(self, wallet: Wallet, contract_hash: str, abi_file: str):
        self.wallet = wallet
        self.contract_hash = self.wallet.w3.to_checksum_address(contract_hash)
        
        with open(f"abis/{abi_file}", 'r') as file:
            self.abi = json.load(file)
            
        self.contract = self.wallet.w3.eth.contract(
            address=self.contract_hash,
            abi=self.abi
        )
