"""
LexFlow Protocol - API Schemas (Pydantic)
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ===== 条項状態設定 =====
class ConditionStatusEnum(str, Enum):
    PENDING = "pending"
    JUDGING = "judging"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"

# ===== コントラクト状態設定 =====
class ContractStatusEnum(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


# ============== コントラクトスキーマ設定 ==============
# ===== コントラクト作成用スキーマ設定 =====
class ContractCreate(BaseModel):
    """新しい契約を作成するためのスキーマ"""
    title: str = Field(..., min_length=1, max_length=255)
    payer_address: str = Field(..., pattern="^0x[a-fA-F0-9]{40}$")
    lawyer_address: str = Field(..., pattern="^0x[a-fA-F0-9]{40}$")
    total_amount: float = Field(..., gt=0)

# ===== コントラクトレスポンススキーマ設定 =====
class ContractResponse(BaseModel):
    """契約のレスポンススキーマ"""
    id: str
    title: str
    file_url: str
    payer_address: str
    lawyer_address: str
    total_amount: float
    released_amount: float
    status: ContractStatusEnum
    blockchain_tx_hash: Optional[str] = None
    created_at: datetime
    condition_count: int = 0
    
    class Config:
        from_attributes = True

# ===== コントラクト詳細スキーマ設定 =====
class ContractDetail(ContractResponse):
    """条件付きの契約の詳細スキーマ"""
    conditions: List["ConditionResponse"] = []
    parsed_data: Optional[dict] = None


# ============== 条項スキーマ設定 ==============
# ===== 条項作成用スキーマ設定 =====
class ConditionCreate(BaseModel):
    """条件を追加するためのスキーマ"""
    condition_type: str = Field(..., pattern="^(milestone|deadline|approval)$")
    description: str = Field(..., min_length=1)
    payment_amount: float = Field(..., gt=0)
    recipient_address: str = Field(..., pattern="^0x[a-fA-F0-9]{40}$")

# ===== 条項レスポンススキーマ設定 =====
class ConditionResponse(BaseModel):
    """条件のレスポンススキーマ"""
    id: str
    contract_id: str
    condition_type: str
    description: str
    payment_amount: float
    recipient_address: str
    status: ConditionStatusEnum
    created_at: datetime
    executed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============== 評価スキーマ設定 ==============
# ===== 評価用スキーマ設定 =====
class EvidenceSubmit(BaseModel):
    """証拠を提出するためのスキーマ"""
    evidence_text: Optional[str] = None
    evidence_url: Optional[str] = None
    evidence_type: Optional[str] = "text"  # text, url, image

# ===== 判決レスポンススキーマ設定 =====
class JudgmentResponse(BaseModel):
    """AIによる証拠評価用の判決スキーマ"""
    condition_id: str
    ai_result: str
    ai_reason: str
    ai_confidence: float
    judged_at: datetime
    
    class Config:
        from_attributes = True

# ===== 承認用スキーマ設定 =====
class ApprovalRequest(BaseModel):
    """弁護士の承認用スキーマ"""
    result: str = Field(..., pattern="^(approved|rejected)$")
    comment: Optional[str] = None


# ============== トランザクションスキーマ設定 ==============
# ===== トランザクションレスポンススキーマ設定 =====
class TransactionResponse(BaseModel):
    """トランザクションのレスポンススキーマ"""
    id: str
    condition_id: str
    tx_hash: str
    amount: float
    from_address: str
    to_address: str
    block_number: Optional[int] = None
    executed_at: datetime
    
    class Config:
        from_attributes = True


# ============== コントラクト解析スキーマ設定 ==============
# ===== 解析された文章スキーマ設定 =====
class ParsedClause(BaseModel):
    """解析された契約の文章スキーマ"""
    clause_id: str
    clause_type: str  # payment, milestone, obligation
    description: str
    amount: Optional[float] = None
    deadline: Optional[str] = None
    parties: List[str] = []

# ===== コントラクト解析レスポンススキーマ設定 =====
class ContractParseResponse(BaseModel):
    """AIによる契約解析用のレスポンススキーマ"""
    contract_id: str
    title: str
    parties: List[str]
    clauses: List[ParsedClause]
    total_value: float
    summary: str


# ===== 前方参照更新 =====
ContractDetail.model_rebuild()
