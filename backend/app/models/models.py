"""
LexFlow Protocol - Database Models
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ===== 条項状態設定 =====
class ConditionStatus(str, enum.Enum):
    PENDING = "pending"
    JUDGING = "judging"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"

# ===== コントラクト状態設定 =====
class ContractStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"

# ===== コントラクトモデル設定 =====
class Contract(Base):
    """ コントラクトモデル設定"""
    __tablename__ = "contracts"
    
    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    pdf_url = Column(Text, nullable=False)
    pdf_hash = Column(String(66), nullable=True)  # IPFS または ファイルハッシュ
    payer_address = Column(String(42), nullable=False)
    lawyer_address = Column(String(42), nullable=False)
    total_amount = Column(Float, nullable=False, default=0)
    released_amount = Column(Float, nullable=False, default=0)
    status = Column(Enum(ContractStatus), default=ContractStatus.PENDING)
    parsed_data = Column(Text, nullable=True)  # JSON文字列の解析された契約データ
    blockchain_tx_hash = Column(String(66), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    conditions = relationship("Condition", back_populates="contract", cascade="all, delete-orphan")

# ===== 条項モデル設定 =====
class Condition(Base):
    """ 条項モデル設定"""
    __tablename__ = "conditions"
    
    id = Column(String(64), primary_key=True)
    contract_id = Column(String(64), ForeignKey("contracts.id"), nullable=False)
    condition_type = Column(String(50), nullable=False)  # マイルストーン、期限、承認
    description = Column(Text, nullable=False)
    payment_amount = Column(Float, nullable=False)
    recipient_address = Column(String(42), nullable=False)
    status = Column(Enum(ConditionStatus), default=ConditionStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)
    
    contract = relationship("Contract", back_populates="conditions")
    judgment = relationship("Judgment", back_populates="condition", uselist=False)
    transaction = relationship("Transaction", back_populates="condition", uselist=False)

# ===== 判決モデル設定 =====
class Judgment(Base):
    """AIによる証拠評価用の判決モデル"""
    __tablename__ = "judgments"
    
    id = Column(String(64), primary_key=True)
    condition_id = Column(String(64), ForeignKey("conditions.id"), nullable=False)
    evidence_url = Column(Text, nullable=True)
    evidence_hash = Column(String(66), nullable=True)
    ai_result = Column(String(20), nullable=True)  # 承認, 拒否
    ai_reason = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    final_result = Column(String(20), nullable=True)
    approved_by = Column(String(42), nullable=True)  # 弁護士のウォレットアドレス
    comment = Column(Text, nullable=True)
    judged_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    condition = relationship("Condition", back_populates="judgment")

# ===== トランザクションモデル設定 =====
class Transaction(Base):
    """トランザクションモデル設定"""
    __tablename__ = "transactions"
    
    id = Column(String(64), primary_key=True)
    condition_id = Column(String(64), ForeignKey("conditions.id"), nullable=False)
    tx_hash = Column(String(66), nullable=False)
    amount = Column(Float, nullable=False)
    from_address = Column(String(42), nullable=False)
    to_address = Column(String(42), nullable=False)
    block_number = Column(Integer, nullable=True)
    gas_used = Column(Integer, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    condition = relationship("Condition", back_populates="transaction")
