"""
LexFlow Protocol - Approval Flows API (V3)
承認フローテンプレート、承認リクエスト、承認タスク、マジックリンクのエンドポイント
"""
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.models.models import (
    ApprovalFlow, ApprovalRequest, ApprovalTask, MagicLink,
    ApprovalRequestStatus, ApprovalTaskStatus, ACLSubjectType,
    Contract, Workspace
)


router = APIRouter(prefix="/approvals", tags=["承認管理 (Approvals)"])


# ===== リクエスト/レスポンススキーマ =====

class ApprovalStage(BaseModel):
    """承認ステージ定義"""
    stage: int
    type: str = Field(..., pattern="^(sequential|parallel)$")  # 順序/並列
    assignees: List[dict]  # [{"type": "user/role/external", "id": "...", "order": 1}]
    condition: Optional[dict] = None  # 条件分岐ルール


class ApprovalFlowCreate(BaseModel):
    """承認フロー作成リクエスト"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    stages: List[ApprovalStage]


class ApprovalFlowResponse(BaseModel):
    """承認フローレスポンス"""
    id: str
    workspace_id: str
    name: str
    description: Optional[str]
    stages: List[dict]
    is_active: bool
    created_at: datetime


class ApprovalRequestCreate(BaseModel):
    """承認リクエスト作成"""
    contract_id: str
    flow_id: Optional[str] = None  # テンプレート使用時
    due_at: Optional[datetime] = None
    reminder_days_before: List[int] = [3, 1, 0]  # 期限の何日前にリマインド
    message: Optional[str] = None
    # テンプレート未使用時の直接指定
    stages: Optional[List[ApprovalStage]] = None


class ApprovalRequestResponse(BaseModel):
    """承認リクエストレスポンス"""
    id: str
    contract_id: str
    flow_id: Optional[str]
    due_at: Optional[datetime]
    status: str
    message: Optional[str]
    created_by: str
    created_at: datetime
    tasks: List[dict] = []


class ApprovalTaskAction(BaseModel):
    """承認/否認/差戻しアクション"""
    comment: Optional[str] = None
    signature: Optional[str] = None  # EIP-712署名（必要時）


class MagicLinkResponse(BaseModel):
    """マジックリンクレスポンス"""
    id: str
    task_id: str
    token: str  # 実際のトークン（発行時のみ）
    expires_at: datetime
    url: str


# ===== 承認フローテンプレートエンドポイント =====

@router.get("/flows", response_model=List[ApprovalFlowResponse])
async def list_approval_flows(workspace_id: str, db: Session = Depends(get_db)):
    """ワークスペースの承認フローテンプレート一覧を取得"""
    flows = db.query(ApprovalFlow).filter(
        ApprovalFlow.workspace_id == workspace_id,
        ApprovalFlow.is_active == True
    ).all()
    
    return [
        ApprovalFlowResponse(
            id=f.id,
            workspace_id=f.workspace_id,
            name=f.name,
            description=f.description,
            stages=json.loads(f.definition_json) if f.definition_json else [],
            is_active=f.is_active,
            created_at=f.created_at
        )
        for f in flows
    ]


@router.post("/flows", response_model=ApprovalFlowResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_flow(workspace_id: str, request: ApprovalFlowCreate, db: Session = Depends(get_db)):
    """承認フローテンプレートを作成"""
    # ワークスペース存在確認
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="ワークスペースが見つかりません")
    
    flow_id = str(uuid.uuid4())
    flow = ApprovalFlow(
        id=flow_id,
        workspace_id=workspace_id,
        name=request.name,
        description=request.description,
        definition_json=json.dumps([s.dict() for s in request.stages]),
        is_active=True
    )
    db.add(flow)
    db.commit()
    db.refresh(flow)
    
    return ApprovalFlowResponse(
        id=flow.id,
        workspace_id=flow.workspace_id,
        name=flow.name,
        description=flow.description,
        stages=json.loads(flow.definition_json),
        is_active=flow.is_active,
        created_at=flow.created_at
    )


@router.delete("/flows/{flow_id}")
async def delete_approval_flow(flow_id: str, db: Session = Depends(get_db)):
    """承認フローテンプレートを無効化（論理削除）"""
    flow = db.query(ApprovalFlow).filter(ApprovalFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="承認フローが見つかりません")
    
    flow.is_active = False
    db.commit()
    
    return {"message": "承認フローを無効化しました"}


# ===== 承認リクエストエンドポイント =====

@router.post("/requests", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    request: ApprovalRequestCreate,
    created_by: str,  # 実際はJWTから取得
    db: Session = Depends(get_db)
):
    """
    承認リクエストを作成
    
    - テンプレート使用時: flow_idを指定
    - 直接指定時: stagesを指定
    """
    # 契約書存在確認
    contract = db.query(Contract).filter(Contract.id == request.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="契約書が見つかりません")
    
    # ステージ定義を取得
    stages = []
    if request.flow_id:
        flow = db.query(ApprovalFlow).filter(ApprovalFlow.id == request.flow_id).first()
        if not flow:
            raise HTTPException(status_code=404, detail="承認フローが見つかりません")
        stages = json.loads(flow.definition_json)
    elif request.stages:
        stages = [s.dict() for s in request.stages]
    else:
        raise HTTPException(status_code=400, detail="flow_id または stages を指定してください")
    
    # 承認リクエスト作成
    request_id = str(uuid.uuid4())
    reminder_policy = json.dumps({"days_before": request.reminder_days_before})
    
    approval_request = ApprovalRequest(
        id=request_id,
        contract_id=request.contract_id,
        flow_id=request.flow_id,
        due_at=request.due_at,
        reminder_policy=reminder_policy,
        status=ApprovalRequestStatus.PENDING,
        message=request.message,
        created_by=created_by
    )
    db.add(approval_request)
    db.flush()
    
    # 承認タスクを生成
    tasks = []
    for stage_def in stages:
        stage_num = stage_def.get("stage", 1)
        for assignee in stage_def.get("assignees", []):
            task_id = str(uuid.uuid4())
            task = ApprovalTask(
                id=task_id,
                request_id=request_id,
                stage=stage_num,
                order=assignee.get("order", 1),
                assignee_type=ACLSubjectType(assignee.get("type", "user")),
                assignee_id=assignee.get("id"),
                status=ApprovalTaskStatus.PENDING
            )
            db.add(task)
            tasks.append({
                "id": task_id,
                "stage": stage_num,
                "assignee_type": assignee.get("type"),
                "assignee_id": assignee.get("id"),
                "status": "pending"
            })
    
    db.commit()
    db.refresh(approval_request)
    
    return ApprovalRequestResponse(
        id=approval_request.id,
        contract_id=approval_request.contract_id,
        flow_id=approval_request.flow_id,
        due_at=approval_request.due_at,
        status=approval_request.status.value,
        message=approval_request.message,
        created_by=approval_request.created_by,
        created_at=approval_request.created_at,
        tasks=tasks
    )


@router.get("/requests/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(request_id: str, db: Session = Depends(get_db)):
    """承認リクエストの詳細を取得"""
    approval_request = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
    if not approval_request:
        raise HTTPException(status_code=404, detail="承認リクエストが見つかりません")
    
    tasks = [
        {
            "id": t.id,
            "stage": t.stage,
            "order": t.order,
            "assignee_type": t.assignee_type.value,
            "assignee_id": t.assignee_id,
            "status": t.status.value,
            "acted_at": t.acted_at.isoformat() if t.acted_at else None,
            "comment": t.comment
        }
        for t in approval_request.tasks
    ]
    
    return ApprovalRequestResponse(
        id=approval_request.id,
        contract_id=approval_request.contract_id,
        flow_id=approval_request.flow_id,
        due_at=approval_request.due_at,
        status=approval_request.status.value,
        message=approval_request.message,
        created_by=approval_request.created_by,
        created_at=approval_request.created_at,
        tasks=tasks
    )


# ===== 承認タスクアクションエンドポイント =====

@router.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str, action: ApprovalTaskAction, db: Session = Depends(get_db)):
    """承認を実行"""
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="承認タスクが見つかりません")
    
    if task.status != ApprovalTaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="このタスクは既に処理済みです")
    
    task.status = ApprovalTaskStatus.APPROVED
    task.acted_at = datetime.utcnow()
    task.comment = action.comment
    task.signature_hash = action.signature
    
    # 次のステージへの進行チェック
    _check_and_progress_request(task.request_id, db)
    
    db.commit()
    
    return {"message": "承認しました", "task_id": task_id}


@router.post("/tasks/{task_id}/reject")
async def reject_task(task_id: str, action: ApprovalTaskAction, db: Session = Depends(get_db)):
    """否認を実行"""
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="承認タスクが見つかりません")
    
    if task.status != ApprovalTaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="このタスクは既に処理済みです")
    
    if not action.comment:
        raise HTTPException(status_code=400, detail="否認理由を入力してください")
    
    task.status = ApprovalTaskStatus.REJECTED
    task.acted_at = datetime.utcnow()
    task.comment = action.comment
    task.signature_hash = action.signature
    
    # リクエスト全体を否認
    approval_request = db.query(ApprovalRequest).filter(ApprovalRequest.id == task.request_id).first()
    if approval_request:
        approval_request.status = ApprovalRequestStatus.REJECTED
    
    db.commit()
    
    return {"message": "否認しました", "task_id": task_id}


@router.post("/tasks/{task_id}/return")
async def return_task(task_id: str, action: ApprovalTaskAction, db: Session = Depends(get_db)):
    """差戻しを実行"""
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="承認タスクが見つかりません")
    
    if task.status != ApprovalTaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="このタスクは既に処理済みです")
    
    if not action.comment:
        raise HTTPException(status_code=400, detail="差戻し理由を入力してください")
    
    task.status = ApprovalTaskStatus.RETURNED
    task.acted_at = datetime.utcnow()
    task.comment = action.comment
    
    # リクエスト全体を差戻し
    approval_request = db.query(ApprovalRequest).filter(ApprovalRequest.id == task.request_id).first()
    if approval_request:
        approval_request.status = ApprovalRequestStatus.RETURNED
    
    db.commit()
    
    return {"message": "差戻ししました", "task_id": task_id}


def _check_and_progress_request(request_id: str, db: Session):
    """
    承認リクエストの進行状況をチェックし、必要に応じてステータスを更新
    """
    approval_request = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
    if not approval_request:
        return
    
    tasks = approval_request.tasks
    
    # 全タスクが承認済みか確認
    all_approved = all(t.status == ApprovalTaskStatus.APPROVED for t in tasks)
    if all_approved:
        approval_request.status = ApprovalRequestStatus.APPROVED
        return
    
    # 否認または差戻しがあるか確認
    has_rejected = any(t.status == ApprovalTaskStatus.REJECTED for t in tasks)
    has_returned = any(t.status == ApprovalTaskStatus.RETURNED for t in tasks)
    
    if has_rejected:
        approval_request.status = ApprovalRequestStatus.REJECTED
    elif has_returned:
        approval_request.status = ApprovalRequestStatus.RETURNED


# ===== マジックリンクエンドポイント =====

@router.post("/tasks/{task_id}/magic-link", response_model=MagicLinkResponse)
async def create_magic_link(
    task_id: str,
    expires_hours: int = 72,
    db: Session = Depends(get_db)
):
    """
    承認タスク用のマジックリンクを発行
    
    - 外部承認者向け
    - ワンタイムトークン（期限付き）
    """
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="承認タスクが見つかりません")
    
    # 既存の有効なリンクを失効
    existing_links = db.query(MagicLink).filter(
        MagicLink.task_id == task_id,
        MagicLink.revoked_at == None,
        MagicLink.consumed_at == None
    ).all()
    for link in existing_links:
        link.revoked_at = datetime.utcnow()
    
    # 新しいトークン生成
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
    
    magic_link = MagicLink(
        id=str(uuid.uuid4()),
        task_id=task_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(magic_link)
    db.commit()
    db.refresh(magic_link)
    
    # URLを構築（本番環境では設定から読み込む）
    base_url = "https://lexflow.example.com"
    url = f"{base_url}/approve/{raw_token}"
    
    return MagicLinkResponse(
        id=magic_link.id,
        task_id=task_id,
        token=raw_token,  # 発行時のみ返す
        expires_at=magic_link.expires_at,
        url=url
    )


@router.post("/magic-link/{token}/consume")
async def consume_magic_link(token: str, db: Session = Depends(get_db)):
    """
    マジックリンクを使用（検証）
    
    - トークンを検証
    - 有効なら承認タスク情報を返す
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    magic_link = db.query(MagicLink).filter(MagicLink.token_hash == token_hash).first()
    if not magic_link:
        raise HTTPException(status_code=404, detail="無効なリンクです")
    
    if magic_link.revoked_at:
        raise HTTPException(status_code=400, detail="このリンクは無効化されています")
    
    if magic_link.consumed_at:
        raise HTTPException(status_code=400, detail="このリンクは既に使用されています")
    
    if datetime.utcnow() > magic_link.expires_at:
        raise HTTPException(status_code=400, detail="このリンクは期限切れです")
    
    # 使用済みにマーク
    magic_link.consumed_at = datetime.utcnow()
    db.commit()
    
    # タスク情報を取得
    task = db.query(ApprovalTask).filter(ApprovalTask.id == magic_link.task_id).first()
    
    return {
        "valid": True,
        "task_id": task.id if task else None,
        "request_id": task.request_id if task else None,
        "message": "リンクが検証されました。承認アクションを実行できます。"
    }


@router.delete("/magic-link/{link_id}")
async def revoke_magic_link(link_id: str, db: Session = Depends(get_db)):
    """マジックリンクを失効"""
    magic_link = db.query(MagicLink).filter(MagicLink.id == link_id).first()
    if not magic_link:
        raise HTTPException(status_code=404, detail="リンクが見つかりません")
    
    magic_link.revoked_at = datetime.utcnow()
    db.commit()
    
    return {"message": "リンクを失効しました"}
