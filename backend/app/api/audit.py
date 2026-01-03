"""
LexFlow Protocol - Audit Trail API (V3)
監査ログの閲覧、検索、整合性検証のエンドポイント
"""
from datetime import datetime
from typing import List, Optional
import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

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
    db: AsyncSession = Depends(get_db)
):
    """
    監査イベント一覧を取得
    
    - ワークスペース、契約書、アクター、イベントタイプでフィルタ可能
    - 日時範囲でフィルタ可能
    - ページネーション対応
    """
    stmt = select(AuditEvent)
    
    # フィルタ適用
    if workspace_id:
        stmt = stmt.where(AuditEvent.workspace_id == workspace_id)
    if contract_id:
        stmt = stmt.where(AuditEvent.contract_id == contract_id)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if event_type:
        try:
            etype = AuditEventType(event_type)
            stmt = stmt.where(AuditEvent.type == etype)
        except ValueError:
            pass  # 不正なタイプは無視
    if from_date:
        stmt = stmt.where(AuditEvent.created_at >= from_date)
    if to_date:
        stmt = stmt.where(AuditEvent.created_at <= to_date)
    
    # 総数を取得
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # ページネーション
    offset = (page - 1) * page_size
    stmt = stmt.order_by(AuditEvent.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    events = result.scalars().all()
    
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
async def get_audit_event(event_id: str, db: AsyncSession = Depends(get_db)):
    """監査イベントの詳細を取得"""
    result = await db.execute(select(AuditEvent).where(AuditEvent.id == event_id))
    event = result.scalar_one_or_none()
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
    db: AsyncSession = Depends(get_db)
):
    """
    ハッシュチェーンの整合性を検証
    
    - ワークスペース単位または全体で検証
    - 前のイベントのハッシュとの連続性をチェック
    """
    result = await audit_service.verify_chain(db, workspace_id, limit)
    
    return ChainVerifyResponse(**result)


@router.get("/export")
async def export_audit_events(
    format: str = Query("csv", regex="^(csv|json)$"),
    workspace_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    event_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(1000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db)
):
    """
    監査イベントをCSVまたはJSON形式でエクスポート
    
    - format: csv または json
    - limit: 最大出力件数（デフォルト1000、最大10000）
    - その他のフィルタはlist_audit_eventsと同様
    """
    # イベント取得（list_audit_eventsと同じロジック）
    stmt = select(AuditEvent)
    
    if workspace_id:
        stmt = stmt.where(AuditEvent.workspace_id == workspace_id)
    if contract_id:
        stmt = stmt.where(AuditEvent.contract_id == contract_id)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if event_type:
        try:
            etype = AuditEventType(event_type)
            stmt = stmt.where(AuditEvent.type == etype)
        except ValueError:
            pass
    if from_date:
        stmt = stmt.where(AuditEvent.created_at >= from_date)
    if to_date:
        stmt = stmt.where(AuditEvent.created_at <= to_date)
    
    stmt = stmt.order_by(AuditEvent.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    if format == "csv":
        # CSV生成
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            "ID", "Type", "Actor ID", "Actor Wallet", "Workspace ID",
            "Contract ID", "Resource ID", "Resource Type",
            "Detail", "Prev Hash", "Hash", "Created At"
        ])
        
        # データ行
        for e in events:
            writer.writerow([
                e.id,
                e.type.value,
                e.actor_id or "",
                e.actor_wallet or "",
                e.workspace_id or "",
                e.contract_id or "",
                e.resource_id or "",
                e.resource_type or "",
                e.detail_json or "",
                e.prev_hash or "",
                e.hash,
                e.created_at.isoformat()
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    
    else:  # JSON
        # JSON生成
        data = [
            {
                "id": e.id,
                "type": e.type.value,
                "actor_id": e.actor_id,
                "actor_wallet": e.actor_wallet,
                "workspace_id": e.workspace_id,
                "contract_id": e.contract_id,
                "resource_id": e.resource_id,
                "resource_type": e.resource_type,
                "detail": json.loads(e.detail_json) if e.detail_json else None,
                "prev_hash": e.prev_hash,
                "hash": e.hash,
                "created_at": e.created_at.isoformat()
            }
            for e in events
        ]
        
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        return StreamingResponse(
            iter([json_str]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
        )


@router.get("/types")
async def list_event_types():
    """利用可能な監査イベントタイプ一覧を取得"""
    return {
        "types": [
            {"key": t.value, "name": t.name}
            for t in AuditEventType
        ]
    }
