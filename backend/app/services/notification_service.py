"""
LexFlow Protocol - Notification Service (V3)
Email/Slack通知の送信を提供
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio

from sqlalchemy.orm import Session

from app.models.models import Notification, NotificationChannel, NotificationStatus


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
        
        - 本番環境ではSendGrid/SMTPを使用
        - ここでは簡略化のためログ出力のみ
        """
        print(f"[EMAIL] To: {recipient}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] Body: {body[:100]}...")
        
        # 本番実装例（SendGrid）:
        # import sendgrid
        # from sendgrid.helpers.mail import Mail
        # sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
        # message = Mail(
        #     from_email='noreply@lexflow.example.com',
        #     to_emails=recipient,
        #     subject=subject,
        #     html_content=html_body or body
        # )
        # response = sg.send(message)
        # return response.status_code == 202
        
        return True
    
    # ===== Slack送信 =====
    
    @staticmethod
    async def send_slack(
        webhook_url: str,
        message: str,
        blocks: Optional[list] = None
    ) -> bool:
        """
        Slackにメッセージを送信
        
        - Webhookを使用
        - ここでは簡略化のためログ出力のみ
        """
        print(f"[SLACK] Webhook: {webhook_url[:50]}...")
        print(f"[SLACK] Message: {message[:100]}...")
        
        # 本番実装例:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     payload = {"text": message}
        #     if blocks:
        #         payload["blocks"] = blocks
        #     response = await client.post(webhook_url, json=payload)
        #     return response.status_code == 200
        
        return True
    
    # ===== 通知作成と送信 =====
    
    @staticmethod
    async def create_and_send(
        db: Session,
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
        db.flush()
        
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
        
        db.commit()
        db.refresh(notification)
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
        </ADDITIONAL_METADATA>
        
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


# シングルトンインスタンス
notification_service = NotificationService()
