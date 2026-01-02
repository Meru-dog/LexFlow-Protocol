"""
LexFlow Protocol - Audit Trail API (V3)
監査ログの閲覧、検索、整合性検証のエンドポイント
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.models.models import AuditEvent, AuditEventType
from app.services.audit_service import audit_service


router = APIRouter(prefix="/audit", tags=["監査証跡 (Audit Trail)"])


# ===== レスポンススキーマ =====

class AuditEventResponse(BaseModel):
    """監査イベントレスポンス"""
    id: str
    type: str
    actor_id: Optional[str]
    actor_wallet: Optional[str]
    workspace_id: Optional[str]
    contract_id: Optional[str]
    resource_id: Optional[str]
    resource_type: Optional[str]
    detail: Optional[dict]
    prev_hash: Optional[str]
    hash: str
    created_at: datetime


class AuditListResponse(BaseModel):
    """監査イベント一覧レスポンス"""
    events: List[AuditEventResponse]
    total: int
    page: int
    page_size: int


class ChainVerifyResponse(BaseModel):
    """チェーン検証レスポンス"""
    valid: bool
    checked_count: int
    first_invalid_id: Optional[str]
    message: str


# ===== エンドポイント =====

@router.get("/events", response_model=AuditListResponse)
async def list_audit_events(
    workspace_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    event_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    監査イベント一覧を取得
    
    - ワークスペース、契約書、アクター、イベントタイプでフィルタ可能
    - 日時範囲でフィルタ可能
    - ページネーション対応
    """
    query = db.query(AuditEvent)
    
    # フィルタ適用
    if workspace_id:
        query = query.filter(AuditEvent.workspace_id == workspace_id)
    if contract_id:
        query = query.filter(AuditEvent.contract_id == contract_id)
    if actor_id:
        query = query.filter(AuditEvent.actor_id == actor_id)
    if event_type:
        try:
            etype = AuditEventType(event_type)
            query = query.filter(AuditEvent.type == etype)
        except ValueError:
            pass  # 不正なタイプは無視
    if from_date:
        query = query.filter(AuditEvent.created_at >= from_date)
    if to_date:
        query = query.filter(AuditEvent.created_at <= to_date)
    
    # 総数を取得
    total = query.count()
    
    # ページネーション
    offset = (page - 1) * page_size
    events = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(page_size).all()
    
    return AuditListResponse(
        events=[
            AuditEventResponse(
                id=e.id,
                type=e.type.value,
                actor_id=e.actor_id,
                actor_wallet=e.actor_wallet,
                workspace_id=e.workspace_id,
                contract_id=e.contract_id,
                resource_id=e.resource_id,
                resource_type=e.resource_type,
                detail=json.loads(e.detail_json) if e.detail_json else None,
                prev_hash=e.prev_hash,
                hash=e.hash,
                created_at=e.created_at
            )
            for e in events
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/events/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(event_id: str, db: Session = Depends(get_db)):
    """監査イベントの詳細を取得"""
    event = db.query(AuditEvent).filter(AuditEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="監査イベントが見つかりません")
    
    return AuditEventResponse(
        id=event.id,
        type=event.type.value,
        actor_id=event.actor_id,
        actor_wallet=event.actor_wallet,
        workspace_id=event.workspace_id,
        contract_id=event.contract_id,
        resource_id=event.resource_id,
        resource_type=event.resource_type,
        detail=json.loads(event.detail_json) if event.detail_json else None,
        prev_hash=event.prev_hash,
        hash=event.hash,
        created_at=event.created_at
    )


@router.get("/verify", response_model=ChainVerifyResponse)
async def verify_chain(
    workspace_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    ハッシュチェーンの整合性を検証
    
    - ワークスペース単位または全体で検証
    - 前のイベントのハッシュとの連続性をチェック
    """
    result = audit_service.verify_chain(db, workspace_id, limit)
    
    return ChainVerifyResponse(**result)


@router.get("/types")
async def list_event_types():
    """利用可能な監査イベントタイプ一覧を取得"""
    return {
        "types": [
            {"key": t.value, "name": t.name}
            for t in AuditEventType
        ]
    }
