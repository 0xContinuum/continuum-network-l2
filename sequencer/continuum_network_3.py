"""
===============================================================================
CONTINUUM NETWORK (v2.1 L2 EVM Edition - Token Paymaster & Anti-Sybil Engine)
===============================================================================
"""

import hashlib
import json
import time
import secrets
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

CONTRACT_ADDRESS = "0x4a6a10bceA56815cD7450Ccb6ebB5470258Cb3BC"
SEPOLIA_RPC_URL = "https://rpc.sepolia.org"
FOUNDER_WALLET_ADDRESS = "0x7ea2688f44f696421f2F44adfa7DBFC102eC7A23"


class CryptoEngine:
    @staticmethod
    def generate_hash(data: Any) -> str:
        serialized = json.dumps(data, sort_keys=True) if isinstance(data, (dict, list)) else str(data)
        return hashlib.sha256(serialized.encode()).hexdigest()

    @staticmethod
    def generate_keypair() -> dict:
        priv_key = secrets.token_hex(32)
        pub_key = hashlib.sha256(priv_key.encode()).hexdigest()[:40]
        return {"private_key": priv_key, "public_key": "0x" + pub_key}


class L2Paymaster:
    """ERC-4337 Uyumlu Token-Paymaster ve Anti-Sybil Modülü."""
    
    MIN_BALANCE_REQUIREMENT = 100.0  # Min. 100 CTM bakiye şartı
    MAX_SPONSORED_PER_24H = 2       # 24 saatte maks. 2 sponsorlu işlem
    CTM_PER_ETH_GAS = 100_000.0     # 1 ETH Gas maliyetine karşılık gelen CTM oranı

    def __init__(self, paymaster_address: str = "0xPaymaster_L2_Vault", ctm_balance: float = 200_000_000.0):
        self.paymaster_address = paymaster_address
        self.ctm_balance = ctm_balance
        self.eth_gas_tank = 10.0  # L2 Sequencer ETH Gaz Tankı
        self.user_usage_history: Dict[str, List[float]] = {}  # Adres -> [Zaman damgaları]

    def is_eligible_for_sponsorship(self, user_address: str, user_balance: float) -> tuple[bool, str]:
        # 1. Bakiye Kontrolü
        if user_balance < self.MIN_BALANCE_REQUIREMENT:
            return False, f"Yetersiz CTM bakiyesi. En az {self.MIN_BALANCE_REQUIREMENT} CTM gerekli."

        # 2. 24 Saatlik Frekans Limiti Kontrolü
        current_time = time.time()
        user_history = self.user_usage_history.get(user_address, [])
        
        # 24 saatten eski kayıtları temizle
        valid_history = [t for t in user_history if current_time - t < 86400]
        self.user_usage_history[user_address] = valid_history

        if len(valid_history) >= self.MAX_SPONSORED_PER_24H:
            return False, f"24 saatlik sponsorlu işlem limitine ulaşıldı ({self.MAX_SPONSORED_PER_24H} işlem/gün)."

        return True, "Sponsorluk onaylandı."

    def calculate_ctm_gas_fee(self, gas_fee_eth: float) -> float:
        """ETH Cinsinden Gas Ücretini CTM Miktarına Çevirir."""
        return gas_fee_eth * self.CTM_PER_ETH_GAS

    def record_usage(self, user_address: str):
        if user_address not in self.user_usage_history:
            self.user_usage_history[user_address] = []
        self.user_usage_history[user_address].append(time.time())


@dataclass
class L2Block:
    index: int
    timestamp: float
    transactions: List[dict]
    previous_hash: str
    sequencer: str
    batch_root: str
    hash: str = ""

    def calculate_hash(self) -> str:
        block_dict = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "sequencer": self.sequencer,
            "batch_root": self.batch_root
        }
        return CryptoEngine.generate_hash(block_dict)


class ContinuumL2Blockchain:
    TOTAL_SUPPLY = 1_000_000_000.0
    FOUNDER_ALLOCATION = 150_000_000.0
    AIRDROP_ALLOCATION = 120_000_000.0
    PAYMASTER_ALLOCATION = 200_000_000.0
    STATE_FILE = "continuum_l2_state.json"

    def __init__(self, founder_address: str = FOUNDER_WALLET_ADDRESS, contract_address: str = CONTRACT_ADDRESS):
        self.founder_address = founder_address
        self.contract_address = contract_address
        self.chain: List[L2Block] = []
        self.balances: Dict[str, float] = {}
        self.paymaster = L2Paymaster()

        if not self.load_state():
            self.balances[self.founder_address] = self.FOUNDER_ALLOCATION
            self.balances["0xAirdrop_Vault_Address"] = self.AIRDROP_ALLOCATION
            self.balances[self.paymaster.paymaster_address] = self.PAYMASTER_ALLOCATION
            self.balances["0xL2_Ecosystem_Liquidity"] = self.TOTAL_SUPPLY - (
                self.FOUNDER_ALLOCATION + self.AIRDROP_ALLOCATION + self.PAYMASTER_ALLOCATION
            )
            self._create_genesis_block()
            self.save_state()

    def _create_genesis_block(self):
        genesis_tx = {
            "type": "L2_GENESIS_DEPLOYMENT",
            "contract_address": self.contract_address,
            "founder_wallet": self.founder_address,
            "founder_mint": self.FOUNDER_ALLOCATION,
            "airdrop_mint": self.AIRDROP_ALLOCATION,
            "paymaster_mint": self.PAYMASTER_ALLOCATION
        }
        genesis_block = L2Block(
            index=0,
            timestamp=time.time(),
            transactions=[genesis_tx],
            previous_hash="0" * 64,
            sequencer="0xContinuum_Sequencer_Main",
            batch_root=CryptoEngine.generate_hash(genesis_tx)
        )
        genesis_block.hash = genesis_block.calculate_hash()
        self.chain.append(genesis_block)

    def save_state(self):
        state_data = {
            "contract_address": self.contract_address,
            "founder_address": self.founder_address,
            "balances": self.balances,
            "paymaster_eth_tank": self.paymaster.eth_gas_tank,
            "paymaster_usage_history": self.paymaster.user_usage_history,
            "chain": [b.__dict__ for b in self.chain]
        }
        with open(self.STATE_FILE, "w") as f:
            json.dump(state_data, f, indent=4)

    def load_state(self) -> bool:
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.contract_address = data.get("contract_address", self.contract_address)
                    self.founder_address = data.get("founder_address", self.founder_address)
                    self.balances = data.get("balances", {})
                    self.paymaster.eth_gas_tank = data.get("paymaster_eth_tank", 10.0)
                    self.paymaster.user_usage_history = data.get("paymaster_usage_history", {})
                    self.chain = []
                    for b_dict in data.get("chain", []):
                        b = L2Block(
                            index=b_dict["index"],
                            timestamp=b_dict["timestamp"],
                            transactions=b_dict["transactions"],
                            previous_hash=b_dict["previous_hash"],
                            sequencer=b_dict["sequencer"],
                            batch_root=b_dict["batch_root"],
                            hash=b_dict["hash"]
                        )
                        self.chain.append(b)
                return True
            except Exception:
                return False
        return False

    def process_l2_batch(self, pending_txs: List[dict], sequencer_address: str) -> L2Block:
        prev_block = self.chain[-1]
        
        for tx in pending_txs:
            sender = tx.get("sender", "0xUnknown")
            gas_fee_eth = tx.get("gas_fee_eth", 0.0001)
            is_sponsored_requested = tx.get("sponsor_gas", False)
            user_balance = self.balances.get(sender, 0.0)

            if is_sponsored_requested:
                eligible, reason = self.paymaster.is_eligible_for_sponsorship(sender, user_balance)
                
                if eligible:
                    ctm_fee = self.paymaster.calculate_ctm_gas_fee(gas_fee_eth)
                    
                    # Kullanıcı bakiyesinden CTM gaz ücreti kesilir
                    self.balances[sender] -= ctm_fee
                    
                    # %50 Paymaster Havuzuna geri aktarılır, %50 Yakılır (Burn)
                    burn_amount = ctm_fee * 0.5
                    recycle_amount = ctm_fee * 0.5
                    
                    self.balances[self.paymaster.paymaster_address] += recycle_amount
                    self.TOTAL_SUPPLY -= burn_amount  # Arz kalıcı olarak düşer (Deflasyonist)
                    
                    self.paymaster.record_usage(sender)
                    
                    tx["gas_status"] = "TOKEN_PAYMASTER_SPONSORED"
                    tx["ctm_gas_deducted"] = ctm_fee
                    tx["ctm_burned"] = burn_amount
                else:
                    tx["gas_status"] = f"REJECTED: {reason}"
            else:
                tx["gas_status"] = "PAID_BY_USER_DIRECT"

        batch_root = CryptoEngine.generate_hash(pending_txs)
        new_block = L2Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=pending_txs,
            previous_hash=prev_block.hash,
            sequencer=sequencer_address,
            batch_root=batch_root
        )
        new_block.hash = new_block.calculate_hash()
        
        self.chain.append(new_block)
        self.save_state()
        return new_block