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
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=True) # V3: 所属ワークスペース
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
    parties = Column(Text, nullable=True)  # JSON文字列の当事者リスト
    summary = Column(Text, nullable=True)  # 契約書の要約
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    workspace = relationship("Workspace", back_populates="contracts")
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


# ===========================
# V3: RBAC & ワークスペース関連モデル
# ===========================

# ===== V3: ユーザーステータス =====
class UserStatus(str, enum.Enum):
    """ユーザーの状態を定義するEnum"""
    PENDING = "pending"        # 招待済み、未確認
    ACTIVE = "active"          # 有効
    SUSPENDED = "suspended"    # 停止中
    DELETED = "deleted"        # 削除済み

# ===== V3: ワークスペースユーザーステータス =====
class WorkspaceUserStatus(str, enum.Enum):
    """ワークスペースメンバーの状態を定義するEnum"""
    INVITED = "invited"        # 招待済み
    ACTIVE = "active"          # 有効
    REMOVED = "removed"        # 削除済み

# ===== V3: ワークスペースモデル =====
class Workspace(Base):
    """
    ワークスペース（テナント）モデル（V3機能）
    企業/チーム単位のテナントを表現
    """
    __tablename__ = "workspaces"
    
    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    roles = relationship("Role", back_populates="workspace", cascade="all, delete-orphan")
    members = relationship("WorkspaceUser", back_populates="workspace", cascade="all, delete-orphan")
    approval_flows = relationship("ApprovalFlow", back_populates="workspace", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="workspace", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="workspace") # V3: 契約一覧

# ===== V3: ユーザーモデル =====
class User(Base):
    """
    ユーザーモデル（V3機能）
    メールアドレスとパスワードで認証
    """
    __tablename__ = "users"
    
    id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    slack_webhook_url = Column(String(255), nullable=True) # V3: 通知用Webhook
    status = Column(Enum(UserStatus), default=UserStatus.PENDING)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
    workspace_memberships = relationship("WorkspaceUser", back_populates="user", cascade="all, delete-orphan")

# ===== V3: ウォレットモデル =====
class Wallet(Base):
    """
    ウォレット（EVM互換アドレス）モデル（V3機能）
    ユーザーと紐付けて所有権を確認
    """
    __tablename__ = "wallets"
    
    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    address = Column(String(42), unique=True, nullable=False, index=True)  # 0x...
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    user = relationship("User", back_populates="wallets")

# ===== V3: ロールモデル =====
class Role(Base):
    """
    役割モデル（V3機能）
    ワークスペース内での権限グループを定義
    """
    __tablename__ = "roles"
    
    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(100), nullable=False)  # Owner, Admin, Manager, Member, Approver, Auditor
    is_custom = Column(Boolean, default=False)  # カスタムロールか否か
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    workspace = relationship("Workspace", back_populates="roles")
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    members = relationship("WorkspaceUser", back_populates="role")

# ===== V3: 権限モデル =====
class Permission(Base):
    """
    権限モデル（V3機能）
    システム全体で定義される権限キー
    """
    __tablename__ = "permissions"
    
    id = Column(String(64), primary_key=True)
    key = Column(String(100), unique=True, nullable=False)  # 例: workspace:invite, contract:edit
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # ワークスペース管理、契約書管理、承認管理、通知管理
    
    # リレーションシップ
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

# ===== V3: ロール権限（中間テーブル） =====
class RolePermission(Base):
    """
    ロールと権限の多対多リレーションシップ（V3機能）
    """
    __tablename__ = "role_permissions"
    
    id = Column(String(64), primary_key=True)
    role_id = Column(String(64), ForeignKey("roles.id"), nullable=False)
    permission_id = Column(String(64), ForeignKey("permissions.id"), nullable=False)
    
    # リレーションシップ
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="role_permissions")

# ===== V3: ワークスペースユーザー =====
class WorkspaceUser(Base):
    """
    ワークスペースとユーザーの所属関係（V3機能）
    """
    __tablename__ = "workspace_users"
    
    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    role_id = Column(String(64), ForeignKey("roles.id"), nullable=False)
    status = Column(Enum(WorkspaceUserStatus), default=WorkspaceUserStatus.INVITED)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")
    role = relationship("Role", back_populates="members")


# ===========================
# V3: 契約書単位ACL
# ===========================

# ===== V3: ACL対象タイプ =====
class ACLSubjectType(str, enum.Enum):
    """ACLの対象タイプを定義するEnum"""
    USER = "user"
    ROLE = "role"
    EXTERNAL = "external"  # 外部承認者（メール or ウォレット）

# ===== V3: 契約書ACLモデル =====
class ContractACL(Base):
    """
    契約書単位のアクセス制御リスト（V3機能）
    ユーザー/ロール/外部承認者ごとに権限を設定
    """
    __tablename__ = "contract_acl"
    
    id = Column(String(64), primary_key=True)
    contract_id = Column(String(64), ForeignKey("contracts.id"), nullable=False)
    subject_type = Column(Enum(ACLSubjectType), nullable=False)
    subject_id = Column(String(255), nullable=False)  # user_id, role_id, or email/wallet
    permissions = Column(Text, nullable=False)  # JSON配列: ["view", "edit", "approve"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(64), nullable=True)  # 作成者のuser_id


# ===========================
# V3: 承認フロー関連モデル
# ===========================

# ===== V3: 承認リクエストステータス =====
class ApprovalRequestStatus(str, enum.Enum):
    """承認リクエストの状態を定義するEnum"""
    PENDING = "pending"      # 承認待ち
    APPROVED = "approved"    # 承認済み
    REJECTED = "rejected"    # 否認
    RETURNED = "returned"    # 差戻し
    EXPIRED = "expired"      # 期限切れ
    CANCELLED = "cancelled"  # キャンセル

# ===== V3: 承認タスクステータス =====
class ApprovalTaskStatus(str, enum.Enum):
    """承認タスクの状態を定義するEnum"""
    PENDING = "pending"      # 待機中
    APPROVED = "approved"    # 承認
    REJECTED = "rejected"    # 否認
    RETURNED = "returned"    # 差戻し
    SKIPPED = "skipped"      # スキップ（条件分岐）

# ===== V3: 承認フローテンプレート =====
class ApprovalFlow(Base):
    """
    承認フローテンプレートモデル（V3機能）
    承認者・順序・条件分岐を定義
    """
    __tablename__ = "approval_flows"
    
    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    definition_json = Column(Text, nullable=False)  # ステージ、条件、承認者のJSON定義
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    workspace = relationship("Workspace", back_populates="approval_flows")
    requests = relationship("ApprovalRequest", back_populates="flow")

# ===== V3: 承認リクエスト（実行インスタンス） =====
class ApprovalRequest(Base):
    """
    承認リクエストモデル（V3機能）
    特定の契約書に対する承認依頼の実行インスタンス
    """
    __tablename__ = "approval_requests"
    
    id = Column(String(64), primary_key=True)
    contract_id = Column(String(64), ForeignKey("contracts.id"), nullable=False)
    flow_id = Column(String(64), ForeignKey("approval_flows.id"), nullable=True)  # テンプレ使用時
    
    # 期限とリマインダー
    due_at = Column(DateTime(timezone=True), nullable=True)
    reminder_policy = Column(Text, nullable=True)  # JSON: {"days_before": [3, 1, 0], "daily": false}
    
    # ステータス
    status = Column(Enum(ApprovalRequestStatus), default=ApprovalRequestStatus.PENDING)
    message = Column(Text, nullable=True)  # 依頼者からのメッセージ
    
    # 作成情報
    created_by = Column(String(64), nullable=False)  # 依頼者のuser_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーションシップ
    flow = relationship("ApprovalFlow", back_populates="requests")
    tasks = relationship("ApprovalTask", back_populates="request", cascade="all, delete-orphan")
    contract = relationship("Contract") # 契約書へのショートカット

# ===== V3: 承認タスク =====
class ApprovalTask(Base):
    """
    承認タスクモデル（V3機能）
    各承認者への個別の承認依頼
    """
    __tablename__ = "approval_tasks"
    
    id = Column(String(64), primary_key=True)
    request_id = Column(String(64), ForeignKey("approval_requests.id"), nullable=False)
    
    # ステージと順序
    stage = Column(Integer, nullable=False, default=1)  # 承認ステージ番号
    order = Column(Integer, nullable=False, default=1)  # ステージ内の順序
    
    # 承認者
    assignee_type = Column(Enum(ACLSubjectType), nullable=False)  # user, role, external
    assignee_id = Column(String(255), nullable=False)  # user_id, role_id, or email/wallet
    
    # ステータス
    status = Column(Enum(ApprovalTaskStatus), default=ApprovalTaskStatus.PENDING)
    acted_at = Column(DateTime(timezone=True), nullable=True)
    comment = Column(Text, nullable=True)  # 承認/否認のコメント
    signature_hash = Column(String(132), nullable=True)  # EIP-712署名（必要時）
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    request = relationship("ApprovalRequest", back_populates="tasks")
    magic_links = relationship("MagicLink", back_populates="task", cascade="all, delete-orphan")

# ===== V3: マジックリンク =====
class MagicLink(Base):
    """
    ワンタイム承認リンクモデル（V3機能）
    外部承認者向けのセキュアなリンク
    """
    __tablename__ = "magic_links"
    
    id = Column(String(64), primary_key=True)
    task_id = Column(String(64), ForeignKey("approval_tasks.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)  # SHA-256ハッシュ
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    task = relationship("ApprovalTask", back_populates="magic_links")


# ===========================
# V3: 通知関連モデル
# ===========================

# ===== V3: 通知チャンネル =====
class NotificationChannel(str, enum.Enum):
    """通知チャンネルを定義するEnum"""
    EMAIL = "email"
    SLACK = "slack"

# ===== V3: 通知ステータス =====
class NotificationStatus(str, enum.Enum):
    """通知の状態を定義するEnum"""
    PENDING = "pending"      # 送信待ち
    SENT = "sent"            # 送信済み
    FAILED = "failed"        # 送信失敗
    RETRYING = "retrying"    # リトライ中

# ===== V3: 通知モデル =====
class Notification(Base):
    """
    通知モデル（V3機能）
    Email/Slackへの通知ログを記録
    """
    __tablename__ = "notifications"
    
    id = Column(String(64), primary_key=True)
    channel = Column(Enum(NotificationChannel), nullable=False)
    recipient = Column(String(255), nullable=False)  # メールアドレス or Slackチャンネル
    subject = Column(String(255), nullable=True)  # メール件名
    payload = Column(Text, nullable=False)  # 通知内容（JSON）
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ===========================
# V3: 監査証跡関連モデル
# ===========================

# ===== V3: 監査イベントタイプ =====
class AuditEventType(str, enum.Enum):
    """監査イベントのタイプを定義するEnum"""
    # 認証
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_WALLET_LINKED = "auth.wallet_linked"
    AUTH_WALLET_UNLINKED = "auth.wallet_unlinked"
    
    # 権限
    RBAC_ROLE_CREATED = "rbac.role_created"
    RBAC_ROLE_UPDATED = "rbac.role_updated"
    RBAC_ROLE_DELETED = "rbac.role_deleted"
    RBAC_USER_INVITED = "rbac.user_invited"
    RBAC_USER_ROLE_CHANGED = "rbac.user_role_changed"
    RBAC_ACL_GRANTED = "rbac.acl_granted"
    RBAC_ACL_REVOKED = "rbac.acl_revoked"
    
    # 契約書
    CONTRACT_CREATED = "contract.created"
    CONTRACT_UPLOADED = "contract.uploaded"
    CONTRACT_METADATA_UPDATED = "contract.metadata_updated"
    CONTRACT_DELETED = "contract.deleted"
    CONTRACT_ARCHIVED = "contract.archived"
    
    # 承認
    APPROVAL_REQUEST_CREATED = "approval.request_created"
    APPROVAL_LINK_ISSUED = "approval.link_issued"
    APPROVAL_LINK_REVOKED = "approval.link_revoked"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_REJECTED = "approval.rejected"
    APPROVAL_RETURNED = "approval.returned"
    
    # 通知
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"

# ===== V3: 監査イベントモデル =====
class AuditEvent(Base):
    """
    監査イベントモデル（V3機能）
    すべての重要な操作を記録し、ハッシュチェーンで改ざん耐性を担保
    """
    __tablename__ = "audit_events"
    
    id = Column(String(64), primary_key=True)
    type = Column(Enum(AuditEventType), nullable=False)
    
    # アクター情報
    actor_id = Column(String(64), nullable=True)  # user_id (システム操作の場合はnull)
    actor_wallet = Column(String(42), nullable=True)  # ウォレットアドレス
    actor_ip = Column(String(45), nullable=True)  # IPアドレス
    actor_user_agent = Column(Text, nullable=True)  # User-Agent
    
    # 対象リソース
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), nullable=True)
    contract_id = Column(String(64), nullable=True)  # ForeignKey省略（削除済み契約の参照用）
    resource_id = Column(String(64), nullable=True)  # 対象リソースID
    resource_type = Column(String(50), nullable=True)  # 対象リソースタイプ
    
    # 詳細
    detail_json = Column(Text, nullable=True)  # 操作の詳細（差分、承認結果など）
    
    # ハッシュチェーン（改ざん耐性）
    prev_hash = Column(String(64), nullable=True)  # 前のイベントのハッシュ
    hash = Column(String(64), nullable=False)  # 本イベントのハッシュ
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    workspace = relationship("Workspace", back_populates="audit_events")

