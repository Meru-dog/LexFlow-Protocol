"""
LexFlow Protocol - Approval Flows API (V3)
承認フローテンプレート、承認リクエスト、承認タスク、マジックリンクのエンドポイント
"""
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import json

from app.core.database import get_db
from app.api.auth import get_current_user_id
from app.models.models import (
    ApprovalFlow, ApprovalRequest, ApprovalTask, MagicLink,
    ApprovalRequestStatus, ApprovalTaskStatus, ACLSubjectType,
    Contract, Workspace, User, AuditEventType
)
from app.services.notification_service import notification_service
from app.services.audit_service import audit_service



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
    is_active: bool = True  # デフォルトはTrue


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
    flow_id: Optional[str] = None
    due_at: Optional[datetime] = None
    status: str
    message: Optional[str] = None
    created_by: str
    created_at: datetime
    tasks: List[dict] = []


class ApprovalTaskResponse(BaseModel):
    """承認タスクレスポンス"""
    id: str
    request_id: str
    stage: int
    order: int
    assignee_type: str
    assignee_id: str
    status: str
    acted_at: Optional[datetime] = None
    comment: Optional[str] = None
    contract_title: Optional[str] = None
    created_at: datetime


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
async def list_approval_flows(workspace_id: str, db: AsyncSession = Depends(get_db)):
    """ワークスペースの承認フローテンプレート一覧を取得"""
    result = await db.execute(select(ApprovalFlow).where(
        ApprovalFlow.workspace_id == workspace_id,
        ApprovalFlow.is_active == True
    ))
    flows = result.scalars().all()
    
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
async def create_approval_flow(workspace_id: str, request: ApprovalFlowCreate, db: AsyncSession = Depends(get_db)):
    """承認フローテンプレートを作成"""
    # ワークスペース存在確認
    result_ws = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result_ws.scalar_one_or_none()
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
    await db.commit()
    await db.refresh(flow)
    
    return ApprovalFlowResponse(
        id=flow.id,
        workspace_id=flow.workspace_id,
        name=flow.name,
        description=flow.description,
        stages=json.loads(flow.definition_json),
        is_active=flow.is_active,
        created_at=flow.created_at
    )


@router.put("/flows/{flow_id}", response_model=ApprovalFlowResponse)
async def update_approval_flow(
    flow_id: str,
    request: ApprovalFlowCreate,
    db: AsyncSession = Depends(get_db)
):
    """承認フローテンプレートを更新"""
    result = await db.execute(select(ApprovalFlow).where(ApprovalFlow.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="承認フローが見つかりません")
    
    # 更新
    flow.name = request.name
    flow.description = request.description
    flow.is_active = request.is_active
    
    if request.stages:
        try:
            # Convert Pydantic models or dicts to JSON
            stages_data = []
            for s in request.stages:
                if isinstance(s, dict):
                    stages_data.append(s)
                elif hasattr(s, 'model_dump'):
                    stages_data.append(s.model_dump())
                elif hasattr(s, 'dict'):
                    stages_data.append(s.dict())
                else:
                    stages_data.append(s)
            flow.definition_json = json.dumps(stages_data)
        except Exception as e:
            import traceback
            print(f"Error processing stages: {e}")
            print(f"Stages type: {type(request.stages)}")
            print(f"Stages content: {request.stages}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to process stages: {str(e)}")
    
    await db.commit()
    await db.refresh(flow)
    
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
async def delete_approval_flow(flow_id: str, db: AsyncSession = Depends(get_db)):
    """承認フローテンプレートを無効化（論理削除）"""
    result = await db.execute(select(ApprovalFlow).where(ApprovalFlow.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="承認フローが見つかりません")
    
    flow.is_active = False
    await db.commit()
    
    return {"message": "承認フローを無効化しました"}


# ===== 承認リクエストエンドポイント =====

@router.post("/requests", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    request: ApprovalRequestCreate,
    db: AsyncSession = Depends(get_db),
    created_by: str = Depends(get_current_user_id)
):
    """
    承認リクエストを作成
    
    - テンプレート使用時: flow_idを指定
    - 直接指定時: stagesを指定
    """
    # 契約書存在確認
    result_contract = await db.execute(select(Contract).where(Contract.id == request.contract_id))
    contract = result_contract.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="契約書が見つかりません")
    
    # ステージ定義を取得
    stages = []
    if request.flow_id:
        result_flow = await db.execute(select(ApprovalFlow).where(ApprovalFlow.id == request.flow_id))
        flow = result_flow.scalar_one_or_none()
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
    await db.flush()
    
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
    
    # 監査ログ
    await audit_service.log_event(
        db, AuditEventType.APPROVAL_REQUEST_CREATED,
        actor_id=created_by,
        contract_id=request.contract_id,
        resource_id=request_id,
        resource_type="approval_request",
        detail={"message": request.message, "due_at": request.due_at.isoformat() if request.due_at else None}
    )
    
    await db.commit()
    await db.refresh(approval_request)
    
    # 承認者への通知送信（非同期、失敗しても処理は継続）
    try:
        # 最初のステージ（stage=1）の承認者に通知
        stage_1_tasks = [t for t in tasks if t["stage"] == 1]
        for task_info in stage_1_tasks:
            if task_info["assignee_type"] == "user":
                # ユーザーを取得
                result_user = await db.execute(
                    select(User).where(User.id == task_info["assignee_id"])
                )
                user = result_user.scalar_one_or_none()
                if user:
                    # 通知ペイロード作成
                    from app.core.config import settings
                    approval_url = f"{settings.FRONTEND_URL}/approvals"
                    
                    payload = notification_service.create_approval_request_payload(
                        contract_title=contract.title or f"契約ID: {contract.id}",
                        requester_name=created_by[:8],  # 簡略化
                        due_at=approval_request.due_at,
                        approval_url=approval_url,
                        message=approval_request.message
                    )
                    
                    # ユーザーに通知（Email/Slack）
                    await notification_service.notify_user(
                        db=db,
                        user=user,
                        subject=f"承認依頼: {contract.title or '契約書'}",
                        payload=payload
                    )
    except Exception as e:
        # 通知失敗はログのみ、リクエスト作成は成功扱い
        print(f"[NOTIFICATION ERROR] 承認依頼通知の送信に失敗しました: {str(e)}")
    
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


@router.get("/requests", response_model=List[ApprovalRequestResponse])
async def list_approval_requests(
    workspace_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """承認リクエスト一覧を取得"""
    query = select(ApprovalRequest).options(selectinload(ApprovalRequest.tasks))
    
    if workspace_id:
        query = query.join(Contract).where(Contract.workspace_id == workspace_id)
    if contract_id:
        query = query.where(ApprovalRequest.contract_id == contract_id)
        
    result = await db.execute(query)
    requests = result.scalars().all()
    
    return [
        ApprovalRequestResponse(
            id=r.id,
            contract_id=r.contract_id,
            flow_id=r.flow_id,
            due_at=r.due_at,
            status=r.status.value,
            message=r.message,
            created_by=r.created_by,
            created_at=r.created_at,
            tasks=[{
                "id": t.id,
                "stage": t.stage,
                "status": t.status.value,
                "comment": t.comment
            } for t in r.tasks]
        )
        for r in requests
    ]


@router.get("/requests/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(request_id: str, db: AsyncSession = Depends(get_db)):
    """承認リクエストの詳細を取得"""
    result = await db.execute(
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.tasks))
        .where(ApprovalRequest.id == request_id)
    )
    approval_request = result.scalar_one_or_none()
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
async def approve_task(task_id: str, action: ApprovalTaskAction, db: AsyncSession = Depends(get_db)):
    """承認を実行"""
    result = await db.execute(select(ApprovalTask).where(ApprovalTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="承認タスクが見つかりません")
    
    if task.status != ApprovalTaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="このタスクは既に処理済みです")
    
    task.status = ApprovalTaskStatus.APPROVED
    task.acted_at = datetime.utcnow()
    task.comment = action.comment
    task.signature_hash = action.signature
    
    # 次のステージへの進行チェック
    await _check_and_progress_request(task.request_id, db)
    
    # 依頼者に通知
    await _notify_requester_of_task_action(task, "APPROVED", db)
    
    await db.commit()
    
    # 監査ログ
    await audit_service.log_event(
        db, AuditEventType.APPROVAL_APPROVED,
        actor_id=task.assignee_id if task.assignee_type == ACLSubjectType.USER else None,
        resource_id=task.id,
        resource_type="approval_task",
        detail={"comment": action.comment}
    )
    
    return {"message": "承認しました", "task_id": task_id}


@router.post("/tasks/{task_id}/reject")
async def reject_task(task_id: str, action: ApprovalTaskAction, db: AsyncSession = Depends(get_db)):
    """否認を実行"""
    result = await db.execute(select(ApprovalTask).where(ApprovalTask.id == task_id))
    task = result.scalar_one_or_none()
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
    result_req = await db.execute(select(ApprovalRequest).where(ApprovalRequest.id == task.request_id))
    approval_request = result_req.scalar_one_or_none()
    if approval_request:
        approval_request.status = ApprovalRequestStatus.REJECTED
        
    # 依頼者に通知
    await _notify_requester_of_task_action(task, "REJECTED", db)
    
    await db.commit()
    
    # 監査ログ
    await audit_service.log_event(
        db, AuditEventType.APPROVAL_REJECTED,
        actor_id=task.assignee_id if task.assignee_type == ACLSubjectType.USER else None,
        resource_id=task.id,
        resource_type="approval_task",
        detail={"comment": action.comment}
    )
    
    return {"message": "否認しました", "task_id": task_id}


@router.post("/tasks/{task_id}/return")
async def return_task(task_id: str, action: ApprovalTaskAction, db: AsyncSession = Depends(get_db)):
    """差戻しを実行"""
    result = await db.execute(select(ApprovalTask).where(ApprovalTask.id == task_id))
    task = result.scalar_one_or_none()
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
    result_req = await db.execute(select(ApprovalRequest).where(ApprovalRequest.id == task.request_id))
    approval_request = result_req.scalar_one_or_none()
    if approval_request:
        approval_request.status = ApprovalRequestStatus.RETURNED
        
    # 依頼者に通知
    await _notify_requester_of_task_action(task, "RETURNED", db)
    
    await db.commit()
    
    # 監査ログ
    await audit_service.log_event(
        db, AuditEventType.APPROVAL_RETURNED,
        actor_id=task.assignee_id if task.assignee_type == ACLSubjectType.USER else None,
        resource_id=task.id,
        resource_type="approval_task",
        detail={"comment": action.comment}
    )
    
    return {"message": "差戻ししました", "task_id": task_id}


@router.get("/tasks", response_model=List[ApprovalTaskResponse])
async def list_approval_tasks(
    status: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """承認タスク一覧を取得（自分に割り当てられたタスク）"""
    query = select(ApprovalTask).options(
        selectinload(ApprovalTask.request).selectinload(ApprovalRequest.contract)
    )
    
    # 自分に割り当てられたタスクのみ
    # assignee_type が USER の場合は assignee_id がユーザーID
    # assignee_type が EXTERNAL の場合は assignee_id がウォレットアドレス
    query = query.where(
        and_(
            ApprovalTask.assignee_type == 'USER',
            ApprovalTask.assignee_id == user_id
        )
    )
    
    if status:
        task_status = ApprovalTaskStatus[status.upper()]
        query = query.where(ApprovalTask.status == task_status)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return [
        {
            "id": t.id,
            "request_id": t.request_id,
            "stage": t.stage,
            "order": t.order,
            "assignee_type": t.assignee_type.value,
            "assignee_id": t.assignee_id,
            "status": t.status.value,
            "created_at": t.created_at,
            # 関連するリクエスト情報も少し付与
            "contract_title": t.request.contract.title if t.request and t.request.contract else "不明な契約"
        }
        for t in tasks
    ]


async def _check_and_progress_request(request_id: str, db: AsyncSession):
    """
    承認リクエストの進行状況をチェックし、必要に応じてステータスを更新
    """
    result = await db.execute(
        select(ApprovalRequest)
        .options(
            selectinload(ApprovalRequest.tasks),
            selectinload(ApprovalRequest.contract)
        )
        .where(ApprovalRequest.id == request_id)
    )
    approval_request = result.scalar_one_or_none()
    if not approval_request:
        return
    
    tasks = approval_request.tasks
    
    # 全タスクが承認済みか確認
    all_approved = all(t.status == ApprovalTaskStatus.APPROVED for t in tasks)
    if all_approved:
        approval_request.status = ApprovalRequestStatus.APPROVED
        
        # 最終承認の通知を依頼者に送信
        try:
            result_user = await db.execute(select(User).where(User.id == approval_request.created_by))
            requester = result_user.scalar_one_or_none()
            if requester:
                from app.core.config import settings
                payload = notification_service.create_task_status_changed_payload(
                    contract_title=approval_request.contract.title or "契約書",
                    assignee_name="最終承認",
                    action="APPROVED",
                    comment="すべての承認プロセスが完了しました",
                    request_url=f"{settings.FRONTEND_URL}/contracts/{approval_request.contract_id}"
                )
                await notification_service.notify_user(db, requester, "最終承認されました", payload)
        except Exception as e:
            print(f"[NOTIFICATION ERROR] 最終承認通知に失敗しました: {str(e)}")
            
        return
    
    # 否認または差戻しがあるか確認
    has_rejected = any(t.status == ApprovalTaskStatus.REJECTED for t in tasks)
    has_returned = any(t.status == ApprovalTaskStatus.RETURNED for t in tasks)
    
    if has_rejected:
        approval_request.status = ApprovalRequestStatus.REJECTED
    elif has_returned:
        approval_request.status = ApprovalRequestStatus.RETURNED
    else:
        # 次のステージへの通知が必要かチェック
        # 全てのタスクのうち、完了していない最小のステージを特定
        # (すでに全承認済みチェックは上で通っているので、必ず incomplete なステージがある)
        completed_stages = {t.stage for t in tasks if t.status == ApprovalTaskStatus.APPROVED}
        all_stages = {t.stage for t in tasks}
        
        # 各ステージが完全に承認されているか確認
        stage_status = {}
        for s in all_stages:
            stage_tasks = [t for t in tasks if t.stage == s]
            stage_status[s] = all(t.status == ApprovalTaskStatus.APPROVED for t in stage_tasks)
            
        # 承認が完了したステージの直後のステージを特定
        # 簡易的に：最小の未完了ステージのタスクにまだ通知が行われていなければ通知する
        current_min_incomplete_stage = min(s for s, complete in stage_status.items() if not complete)
        
        # このステージのタスクを取得して通知（初回の stage=1 は作成時に送信済みなので除外したいが、
        # ここでは「ステージが1つ進んだタイミング」でそのステージ全員に送る）
        # ※ 実際には重複送信を防ぐフラグ等が必要だが、現状は簡易的に実装
        
        # 前のステージが全て完了した直後のタイミングか判定
        # (全てのステージが1から順に並んでいると仮定)
        if current_min_incomplete_stage > 1:
            prev_stage_all_complete = stage_status.get(current_min_incomplete_stage - 1, False)
            if prev_stage_all_complete:
                # このステージの担当者に通知
                try:
                    next_tasks = [t for t in tasks if t.stage == current_min_incomplete_stage]
                    for task in next_tasks:
                        if task.assignee_type == ACLSubjectType.USER:
                            res_u = await db.execute(select(User).where(User.id == task.assignee_id))
                            u = res_u.scalar_one_or_none()
                            if u:
                                from app.core.config import settings
                                payload = notification_service.create_approval_request_payload(
                                    contract_title=approval_request.contract.title or "契約書",
                                    requester_name="LexFlow",
                                    due_at=approval_request.due_at,
                                    approval_url=f"{settings.FRONTEND_URL}/approvals",
                                    message=approval_request.message
                                )
                                await notification_service.notify_user(db, u, "承認依頼が届いています", payload)
                except Exception as e:
                    print(f"[NOTIFICATION ERROR] 次ステージへの通知に失敗しました: {str(e)}")


# ===== マジックリンクエンドポイント =====

@router.post("/tasks/{task_id}/magic-link", response_model=MagicLinkResponse)
async def create_magic_link(
    task_id: str,
    expires_hours: int = 72,
    db: AsyncSession = Depends(get_db)
):
    """
    承認タスク用のマジックリンクを発行
    
    - 外部承認者向け
    - ワンタイムトークン（期限付き）
    """
    result_task = await db.execute(select(ApprovalTask).where(ApprovalTask.id == task_id))
    task = result_task.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="承認タスクが見つかりません")
    
    # 既存の有効なリンクを失効
    result_links = await db.execute(select(MagicLink).where(
        MagicLink.task_id == task_id,
        MagicLink.revoked_at == None,
        MagicLink.consumed_at == None
    ))
    existing_links = result_links.scalars().all()
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
    await db.commit()
    await db.refresh(magic_link)
    
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
async def consume_magic_link(token: str, db: AsyncSession = Depends(get_db)):
    """
    マジックリンクを使用（検証）
    
    - トークンを検証
    - 有効なら承認タスク情報を返す
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    result_link = await db.execute(select(MagicLink).where(MagicLink.token_hash == token_hash))
    magic_link = result_link.scalar_one_or_none()
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
    await db.commit()
    
    # タスク情報を取得
    result_task = await db.execute(select(ApprovalTask).where(ApprovalTask.id == magic_link.task_id))
    task = result_task.scalar_one_or_none()
    
    return {
        "valid": True,
        "task_id": task.id if task else None,
        "request_id": task.request_id if task else None,
        "message": "リンクが検証されました。承認アクションを実行できます。"
    }


@router.delete("/magic-link/{link_id}")
async def revoke_magic_link(link_id: str, db: AsyncSession = Depends(get_db)):
    """マジックリンクを失効"""
    result = await db.execute(select(MagicLink).where(MagicLink.id == link_id))
    magic_link = result.scalar_one_or_none()
    if not magic_link:
        raise HTTPException(status_code=404, detail="リンクが見つかりません")
    
    magic_link.revoked_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "リンクを失効しました"}


async def _notify_requester_of_task_action(
    task: ApprovalTask, 
    action: str, 
    db: AsyncSession
):
    """承認依頼者にタスクの結果を通知"""
    try:
        # リクエストと契約を取得
        result_req = await db.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.contract))
            .where(ApprovalRequest.id == task.request_id)
        )
        request = result_req.scalar_one_or_none()
        if not request:
            return

        # 依頼者（作成者）ユーザーを取得
        result_user = await db.execute(select(User).where(User.id == request.created_by))
        requester = result_user.scalar_one_or_none()
        if not requester:
            return

        # 承認者の情報を取得
        assignee_name = "承認者"
        if task.assignee_type == ACLSubjectType.USER:
            result_assignee = await db.execute(select(User).where(User.id == task.assignee_id))
            assignee_user = result_assignee.scalar_one_or_none()
            if assignee_user:
                assignee_name = assignee_user.display_name or assignee_user.email
        elif task.assignee_type == ACLSubjectType.EXTERNAL:
            assignee_name = task.assignee_id # メールアドレス等

        # 通知ペイロード作成
        from app.core.config import settings
        request_url = f"{settings.FRONTEND_URL}/contracts/{request.contract_id}"
        
        payload = notification_service.create_task_status_changed_payload(
            contract_title=request.contract.title or "契約書",
            assignee_name=assignee_name,
            action=action,
            comment=task.comment,
            request_url=request_url
        )

        # ユーザーに通知
        await notification_service.notify_user(
            db=db,
            user=requester,
            subject=f"承認ステータス変更: {request.contract.title or '契約書'}",
            payload=payload
        )
    except Exception as e:
        print(f"[NOTIFICATION ERROR] 依頼者へのステータス変更通知に失敗しました: {str(e)}")
