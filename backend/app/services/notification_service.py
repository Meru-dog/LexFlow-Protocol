"""
LexFlow Protocol - Notification Service (V3)
Email/Slack通知の送信を提供
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Notification, NotificationChannel, NotificationStatus
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class NotificationService:
    """通知サービスクラス"""
    
    # ===== メール送信 =====
    
    @staticmethod
    async def send_email(
        recipient: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        メールを送信
        
        - USE_SMTP=Trueの場合: 実際にSMTP経由で送信
        - USE_SMTP=Falseの場合: ログ出力のみ
        """
        from app.core.config import settings
        
        # ログ出力（デ開発時の確認用）
        print(f"[EMAIL] To: {recipient}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] Body: {body[:100]}...")
        
        # SMTP送信が無効の場合はログのみ
        if not settings.USE_SMTP:
            logger.info(f"[EMAIL] SMTP disabled. Email to {recipient} not sent (subject: {subject})")
            return True
        
        # 実際のSMTP送信
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # メッセージ作成
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # プレーンテキスト部分
            part1 = MIMEText(body, 'plain', 'utf-8')
            msg.attach(part1)
            
            # HTML部分（指定されている場合）
            if html_body:
                part2 = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(part2)
            
            # SMTP接続・送信
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()  # TLS暗号化
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"[EMAIL] Successfully sent email to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Failed to send email to {recipient}: {str(e)}", exc_info=True)
            # 送信失敗時もログには記録されているため、Falseを返す
            return False
    
    # ===== Slack送信 =====
    
    @staticmethod
    async def send_slack(
        webhook_url: str,
        message: str,
        blocks: Optional[list] = None
    ) -> bool:
        """
        Slackにメッセージを送信
        
        - Webhookを使用して実際に送信
        - 送信失敗時はログに記録
        """
        logger.debug(f"[SLACK] Sending to webhook: {webhook_url[:50]}...")
        logger.debug(f"[SLACK] Message: {message[:100]}...")
        
        # 実際のWebhook送信
        try:
            import httpx
            
            payload = {"text": message}
            if blocks:
                payload["blocks"] = blocks
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                
                if response.status_code == 200:
                    logger.info("[SLACK] Successfully sent message to Slack")
                    return True
                else:
                    logger.error(f"[SLACK ERROR] Webhook送信に失敗しました: {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"[SLACK ERROR] Failed to send Slack message: {str(e)}", exc_info=True)
            return False
    
    # ===== 通知作成と送信 =====
    
    @staticmethod
    async def create_and_send(
        db: AsyncSession,
        channel: NotificationChannel,
        recipient: str,
        subject: Optional[str],
        payload: Dict[str, Any]
    ) -> Notification:
        """
        通知を作成し、送信を試行
        
        - 失敗時はステータスをFAILEDに設定
        - リトライは別途ジョブで処理
        """
        notification_id = str(uuid.uuid4())
        notification = Notification(
            id=notification_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            payload=json.dumps(payload, ensure_ascii=False),
            status=NotificationStatus.PENDING
        )
        db.add(notification)
        await db.flush()
        
        try:
            if channel == NotificationChannel.EMAIL:
                success = await NotificationService.send_email(
                    recipient=recipient,
                    subject=subject or "LexFlow通知",
                    body=payload.get("body", ""),
                    html_body=payload.get("html_body")
                )
            elif channel == NotificationChannel.SLACK:
                success = await NotificationService.send_slack(
                    webhook_url=recipient,  # Slackの場合はWebhook URLを使用
                    message=payload.get("message", ""),
                    blocks=payload.get("blocks")
                )
            else:
                success = False
            
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            else:
                notification.status = NotificationStatus.FAILED
                notification.error = "送信に失敗しました"
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error = str(e)
        
        await db.commit()
        await db.refresh(notification)
        return notification
    
    # ===== 承認依頼通知テンプレート =====
    
    @staticmethod
    def create_approval_request_payload(
        contract_title: str,
        requester_name: str,
        due_at: Optional[datetime],
        approval_url: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """承認依頼通知のペイロードを作成"""
        due_str = due_at.strftime("%Y年%m月%d日 %H:%M") if due_at else "未設定"
        
        body = f"""
        承認依頼が届いています。
        
        契約書: {contract_title}
        依頼者: {requester_name}
        期限: {due_str}
        
        {message or ""}
        
        以下のリンクから承認を行ってください:
        {approval_url}
        """
        
        html_body = f"""
        <h2>承認依頼が届いています</h2>
        <p><strong>契約書:</strong> {contract_title}</p>
        <p><strong>依頼者:</strong> {requester_name}</p>
        <p><strong>期限:</strong> {due_str}</p>
        <p>{message or ""}</p>
        <p><a href="{approval_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">承認ページを開く</a></p>
        """
        
        return {
            "body": body.strip(),
            "html_body": html_body,
            "message": f"📝 承認依頼: {contract_title} (期限: {due_str})",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📝 承認依頼が届いています*\n\n*契約書:* {contract_title}\n*依頼者:* {requester_name}\n*期限:* {due_str}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "承認ページを開く"},
                            "url": approval_url,
                            "style": "primary"
                        }
                    ]
                }
            ]
        }
    
    # ===== リマインド通知テンプレート =====
    
    @staticmethod
    def create_reminder_payload(
        contract_title: str,
        due_at: datetime,
        days_until_due: int,
        approval_url: str
    ) -> Dict[str, Any]:
        """リマインド通知のペイロードを作成"""
        due_str = due_at.strftime("%Y年%m月%d日 %H:%M")
        
        if days_until_due == 0:
            urgency = "⚠️ 本日が期限です"
        elif days_until_due == 1:
            urgency = "⚠️ 明日が期限です"
        else:
            urgency = f"📅 期限まであと{days_until_due}日です"
        
        body = f"""
{urgency}

契約書: {contract_title}
期限: {due_str}

以下のリンクから承認を行ってください:
{approval_url}
"""
        
        return {
            "body": body.strip(),
            "message": f"{urgency} - {contract_title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{urgency}*\n\n*契約書:* {contract_title}\n*期限:* {due_str}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "承認ページを開く"},
                            "url": approval_url,
                            "style": "danger" if days_until_due <= 1 else "primary"
                        }
                    ]
                }
            ]
        }


    @staticmethod
    def create_task_status_changed_payload(
        contract_title: str,
        assignee_name: str,
        action: str,  # "APPROVED", "REJECTED", "RETURNED"
        comment: Optional[str] = None,
        request_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """承認タスクのステータス変更通知のペイロードを作成"""
        action_map = {
            "APPROVED": "✅ 承認されました",
            "REJECTED": "❌ 否認されました",
            "RETURNED": "↩️ 差戻されました"
        }
        action_text = action_map.get(action, action)
        
        body = f"""
{action_text}

契約書: {contract_title}
担当者: {assignee_name}
コメント: {comment or "なし"}

詳細はこちら:
{request_url}
"""
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": action_text
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*契約書:* {contract_title}\n*担当者:* {assignee_name}\n*コメント:* {comment or 'なし'}"
                }
            }
        ]
        
        if request_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "リクエストを確認"},
                        "url": request_url,
                        "style": "primary" if action == "APPROVED" else "danger"
                    }
                ]
            })
            
        return {
            "body": body.strip(),
            "message": f"{action_text}: {contract_title}",
            "blocks": blocks
        }

    # ===== ユーザーへの統合送信 =====
    
    @staticmethod
    async def notify_user(
        db: AsyncSession,
        user: Any,  # Userモデルのインスタンス
        subject: Optional[str],
        payload: Dict[str, Any]
    ) -> List[Notification]:
        """ユーザー設定に合わせてEmailとSlackの両方で通知を送信"""
        notifications = []
        
        # Email通知
        if hasattr(user, 'email') and user.email:
            n = await NotificationService.create_and_send(
                db=db,
                channel=NotificationChannel.EMAIL,
                recipient=user.email,
                subject=subject or "LexFlow通知",
                payload=payload
            )
            notifications.append(n)
            
        # Slack通知
        if hasattr(user, 'slack_webhook_url') and user.slack_webhook_url:
            n = await NotificationService.create_and_send(
                db=db,
                channel=NotificationChannel.SLACK,
                recipient=user.slack_webhook_url,
                subject=None,
                payload=payload
            )
            notifications.append(n)
            
        return notifications


# シングルトンインスタンス
notification_service = NotificationService()
