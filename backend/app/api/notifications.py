"""
LexFlow Protocol - Notifications API (V3)
通知設定、Slack連携、通知履歴のエンドポイント
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import json

from app.core.database import get_db
from app.models.models import Notification, NotificationChannel, NotificationStatus
from app.services.notification_service import notification_service


router = APIRouter(prefix="/notifications", tags=["通知 (Notifications)"])


# ===== リクエスト/レスポンススキーマ =====

class SlackIntegrationCreate(BaseModel):
    """Slack連携設定リクエスト"""
    workspace_id: str
    webhook_url: str
    channel_name: str


class SlackIntegrationResponse(BaseModel):
    """Slack連携設定レスポンス"""
    id: str
    workspace_id: str
    channel_name: str
    is_active: bool
    created_at: datetime


class NotificationResponse(BaseModel):
    """通知レスポンス"""
    id: str
    channel: str
    recipient: str
    subject: Optional[str]
    payload: dict
    status: str
    sent_at: Optional[datetime]
    error: Optional[str]
    created_at: datetime


class NotificationListResponse(BaseModel):
    """通知一覧レスポンス"""
    notifications: List[NotificationResponse]
    total: int
    page: int
    page_size: int


class SendTestNotificationRequest(BaseModel):
    """テスト通知送信リクエスト"""
    channel: str  # "email" or "slack"
    recipient: str  # メールアドレス or Webhook URL


# ===== 一時的なSlack連携設定保存（本番環境ではDB保存） =====
_slack_integrations: dict = {}


# ===== エンドポイント =====

@router.post("/integrations/slack", response_model=SlackIntegrationResponse)
async def connect_slack(request: SlackIntegrationCreate):
    """
    Slack Webhook連携を設定
    
    - ワークスペースごとに複数のWebhookを設定可能
    - 本番環境ではDBに保存
    """
    import uuid
    
    integration_id = str(uuid.uuid4())
    
    integration = {
        "id": integration_id,
        "workspace_id": request.workspace_id,
        "webhook_url": request.webhook_url,
        "channel_name": request.channel_name,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    _slack_integrations[integration_id] = integration
    
    return SlackIntegrationResponse(
        id=integration_id,
        workspace_id=request.workspace_id,
        channel_name=request.channel_name,
        is_active=True,
        created_at=integration["created_at"]
    )


@router.get("/integrations/slack", response_model=List[SlackIntegrationResponse])
async def list_slack_integrations(workspace_id: str):
    """ワークスペースのSlack連携一覧を取得"""
    integrations = [
        SlackIntegrationResponse(
            id=i["id"],
            workspace_id=i["workspace_id"],
            channel_name=i["channel_name"],
            is_active=i["is_active"],
            created_at=i["created_at"]
        )
        for i in _slack_integrations.values()
        if i["workspace_id"] == workspace_id
    ]
    return integrations


@router.delete("/integrations/slack/{integration_id}")
async def disconnect_slack(integration_id: str):
    """Slack連携を解除"""
    if integration_id not in _slack_integrations:
        raise HTTPException(status_code=404, detail="連携が見つかりません")
    
    del _slack_integrations[integration_id]
    return {"message": "Slack連携を解除しました"}


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    workspace_id: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    通知履歴一覧を取得
    
    - チャンネル、ステータスでフィルタ可能
    - ページネーション対応
    """
    stmt = select(Notification)
    
    if channel:
        try:
            ch = NotificationChannel(channel)
            stmt = stmt.where(Notification.channel == ch)
        except ValueError:
            pass
    
    if status:
        try:
            st = NotificationStatus(status)
            stmt = stmt.where(Notification.status == st)
        except ValueError:
            pass
    
    # 総数を取得
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id,
                channel=n.channel.value,
                recipient=n.recipient,
                subject=n.subject,
                payload=json.loads(n.payload) if n.payload else {},
                status=n.status.value,
                sent_at=n.sent_at,
                error=n.error,
                created_at=n.created_at
            )
            for n in notifications
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/test")
async def send_test_notification(request: SendTestNotificationRequest, db: AsyncSession = Depends(get_db)):
    """
    テスト通知を送信
    
    - 設定確認用
    """
    if request.channel == "email":
        channel = NotificationChannel.EMAIL
        payload = {
            "body": "これはLexFlowからのテスト通知です。\n\n正常に受信できた場合、メール通知は正しく設定されています。",
            "html_body": "<h2>テスト通知</h2><p>これはLexFlowからのテスト通知です。</p><p>正常に受信できた場合、メール通知は正しく設定されています。</p>"
        }
        subject = "[LexFlow] テスト通知"
    elif request.channel == "slack":
        channel = NotificationChannel.SLACK
        payload = {
            "message": "🔔 これはLexFlowからのテスト通知です。正常に受信できた場合、Slack連携は正しく設定されています。",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🔔 テスト通知*\n\nこれはLexFlowからのテスト通知です。\n正常に受信できた場合、Slack連携は正しく設定されています。"
                    }
                }
            ]
        }
        subject = None
    else:
        raise HTTPException(status_code=400, detail="無効なチャンネルです。'email' または 'slack' を指定してください。")
    
    notification = await notification_service.create_and_send(
        db=db,
        channel=channel,
        recipient=request.recipient,
        subject=subject,
        payload=payload
    )
    
    return {
        "success": notification.status == NotificationStatus.SENT,
        "notification_id": notification.id,
        "status": notification.status.value,
        "error": notification.error
    }


@router.post("/{notification_id}/retry")
async def retry_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
    """
    失敗した通知を再送信
    """
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="通知が見つかりません")
    
    if notification.status != NotificationStatus.FAILED:
        raise HTTPException(status_code=400, detail="この通知は再送信できません")
    
    notification.status = NotificationStatus.RETRYING
    notification.retry_count += 1
    await db.commit()
    
    payload = json.loads(notification.payload) if notification.payload else {}
    
    try:
        if notification.channel == NotificationChannel.EMAIL:
            success = await notification_service.send_email(
                recipient=notification.recipient,
                subject=notification.subject or "LexFlow通知",
                body=payload.get("body", ""),
                html_body=payload.get("html_body")
            )
        elif notification.channel == NotificationChannel.SLACK:
            success = await notification_service.send_slack(
                webhook_url=notification.recipient,
                message=payload.get("message", ""),
                blocks=payload.get("blocks")
            )
        else:
            success = False
        
        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
            notification.error = None
        else:
            notification.status = NotificationStatus.FAILED
            notification.error = "再送信に失敗しました"
    except Exception as e:
        notification.status = NotificationStatus.FAILED
        notification.error = str(e)
    
    await db.commit()
    
    return {
        "success": notification.status == NotificationStatus.SENT,
        "status": notification.status.value,
        "retry_count": notification.retry_count,
        "error": notification.error
    }
