"""
LexFlow Protocol - ZK Proof Verifier Service

ゼロ知識証明の検証を行うサービス。
snarkjsで生成された証明をPythonで検証します。

"""
import json
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ZKVerifier:
    """ゼロ知識証明検証サービス"""
    
    def __init__(self, circuits_path: str = None):
        """
        Initialize the ZK Verifier
        
        Args:
            circuits_path: コンパイルされた回路のディレクトリ
        """
        if circuits_path:
            self.circuits_path = Path(circuits_path)
        else:
            # プロジェクトの contracts/zk/build ディレクトリをデフォルトにする
            self.circuits_path = Path(__file__).parent.parent.parent.parent / "contracts" / "zk" / "build"
    
    async def verify_kyc_proof(
        self,
        proof: Dict[str, Any],
        public_signals: list
    ) -> tuple[bool, Optional[str]]:
        """
        KYC ZK証明を検証
        
        Args:
            proof: Groth16証明オブジェクト
            public_signals: 証明から公開信号
            
        Returns:
            (is_valid, error_message)
        """
        return await self._verify_proof(
            proof=proof,
            public_signals=public_signals,
            circuit_name="kyc",
            vkey_file="kyc_verification_verification_key.json"
        )
    
    async def verify_coi_proof(
        self,
        proof: Dict[str, Any],
        public_signals: list
    ) -> tuple[bool, Optional[str]]:
        """
        利益相反のZK証明を検証
        
        Args:
            proof: Groth16証明オブジェクト
            public_signals: 証明から公開信号
            
        Returns:
            (is_valid, error_message)
        """
        return await self._verify_proof(
            proof=proof,
            public_signals=public_signals,
            circuit_name="coi",
            vkey_file="conflict_of_interest_verification_key.json"
        )
    
    async def verify_fulfillment_proof(
        self,
        proof: Dict[str, Any],
        public_signals: list
    ) -> tuple[bool, Optional[str]]:
        """
        履行状態のZK証明を検証
        
        Args:
            proof: Groth16証明オブジェクト
            public_signals: 証明から公開信号
            
        Returns:
            (is_valid, error_message)
        """
        return await self._verify_proof(
            proof=proof,
            public_signals=public_signals,
            circuit_name="fulfillment",
            vkey_file="fulfillment_status_verification_key.json"
        )
    
    async def _verify_proof(
        self,
        proof: Dict[str, Any],
        public_signals: list,
        circuit_name: str,
        vkey_file: str
    ) -> tuple[bool, Optional[str]]:
        """
        内部メソッド。snarkjs CLIを使用して任意のZK証明を検証
        
        Groth16証明の純粋なPython検証は複雑な楕円曲線操作を必要とするため、
        CLIアプローチを使用します。
        """
        vkey_path = self.circuits_path / circuit_name / vkey_file
        
        if not vkey_path.exists():
            return False, f"検証鍵が見つかりません: {vkey_path}"
        
        try:
            # 証明と公開信号の一時ファイルを作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as proof_file:
                json.dump(proof, proof_file)
                proof_path = proof_file.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as signals_file:
                json.dump(public_signals, signals_file)
                signals_path = signals_file.name
            
            # snarkjsのパスを取得（contracts/zk/node_modules/.bin/snarkjs）
            snarkjs_path = self.circuits_path.parent / "node_modules" / ".bin" / "snarkjs"
            
            # snarkjs verifyコマンドを実行
            # npxを使わずに直接実行することでオーバーヘッドを削減
            cmd = [
                str(snarkjs_path), 'groth16', 'verify',
                str(vkey_path),
                signals_path,
                proof_path
            ]
            
            # もしバイナリが見つからない場合はフォールバックとしてnpxを使う
            if not snarkjs_path.exists():
                cmd = ['npx', 'snarkjs', 'groth16', 'verify', str(vkey_path), signals_path, proof_path]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # 一時ファイルを削除
            os.unlink(proof_path)
            os.unlink(signals_path)
            
            if result.returncode == 0 and "OK" in result.stdout:
                return True, None
            else:
                return False, result.stderr or "検証失敗"
                
        except subprocess.TimeoutExpired:
            return False, "検証タイムアウト"
        except Exception as e:
            return False, f"検証エラー: {str(e)}"
    
    def get_circuit_status(self) -> Dict[str, bool]:
        """
        コンパイルされた回路を確認
        
        Returns:
            コンパイルされた回路の状態を辞書で返す
        """
        circuits = {
            "kyc": "kyc/kyc_verification_verification_key.json",
            "coi": "coi/conflict_of_interest_verification_key.json",
            "fulfillment": "fulfillment/fulfillment_status_verification_key.json"
        }
        
        status = {}
        for name, path in circuits.items():
            full_path = self.circuits_path / path
            status[name] = full_path.exists()
        
        return status


# シングルトンインスタンス
zk_verifier = ZKVerifier()
