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
    file_url = Column(Text, nullable=False)
    file_hash = Column(String(66), nullable=True)  # IPFS または ファイルハッシュ
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
    obligations = relationship("Obligation", back_populates="contract", cascade="all, delete-orphan")  # V2: F2用

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

# ===== V2: 義務タイプ（F2用） =====
class ObligationType(str, enum.Enum):
    """義務のタイプを定義するEnum"""
    PAYMENT = "payment"              # 支払義務
    RENEWAL = "renewal"              # 更新義務
    TERMINATION = "termination"      # 解除義務
    INSPECTION = "inspection"        # 検収義務
    DELIVERY = "delivery"            # 納品義務
    REPORT = "report"                # 報告義務
    CONFIDENTIALITY = "confidentiality"  # 秘密保持義務
    OTHER = "other"                  # その他

# ===== V2: 責任者タイプ（F2用） =====
class PartyType(str, enum.Enum):
    """義務の責任者を定義するEnum"""
    CLIENT = "client"                # 依頼者
    LAWYER = "lawyer"                # 弁護士
    COUNTERPARTY = "counterparty"    # 相手方
    BOTH = "both"                    # 双方
    UNKNOWN = "unknown"              # 不明

# ===== V2: リスクレベル（F2用） =====
class RiskLevel(str, enum.Enum):
    """リスクレベルを定義するEnum"""
    HIGH = "high"      # 高
    MEDIUM = "medium"  # 中
    LOW = "low"        # 低

# ===== V2: 義務ステータス（F2用） =====
class ObligationStatus(str, enum.Enum):
    """義務の状態を定義するEnum"""
    PENDING = "pending"          # 保留中
    DUE_SOON = "due_soon"        # 期限間近（7日前）
    COMPLETED = "completed"      # 完了
    OVERDUE = "overdue"          # 期限超過
    DISPUTED = "disputed"        # 係争中

# ===== V2: 義務モデル（F2用） =====
class Obligation(Base):
    """
    契約上の義務を管理するモデル（Version 2: F2機能）
    期限・条件・アクションを含む実務タスク単位を表現
    """
    __tablename__ = "obligations"
    
    # 基本情報
    id = Column(String(64), primary_key=True)
    contract_id = Column(String(64), ForeignKey("contracts.id"), nullable=False)
    title = Column(String(255), nullable=False)  # 例: "更新通知期限"
    
    # 義務の詳細
    type = Column(Enum(ObligationType), nullable=False)  # 義務タイプ
    due_date = Column(DateTime(timezone=True), nullable=True)  # 期限日（相対期限の場合はnull）
    trigger_condition = Column(Text, nullable=True)  # トリガー条件（例: "契約開始日から30日"）
    responsible_party = Column(Enum(PartyType), nullable=False)  # 責任者
    action = Column(Text, nullable=False)  # 実行すべきアクション（例: "通知する", "支払う"）
    evidence_required = Column(Text, nullable=True)  # 必要な証跡（JSON配列の文字列）
    
    # リスクと確度
    risk_level = Column(Enum(RiskLevel), nullable=False)  # リスクレベル
    confidence = Column(Float, nullable=True)  # AI抽出の確度（0.0-1.0）
    clause_reference = Column(Text, nullable=True)  # 根拠条項（条番号・該当抜粋）
    
    # ステータスと完了情報
    status = Column(Enum(ObligationStatus), default=ObligationStatus.PENDING)
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 完了日時
    completed_by = Column(String(42), nullable=True)  # 完了者のウォレットアドレス
    
    # 備考
    notes = Column(Text, nullable=True)  # 弁護士による編集メモ
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    contract = relationship("Contract", back_populates="obligations")
    edit_history = relationship("ObligationEditHistory", back_populates="obligation", cascade="all, delete-orphan")

# ===== V2: 義務編集履歴モデル（F2用） =====
class ObligationEditHistory(Base):
    """
    義務の編集履歴を記録するモデル（Version 2: F2機能）
    いつ誰が何を変更したかを監査用に記録
    """
    __tablename__ = "obligation_edit_history"
    
    id = Column(String(64), primary_key=True)
    obligation_id = Column(String(64), ForeignKey("obligations.id"), nullable=False)
    edited_by = Column(String(42), nullable=False)  # 編集者のウォレットアドレス
    field_name = Column(String(100), nullable=False)  # 変更したフィールド名
    old_value = Column(Text, nullable=True)  # 変更前の値
    new_value = Column(Text, nullable=True)  # 変更後の値
    edited_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    obligation = relationship("Obligation", back_populates="edit_history")


# ===== F8: 課金ログ =====
class PaymentLog(Base):
    """x402課金トランザクションログ"""
    __tablename__ = "payment_logs"
    
    tx_hash = Column(String(66), primary_key=True) # 0x...
    endpoint = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    token = Column(String(10), nullable=False)
    payer = Column(String(42), nullable=False) # 0x...
    created_at = Column(DateTime(timezone=True), server_default=func.now())
class VersionStatus(str, enum.Enum):
    """契約版の状態を定義するEnum"""
    DRAFT = "draft"                      # 下書き
    PENDING_SIGNATURE = "pending_signature"  # 署名待ち
    SIGNED = "signed"                    # 署名済み
    SUPERSEDED = "superseded"            # 無効化（新版により）

# ===== V2: 契約版モデル（F3用） =====
class ContractVersion(Base):
    """
    契約の版管理モデル（Version 2: F3機能）
    同一案件の異なる版を管理し、各版のハッシュを保持
    """
    __tablename__ = "contract_versions"
    
    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), nullable=False)  # 案件ID（複数版を束ねる）
    version = Column(Integer, nullable=False)  # 版番号（1, 2, 3...）
    doc_hash = Column(String(66), nullable=False)  # SHA-256ハッシュ
    file_url = Column(Text, nullable=False)  # ファイルのURL
    title = Column(String(255), nullable=True)  # 契約タイトル
    summary = Column(Text, nullable=True)  # AI生成の要約
    key_risks = Column(Text, nullable=True)  # 主要リスク（JSON配列の文字列）
    status = Column(Enum(VersionStatus), default=VersionStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(42), nullable=True)  # 作成者のウォレットアドレス
    
    # リレーションシップ
    signatures = relationship("Signature", back_populates="contract_version", cascade="all, delete-orphan")

# ===== V2: 署名モデル（F3用） =====
class Signature(Base):
    """
    EIP-712署名を記録するモデル（Version 2: F3機能）
    誰がいつどの版に署名したかを記録
    """
    __tablename__ = "signatures"
    
    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), nullable=False)  # 案件ID
    version = Column(Integer, nullable=False)  # 版番号
    doc_hash = Column(String(66), nullable=False)  # 署名対象のdocHash
    signer = Column(String(42), nullable=False)  # 署名者のウォレットアドレス
    role = Column(String(50), nullable=False)  # 署名者の役割（client/lawyer/counterparty）
    
    # EIP-712署名データ
    signature_r = Column(String(66), nullable=True)  # r値
    signature_s = Column(String(66), nullable=True)  # s値
    signature_v = Column(Integer, nullable=True)  # v値
    timestamp = Column(Integer, nullable=True)  # Unix timestamp
    
    # ブロックチェーン記録
    tx_hash = Column(String(66), nullable=True)  # トランザクションハッシュ
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    version_id = Column(String(64), ForeignKey("contract_versions.id"), nullable=True)
    contract_version = relationship("ContractVersion", back_populates="signatures")
