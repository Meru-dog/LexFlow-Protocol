"""
LexFlow Protocol - Signature Service
EIP-712 Signature Verification and Hashing
"""
from typing import Dict, Any, Optional, Tuple
from eth_account import Account
from eth_account.messages import encode_typed_data
import hashlib
import time
from web3 import Web3

from app.core.config import settings

class SignatureService:
    """
    EIP-712署名の生成（ハッシュ）と検証を行うサービス
    """
    
    def get_signing_domain(self, chain_id: int = 11155111) -> Dict[str, Any]:
        """
        EIP-712ドメイン定義を取得
        デフォルトは Sepolia (11155111)
        """
        # settingsから取得する際も int にキャストして安全性を高める
        final_chain_id = int(chain_id)
        
        # verifyingContractが空の場合は0アドレスを使用
        contract_addr = settings.ESCROW_CONTRACT_ADDRESS
        if not contract_addr or contract_addr == "":
            contract_addr = "0x0000000000000000000000000000000000000000"
            
        return {
            "name": "LexFlow Protocol",
            "version": "1",
            "chainId": final_chain_id,
            "verifyingContract": Web3.to_checksum_address(contract_addr)
        }

    def get_version_types(self) -> Dict[str, Any]:
        """
        EIP-712のデータ型定義 (ContractVersion型)
        """
        return {
            "ContractVersion": [
                {"name": "caseId", "type": "string"},
                {"name": "version", "type": "uint256"},
                {"name": "docHash", "type": "bytes32"},
                {"name": "timestamp", "type": "uint256"}
            ]
        }

    def calculate_doc_hash(self, file_content: bytes) -> str:
        """
        ファイルのSHA-256ハッシュを計算する (0xプレフィックス付き)
        """
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        return f"0x{sha256_hash}"

    def verify_eip712_signature(
        self,
        signer_address: str,
        signature: str,
        case_id: str,
        version_num: int,
        doc_hash: str,
        timestamp: int,
        chain_id: int = 11155111
    ) -> Tuple[bool, str, Optional[str]]:
        """
        EIP-712署名を検証する
        
        Returns:
            (is_valid, error_msg, recovered_address)
        """
        try:
            # 入力の正規化
            clean_case_id = str(case_id).strip()
            clean_doc_hash = str(doc_hash).strip()
            expected_signer = Web3.to_checksum_address(signer_address.strip())
            
            # docHashのバイト化
            bytes_doc_hash = clean_doc_hash
            if clean_doc_hash.startswith("0x"):
                try:
                    bytes_doc_hash = bytes.fromhex(clean_doc_hash[2:])
                except ValueError:
                    # If conversion fails, keep it as string for now, will be handled by string trial
                    pass

            try:
                import importlib.metadata
                eth_account_version = importlib.metadata.version("eth-account")
                print(f"DEBUG: eth-account version: {eth_account_version}")
            except Exception:
                print("DEBUG: Could not determine eth-account version")
            
            # 署名データの構築
            domain = self.get_signing_domain(int(chain_id))
            types = self.get_version_types()
            
            def build_structured_data(d_hash_val):
                return {
                    "types": {
                        "EIP712Domain": [
                            {"name": "name", "type": "string"},
                            {"name": "version", "type": "string"},
                            {"name": "chainId", "type": "uint256"},
                            {"name": "verifyingContract", "type": "address"},
                        ],
                        **types
                    },
                    "domain": domain,
                    "primaryType": "ContractVersion",
                    "message": {
                        "caseId": clean_case_id,
                        "version": int(version_num),
                        "docHash": d_hash_val,
                        "timestamp": int(timestamp)
                    }
                }

            import json
            # 試行1: Bytes docHash
            try:
                sd1 = build_structured_data(bytes_doc_hash)
                encoded1 = encode_typed_data(full_message=sd1)
                recovered1 = Account.recover_message(encoded1, signature=signature)
                if Web3.to_checksum_address(recovered1) == expected_signer:
                    return True, "", recovered1
            except Exception as e:
                recovered1 = f"Error: {str(e)}"

            # 試行2: String docHash
            try:
                sd2 = build_structured_data(clean_doc_hash)
                encoded2 = encode_typed_data(full_message=sd2)
                recovered2 = Account.recover_message(encoded2, signature=signature)
                if Web3.to_checksum_address(recovered2) == expected_signer:
                    return True, "", recovered2
            except Exception as e:
                recovered2 = f"Error: {str(e)}"

            # いずれも失敗した場合は詳細を返す
            error_detail = (
                f"Recovered address mismatch. Expected: {expected_signer}, "
                f"Recovered(bytes): {recovered1}, Recovered(hex): {recovered2}. "
            )
            print(f"❌ {error_detail}")
            return False, error_detail, recovered1
            
        except Exception as e:
            error_msg = f"Signature verification logic error: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg, None

    def split_signature(self, signature_hex: str) -> Tuple[str, str, int]:
        """
        65バイトの署名を r, s, v に分割する
        """
        if signature_hex.startswith('0x'):
            signature_hex = signature_hex[2:]
            
        if len(signature_hex) != 130:
            raise ValueError("Invalid signature length")
            
        r = "0x" + signature_hex[:64]
        s = "0x" + signature_hex[64:128]
        # vは最後の1バイト (通常 27 または 28)
        v = int(signature_hex[128:], 16)
        
        # Metamask等は00/01で返すことがあるため調整が必要な場合がある
        if v < 27:
            v += 27
            
        return r, s, v

# インスタンス化
signature_service = SignatureService()
