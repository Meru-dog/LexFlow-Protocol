"""
LexFlow Protocol - Audit Trail Service (V3)
監査イベントの記録とハッシュチェーンによる改ざん耐性を提供
"""
import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import AuditEvent, AuditEventType


class AuditService:
    """監査証跡サービスクラス"""
    
    @staticmethod
    def compute_event_hash(
        event_id: str,
        event_type: str,
        actor_id: Optional[str],
        workspace_id: Optional[str],
        contract_id: Optional[str],
        detail_json: Optional[str],
        prev_hash: Optional[str],
        timestamp: str
    ) -> str:
        """
        イベントのハッシュを計算
        
        - 前のイベントのハッシュを含めることでチェーンを形成
        - SHA-256を使用
        """
        data = f"{event_id}|{event_type}|{actor_id or ''}|{workspace_id or ''}|{contract_id or ''}|{detail_json or ''}|{prev_hash or ''}|{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    async def get_latest_hash(db: AsyncSession, workspace_id: Optional[str] = None) -> Optional[str]:
        """
        最新の監査イベントのハッシュを取得
        
        - ワークスペース指定時はそのワークスペース内の最新
        - 未指定時はグローバルで最新
        """
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
        if workspace_id:
            stmt = stmt.where(AuditEvent.workspace_id == workspace_id)
        
        result = await db.execute(stmt)
        latest = result.scalars().first()
        return latest.hash if latest else None
    
    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: AuditEventType,
        actor_id: Optional[str] = None,
        actor_wallet: Optional[str] = None,
        actor_ip: Optional[str] = None,
        actor_user_agent: Optional[str] = None,
        workspace_id: Optional[str] = None,
        contract_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        監査イベントを記録
        
        - ハッシュチェーンを維持
        - 明示的なタイムスタンプを使用してハッシュの一貫性を確保
        """
        event_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        timestamp_str = created_at.isoformat()
        detail_json = json.dumps(detail, ensure_ascii=False) if detail else None
        
        # 前のハッシュを取得
        prev_hash = await AuditService.get_latest_hash(db, workspace_id)
        
        # 新しいハッシュを計算
        event_hash = AuditService.compute_event_hash(
            event_id=event_id,
            event_type=event_type.value,
            actor_id=actor_id,
            workspace_id=workspace_id,
            contract_id=contract_id,
            detail_json=detail_json,
            prev_hash=prev_hash,
            timestamp=timestamp_str
        )
        
        # イベント作成
        event = AuditEvent(
            id=event_id,
            type=event_type,
            actor_id=actor_id,
            actor_wallet=actor_wallet,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            workspace_id=workspace_id,
            contract_id=contract_id,
            resource_id=resource_id,
            resource_type=resource_type,
            detail_json=detail_json,
            prev_hash=prev_hash,
            hash=event_hash,
            created_at=created_at
        )
        db.add(event)
        
        return event
    
    @staticmethod
    async def verify_chain(db: AsyncSession, workspace_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        ハッシュチェーンの整合性を検証
        """
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.asc())
        if workspace_id:
            stmt = stmt.where(AuditEvent.workspace_id == workspace_id)
        
        result = await db.execute(stmt.limit(limit))
        events = result.scalars().all()
        
        if not events:
            return {
                "valid": True,
                "checked_count": 0,
                "first_invalid_id": None,
                "message": "監査イベントがありません"
            }
        
        prev_hash = None
        for i, event in enumerate(events):
            # 1. 前のハッシュが一致するか確認
            if event.prev_hash != prev_hash:
                return {
                    "valid": False,
                    "checked_count": i,
                    "first_invalid_id": event.id,
                    "message": f"イベント {event.id} の前ハッシュが不整合です (期待: {prev_hash or 'None'}, 実際: {event.prev_hash})"
                }
            
            # 2. ハッシュを再計算して検証
            # ISO format への変換は log_event と一致させる
            timestamp_str = event.created_at.isoformat() if event.created_at else ""
            
            expected_hash = AuditService.compute_event_hash(
                event_id=event.id,
                event_type=event.type.value,
                actor_id=event.actor_id,
                workspace_id=event.workspace_id,
                contract_id=event.contract_id,
                detail_json=event.detail_json,
                prev_hash=event.prev_hash,
                timestamp=timestamp_str
            )
            
            if event.hash != expected_hash:
                return {
                    "valid": False,
                    "checked_count": i,
                    "first_invalid_id": event.id,
                    "message": f"イベント {event.id} の自体ハッシュが不整合です (改ざんの疑い)"
                }
            
            prev_hash = event.hash
        
        return {
            "valid": True,
            "checked_count": len(events),
            "first_invalid_id": None,
            "message": f"{len(events)}件のイベントを検証し、すべての整合性が確認されました。"
        }


# シングルトンインスタンス
audit_service = AuditService()
