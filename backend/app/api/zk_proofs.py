"""
LexFlow Protocol - ZK Proofs API (Optional Module)

使用方法:
1. zk-proofs/ ディレクトリで回路をコンパイル
2. main.py に以下を追加:
   from app.api import zk_proofs
   app.include_router(zk_proofs.router, prefix="/api/v1")
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field


# Router (未登録 - 将来の統合用)
router = APIRouter(prefix="/zk", tags=["zk-proofs"])


# ===== Pydantic Schemas =====

class ZKProof(BaseModel):
    """Groth16証明構造"""
    pi_a: List[str] = Field(..., description="証明要素A")
    pi_b: List[List[str]] = Field(..., description="証明要素B")
    pi_c: List[str] = Field(..., description="証明要素C")
    protocol: str = Field(default="groth16")
    curve: str = Field(default="bn128")


class VerifyKYCRequest(BaseModel):
    """KYC検証リクエスト"""
    proof: ZKProof
    public_signals: List[str]
    # Public inputs
    expected_provider_hash: str = Field(..., description="KYCプロバイダーのハッシュ")
    current_timestamp: int = Field(..., description="現在のタイムスタンプ")
    validity_period: int = Field(..., description="有効期間（秒）")
    expected_identity_hash: str = Field(..., description="ユーザーIDハッシュ")


class VerifyCOIRequest(BaseModel):
    """利益相反検証リクエスト"""
    proof: ZKProof
    public_signals: List[str]
    # Public inputs
    new_client_hash: str = Field(..., description="新規クライアントのハッシュ")
    expected_client_list_commitment: str = Field(..., description="既存クライアントリストのコミットメント")
    expected_firm_hash: str = Field(..., description="法律事務所のハッシュ")


class VerifyFulfillmentRequest(BaseModel):
    """履行状態検証リクエスト"""
    proof: ZKProof
    public_signals: List[str]
    # Public inputs
    expected_obligation_hash: str = Field(..., description="義務のハッシュ")
    expected_evidence_type: str = Field(..., description="必要な証拠タイプ")
    expected_fulfiller_hash: str = Field(..., description="履行者のハッシュ")
    deadline_timestamp: int = Field(..., description="期限タイムスタンプ")
    contract_id: str = Field(..., description="契約ID")


class VerificationResponse(BaseModel):
    """検証結果"""
    valid: bool
    message: Optional[str] = None


class CircuitStatusResponse(BaseModel):
    """回路の利用可能状態"""
    kyc: bool
    coi: bool
    fulfillment: bool


# ===== API Endpoints =====

@router.get("/status", response_model=CircuitStatusResponse)
async def get_circuit_status():
    """
    ZK回路の利用可能状態を確認
    
    回路がコンパイル済みかどうかを返します。
    """
    from app.services.zk_verifier import zk_verifier
    status = zk_verifier.get_circuit_status()
    return CircuitStatusResponse(**status)


@router.post("/verify/kyc", response_model=VerificationResponse)
async def verify_kyc(request: VerifyKYCRequest):
    """
    KYC証明を検証
    
    ユーザーがKYCを通過していることを、身元情報を開示せずに検証します。
    """
    from app.services.zk_verifier import zk_verifier
    
    is_valid, error = await zk_verifier.verify_kyc_proof(
        proof=request.proof.dict(),
        public_signals=request.public_signals
    )
    
    if error:
        return VerificationResponse(valid=False, message=error)
    
    return VerificationResponse(valid=is_valid, message="KYC verified" if is_valid else "Invalid proof")


@router.post("/verify/coi", response_model=VerificationResponse)
async def verify_conflict_of_interest(request: VerifyCOIRequest):
    """
    利益相反チェック証明を検証
    
    新規クライアントとの利益相反がないことを、既存クライアントリストを
    開示せずに検証します。
    """
    from app.services.zk_verifier import zk_verifier
    
    is_valid, error = await zk_verifier.verify_coi_proof(
        proof=request.proof.dict(),
        public_signals=request.public_signals
    )
    
    if error:
        return VerificationResponse(valid=False, message=error)
    
    return VerificationResponse(valid=is_valid, message="No conflict" if is_valid else "Conflict detected or invalid proof")


@router.post("/verify/fulfillment", response_model=VerificationResponse)
async def verify_fulfillment(request: VerifyFulfillmentRequest):
    """
    履行状態証明を検証
    
    義務が適切に履行されたことを、証拠の詳細を開示せずに検証します。
    """
    from app.services.zk_verifier import zk_verifier
    
    is_valid, error = await zk_verifier.verify_fulfillment_proof(
        proof=request.proof.dict(),
        public_signals=request.public_signals
    )
    
    if error:
        return VerificationResponse(valid=False, message=error)
    
    return VerificationResponse(valid=is_valid, message="Fulfilled" if is_valid else "Not fulfilled or invalid proof")
