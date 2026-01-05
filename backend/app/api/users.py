"""
LexFlow Protocol - Users API (V3)
プロフィールの取得、更新
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import User
from app.api.auth import get_current_user_id

router = APIRouter(prefix="/users", tags=["ユーザー管理 (Users)"])

# ===== スキーマ =====

class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    status: str
    created_at: str

class UserProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    slack_webhook_url: Optional[str] = None

class SlackTestRequest(BaseModel):
    """Slack通知テストリクエスト"""
    webhook_url: Optional[str] = None

# ===== エンドポイント =====

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """自身のプロフィールを取得"""
    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="ユーザー情報が失われました（DBリセット等）。再ログインしてください"
        )
        
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        slack_webhook_url=user.slack_webhook_url,
        status=user.status,
        created_at=user.created_at.isoformat()
    )

@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    request: UserProfileUpdateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """自身のプロフィールを更新"""
    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="ユーザー情報が失われました。再ログインしてください"
        )
    
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.slack_webhook_url is not None:
        user.slack_webhook_url = request.slack_webhook_url
        
    await db.commit()
    await db.refresh(user)
    
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        slack_webhook_url=user.slack_webhook_url,
        status=user.status,
        created_at=user.created_at.isoformat()
    )

@router.post("/me/test-slack")
async def test_slack_notification(
    request: Optional[SlackTestRequest] = None,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """自身のSlack Webhook設定をテスト"""
    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()
    
    # リクエストボディにURLがある場合はそれを使用、なければDBのURLを使用
    webhook_url = (request.webhook_url if request else None) or (user.slack_webhook_url if user else None)
    
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Slack Webhook URLが設定されていません")
    
    from app.services.notification_service import notification_service
    from app.models.models import NotificationChannel
    
    # テストメッセージを送信
    payload = {
        "message": "🔔 LexFlow Protocol: Slack通知のテストに成功しました！",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Slack通知テスト"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"LexFlow Protocolからのテスト通知です。このメッセージが表示されている場合、Webhookの設定は正常です。\n\n*ユーザー:* {user.display_name or user.email}"
                }
            }
        ]
    }
    
    notification = await notification_service.create_and_send(
        db=db,
        channel=NotificationChannel.SLACK,
        recipient=webhook_url,
        subject="Slack Notification Test",
        payload=payload
    )
    
    # ステータスをチェック
    from app.models.models import NotificationStatus
    if notification.status == NotificationStatus.SENT:
        return {"success": True, "message": "テストメッセージを送信しました。Slackを確認してください。"}
    else:
        return {"success": False, "message": f"送信に失敗しました: {notification.error or '不明なエラー'}"}

@router.post("/me/test-email")
async def test_email_notification(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """自身の登録メールアドレスにテストメッセージを送信"""
    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="ユーザーが見つかりません。再ログインしてください"
        )
    if not user.email:
        raise HTTPException(status_code=400, detail="メールアドレスが登録されていません")
    
    from app.services.notification_service import notification_service
    from app.models.models import NotificationChannel
    
    # テストメッセージを送信
    payload = {
        "body": f"LexFlow Protocolからのテストメールです。このメールが届いている場合、システム設定は正常です。\n\nユーザー: {user.display_name or user.email}",
        "html_body": f"""
        <h2>✅ LexFlow Protocol メールテスト</h2>
        <p>LexFlow Protocolからのテストメールです。このメールが届いている場合、通知システムは正常に動作しています。</p>
        <ul>
            <li><strong>送信先:</strong> {user.email}</li>
            <li><strong>表示名:</strong> {user.display_name or 'なし'}</li>
        </ul>
        <p>承認依頼や重要な通知もこのアドレスに届きます。</p>
        """
    }
    
    notification = await notification_service.create_and_send(
        db=db,
        channel=NotificationChannel.EMAIL,
        recipient=user.email,
        subject="【LexFlow】メール通知テスト",
        payload=payload
    )
    
    # ステータスをチェック
    from app.models.models import NotificationStatus
    if notification.status == NotificationStatus.SENT:
        return {"success": True, "message": "テストメールを送信しました。受信ボックスを確認してください。"}
    else:
        return {"success": False, "message": f"送信に失敗しました: {notification.error or '不明なエラー'}"}
