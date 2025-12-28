"""
LexFlow Protocol - Blockchain Service
Web3.py integration for Ethereum smart contract interactions
"""
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account
import json
import hashlib

from app.core.config import settings


# LexFlowEscrowコントラクトの最小インターフェース
ESCROW_ABI = [
    {
        "inputs": [
            {"name": "contractId", "type": "bytes32"},
            {"name": "lawyer", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "createContract",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "contractId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "payee", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "addCondition",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "contractId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "evidenceHash", "type": "bytes32"}
        ],
        "name": "submitEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "contractId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"}
        ],
        "name": "approveCondition",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "contractId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"}
        ],
        "name": "rejectCondition",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "contractId", "type": "bytes32"}],
        "name": "getContract",
        "outputs": [
            {
                "components": [
                    {"name": "contractId", "type": "bytes32"},
                    {"name": "payer", "type": "address"},
                    {"name": "lawyer", "type": "address"},
                    {"name": "totalAmount", "type": "uint256"},
                    {"name": "releasedAmount", "type": "uint256"},
                    {"name": "isActive", "type": "bool"},
                    {"name": "conditionCount", "type": "uint256"}
                ],
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "contractId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"}
        ],
        "name": "getCondition",
        "outputs": [
            {
                "components": [
                    {"name": "conditionId", "type": "bytes32"},
                    {"name": "payee", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "status", "type": "uint8"},
                    {"name": "evidenceHash", "type": "bytes32"},
                    {"name": "createdAt", "type": "uint256"},
                    {"name": "executedAt", "type": "uint256"}
                ],
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "contractId", "type": "bytes32"}],
        "name": "getEscrowBalance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# JPYCトークンのERC20 ABI
ERC20_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ブロックチェーンサービスクラス
class BlockchainService:

    def __init__(self):
        # Web3インスタンスを初期化する
        self.w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_RPC_URL))
        self.escrow_address = settings.ESCROW_CONTRACT_ADDRESS
        self.jpyc_address = settings.JPYC_CONTRACT_ADDRESS
        
        # PRIVATE_KEY の検証と読み込み
        if settings.PRIVATE_KEY:
            try:
                # 秘密鍵が正しい形式かチェック
                if not settings.PRIVATE_KEY.startswith("0x"):
                    raise ValueError("PRIVATE_KEY must start with '0x'")
                if len(settings.PRIVATE_KEY) != 66:  # 0x + 64 hex chars
                    raise ValueError("PRIVATE_KEY must be 66 characters (0x + 64 hex)")
                self.account = Account.from_key(settings.PRIVATE_KEY)
            except Exception as e:
                print(f"⚠️ Warning: Invalid PRIVATE_KEY in .env: {e}")
                print("⚠️ Blockchain transactions will not be available.")
                self.account = None
        else:
            self.account = None
        
        # コントラクトを初期化する
        if self.escrow_address and self.escrow_address.startswith("0x"):
            self.escrow = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.escrow_address),
                abi=ESCROW_ABI
            )
        else:
            self.escrow = None
        
        # JPYCトークンのコントラクトを初期化する
        if self.jpyc_address and self.jpyc_address.startswith("0x"):
            self.jpyc = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.jpyc_address),
                abi=ERC20_ABI
            )
        else:
            self.jpyc = None
    
    def hex_with_0x(self, hex_str: str) -> str:
        """Ensure hex string has 0x prefix"""
        if not hex_str:
            return ""
        if hex_str.startswith("0x"):
            return hex_str
        return f"0x{hex_str}"

    def string_to_bytes32(self, text: str) -> bytes:
        """文字列をbytes32に変換する"""
        if text.startswith("0x") and len(text) == 66:
            return bytes.fromhex(text[2:])
        return Web3.keccak(text=text)
    
    def is_connected(self) -> bool:
        """ブロックチェーンに接続されているかを確認する"""
        return self.w3.is_connected()
    
    def get_chain_id(self) -> int:
        """現在のチェーンIDを取得する"""
        return self.w3.eth.chain_id
    
    async def approve_jpyc_for_escrow(
        self,
        amount_jpyc: float,
    ) -> Dict[str, Any]:
        """
        EscrowコントラクトがJPYCを使用できるように承認する
        
        Args:
            amount_jpyc: 承認するJPYCの金額
            
        Returns:
            トランザクションレシート
        """
        if not self.jpyc or not self.account or not self.escrow_address:
            return {"error": "JPYC or Escrow not configured"}
        
        amount_wei = self.w3.to_wei(amount_jpyc, 'ether')
        
        # 現在の allowance を確認
        current_allowance = self.jpyc.functions.allowance(
            self.account.address,
            Web3.to_checksum_address(self.escrow_address)
        ).call()
        
        # 既に十分な allowance がある場合はスキップ
        if current_allowance >= amount_wei:
            return {
                "status": "already_approved",
                "allowance": current_allowance,
            }
        
        # approve トランザクションを構築
        tx = self.jpyc.functions.approve(
            Web3.to_checksum_address(self.escrow_address),
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price,
        })
        
        # 署名して送信
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # トランザクション完了を待機（タイムアウト付き）
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return {
                "tx_hash": self.hex_with_0x(receipt.transactionHash.hex()),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "status": "success" if receipt.status == 1 else "failed",
            }
        except Exception as e:
            return {"error": f"Approval transaction timeout or failed: {str(e)}"}
    
    async def create_escrow_contract(
        self,
        contract_id: str,
        lawyer_address: str,
        amount_jpyc: float,
    ) -> Dict[str, Any]:
        """
        新しいエスクロー契約を取得する
        
        Args:
            contract_id: 契約ID
            lawyer_address: 承認弁護士のアドレス
            amount_jpyc: JPYCの金額
            
        Returns:
            トランザクションレシート
        """
        if not self.escrow or not self.account:
            return {"error": "Blockchain not configured"}
        
        # Step 1: JPYC の使用を承認
        approval_result = await self.approve_jpyc_for_escrow(amount_jpyc)
        if "error" in approval_result:
            return approval_result
        
        contract_id_bytes = self.string_to_bytes32(contract_id)
        amount_wei = self.w3.to_wei(amount_jpyc, 'ether')
        
        # トランザクションを構築する
        tx = self.escrow.functions.createContract(
            contract_id_bytes,
            Web3.to_checksum_address(lawyer_address),
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price,
        })
        
        # 署名して送信する
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # トランザクション完了を待機（タイムアウト付き）
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return {
                "tx_hash": self.hex_with_0x(receipt.transactionHash.hex()),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "status": "success" if receipt.status == 1 else "failed",
            }
        except Exception as e:
            return {"error": f"Transaction timeout or failed: {str(e)}"}
    
    async def add_condition(
        self,
        contract_id: str,
        condition_id: str,
        payee_address: str,
        amount_jpyc: float,
    ) -> Dict[str, Any]:
        """条件をエスクロー契約に追加する"""
        if not self.escrow or not self.account:
            return {"error": "Blockchain not configured"}
        
        contract_id_bytes = self.string_to_bytes32(contract_id)
        condition_id_bytes = self.string_to_bytes32(condition_id)
        amount_wei = self.w3.to_wei(amount_jpyc, 'ether')
        
        tx = self.escrow.functions.addCondition(
            contract_id_bytes,
            condition_id_bytes,
            Web3.to_checksum_address(payee_address),
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price,
        })
        
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            "tx_hash": self.hex_with_0x(receipt.transactionHash.hex()),
            "block_number": receipt.blockNumber,
            "status": "success" if receipt.status == 1 else "failed",
        }
    
    async def submit_evidence(
        self,
        contract_id: str,
        condition_id: str,
        evidence_data: str,
    ) -> Dict[str, Any]:
        """エビデンスハッシュを条件に提出する"""
        if not self.escrow or not self.account:
            return {"error": "Blockchain not configured"}
        
        contract_id_bytes = self.string_to_bytes32(contract_id)
        condition_id_bytes = self.string_to_bytes32(condition_id)
        evidence_hash = self.string_to_bytes32(evidence_data)
        
        tx = self.escrow.functions.submitEvidence(
            contract_id_bytes,
            condition_id_bytes,
            evidence_hash
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 150000,
            'gasPrice': self.w3.eth.gas_price,
        })
        
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            "tx_hash": self.hex_with_0x(receipt.transactionHash.hex()),
            "evidence_hash": evidence_hash.hex(),
            "status": "success" if receipt.status == 1 else "failed",
        }
    
    async def approve_condition(
        self,
        contract_id: str,
        condition_id: str,
    ) -> Dict[str, Any]:
        """条件を承認して支払いをトリガーする"""
        if not self.escrow or not self.account:
            return {"error": "Blockchain not configured"}
        
        contract_id_bytes = self.string_to_bytes32(contract_id)
        condition_id_bytes = self.string_to_bytes32(condition_id)
        
        tx = self.escrow.functions.approveCondition(
            contract_id_bytes,
            condition_id_bytes
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 250000,
            'gasPrice': self.w3.eth.gas_price,
        })
        
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            "tx_hash": self.hex_with_0x(receipt.transactionHash.hex()),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "status": "success" if receipt.status == 1 else "failed",
        }
    
    async def get_contract_info(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """ブロックチェーンから契約情報を取得する"""
        if not self.escrow:
            return None
        
        contract_id_bytes = self.string_to_bytes32(contract_id)
        
        try:
            result = self.escrow.functions.getContract(contract_id_bytes).call()
            return {
                "contract_id": result[0].hex(),
                "payer": result[1],
                "lawyer": result[2],
                "total_amount": self.w3.from_wei(result[3], 'ether'),
                "released_amount": self.w3.from_wei(result[4], 'ether'),
                "is_active": result[5],
                "condition_count": result[6],
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_etherscan_url(self, tx_hash: str) -> str:
        """トランザクションのEtherscan URLを取得する"""
        chain_id = self.get_chain_id() if self.is_connected() else 11155111
        
        if chain_id == 1:
            return f"https://etherscan.io/tx/{tx_hash}"
        elif chain_id == 11155111:
            return f"https://sepolia.etherscan.io/tx/{tx_hash}"
        else:
            return f"https://etherscan.io/tx/{tx_hash}"


# インスタンス化
blockchain_service = BlockchainService()
