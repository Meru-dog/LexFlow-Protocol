"""
LexFlow Protocol - 義務抽出・管理サービス (Version 2: F2)

契約書から義務を自動抽出し、管理するためのサービス
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import openai

from app.core.config import settings
from app.models.models import (
    Obligation, ObligationEditHistory, ObligationType,
    PartyType, RiskLevel, ObligationStatus, Contract
)

# OpenAI APIクライアントの初期化
client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class ObligationService:
    """義務抽出・管理を担当するサービスクラス"""
    
    @staticmethod
    async def extract_obligations_from_contract(
        contract_text: str,
        contract_id: str
    ) -> List[Dict]:
        """
        契約書のテキストから義務を自動抽出
        
        Args:
            contract_text: 契約書の全文テキスト
            contract_id: 契約ID
            
        Returns:
            抽出された義務のリスト
        """
        print(f"🔍 Analyzing contract text: {len(contract_text)} characters")
        if not contract_text or len(contract_text.strip()) < 10:
             print("⚠️ Contract text is empty or too short!")
             return []

        # OpenAI APIを使用して義務を抽出
        system_prompt = """あなたは契約書解析の専門家です。
        契約書から以下の情報を抽出してください：

        1. 義務のタイトル（簡潔に）
        2. 義務のタイプ（payment/renewal/termination/inspection/delivery/report/confidentiality/other）
        3. 期限（具体的な日付があれば）
        4. トリガー条件（「契約開始日から30日」など）
        5. 責任者（client/lawyer/counterparty/both/unknown）
        6. 実行すべきアクション
        7. 必要な証跡（配列）
        8. リスクレベル（high/medium/low）
        9. 根拠条項（条番号と該当箇所の抜粋）
        
        重要: Enum値は必ず以下の小文字の値を使用してください。
        - type: payment, renewal, termination, inspection, delivery, report, confidentiality, other
        - responsible_party: client, lawyer, counterparty, both, unknown
        - risk_level: high, medium, low
        
        以下のJSON形式で出力してください：
        {
            "obligations": [
                {
                    "title": "更新通知期限",
                    "type": "renewal",
                    "due_date": null,
                    "trigger_condition": "契約開始日から30日前",
                    "responsible_party": "client",
                    "action": "書面にて更新の意思を通知する",
                    "evidence_required": ["通知書の写し", "送付証明"],
                    "risk_level": "high",
                    "clause_reference": "第12条第2項「甲は、契約期間満了の30日前までに...」",
                    "confidence": 0.95
                }
            ]
        }
    """

        try:
            # 最新のモデル gpt-4o を使用 (高速・高精度)
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"以下の契約書から義務を抽出してください：\n\n{contract_text[:10000]}"}  # 文字数上限を拡張
                ],
                temperature=0.1,  # より決定論的な出力のため温度を下げる
                response_format={"type": "json_object"}
            )
            
            # レスポンスをパース
            content = response.choices[0].message.content
            if not content:
                 print("⚠️ AI returned empty content")
                 return []
                 
            print(f"🤖 AI Response: {content[:500]}...") # ログ出力拡張
            
            result = json.loads(content)
            obligations = result.get("obligations", [])
            print(f"✅ Extracted {len(obligations)} obligations from AI response")
            
            return obligations
            
        except Exception as e:
            print(f"❌ 義務抽出中のAIエラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    async def create_obligation(
        db: AsyncSession,
        contract_id: str,
        title: str,
        type: str,
        due_date: Optional[datetime],
        trigger_condition: Optional[str],
        responsible_party: str,
        action: str,
        evidence_required: List[str],
        risk_level: str,
        confidence: Optional[float],
        clause_reference: Optional[str],
        notes: Optional[str] = None
    ) -> Obligation:
        """
        新しい義務を作成
        
        Args:
            db: データベースセッション
            (その他のパラメータ)
            
        Returns:
            作成された義務オブジェクト
        """
        # IDを生成（ハッシュベース）
        obligation_id = hashlib.sha256(
            f"{contract_id}:{title}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # 証跡リストをJSON文字列に変換
        evidence_json = json.dumps(evidence_required, ensure_ascii=False)
        
        # Enum変換（エラー時はデフォルト値を使用）
        try:
            ob_type = ObligationType(type.lower())
        except (ValueError, AttributeError):
            ob_type = ObligationType.OTHER
            
        try:
            ob_party = PartyType(responsible_party.lower())
        except (ValueError, AttributeError):
            ob_party = PartyType.UNKNOWN
            
        try:
            ob_risk = RiskLevel(risk_level.lower())
        except (ValueError, AttributeError):
            ob_risk = RiskLevel.LOW

        # Obligationオブジェクトを作成
        obligation = Obligation(
            id=obligation_id,
            contract_id=contract_id,
            title=title,
            type=ob_type,
            due_date=due_date,
            trigger_condition=trigger_condition,
            responsible_party=ob_party,
            action=action,
            evidence_required=evidence_json,
            risk_level=ob_risk,
            confidence=confidence,
            clause_reference=clause_reference,
            status=ObligationStatus.PENDING,
            notes=notes
        )
        
        # データベースに保存
        db.add(obligation)
        await db.commit()
        await db.refresh(obligation)
        
        return obligation
    
    @staticmethod
    async def update_obligation(
        db: AsyncSession,
        obligation_id: str,
        updated_fields: Dict,
        edited_by: str
    ) -> Optional[Obligation]:
        """
        既存の義務を更新し、編集履歴を記録
        
        Args:
            db: データベースセッション
            obligation_id: 義務ID
            updated_fields: 更新するフィールドの辞書
            edited_by: 編集者のウォレットアドレス
            
        Returns:
            更新された義務オブジェクト
        """
        # 既存の義務を取得
        result = await db.execute(
            select(Obligation).where(Obligation.id == obligation_id)
        )
        obligation = result.scalar_one_or_none()
        
        if not obligation:
            return None
        
        # 各フィールドの変更を記録
        for field_name, new_value in updated_fields.items():
            if hasattr(obligation, field_name):
                old_value = getattr(obligation, field_name)
                
                # 値が変更された場合のみ履歴を記録
                if old_value != new_value:
                    # 編集履歴を作成
                    history_id = hashlib.sha256(
                        f"{obligation_id}:{field_name}:{datetime.now().isoformat()}".encode()
                    ).hexdigest()[:16]
                    
                    history = ObligationEditHistory(
                        id=history_id,
                        obligation_id=obligation_id,
                        edited_by=edited_by,
                        field_name=field_name,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None
                    )
                    db.add(history)
                    
                    # 値を更新
                    setattr(obligation, field_name, new_value)
        
        # 更新日時を更新
        obligation.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(obligation)
        
        return obligation
    
    @staticmethod
    async def get_obligations_by_contract(
        db: AsyncSession,
        contract_id: str
    ) -> List[Obligation]:
        """
        特定の契約に紐づく義務を全て取得
        
        Args:
            db: データベースセッション
            contract_id: 契約ID
            
        Returns:
            義務のリスト
        """
        result = await db.execute(
            select(Obligation)
            .where(Obligation.contract_id == contract_id)
            .order_by(Obligation.due_date.asc())  # 期限順にソート
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_obligation_status_from_blockchain(
        db: AsyncSession,
        contract_id: str,
        event_type: str
    ) -> None:
        """
        ブロックチェーンイベントに基づいて義務のステータスを更新
        
        Args:
            db: データベースセッション
            contract_id: 契約ID
            event_type: イベントタイプ（例: "payment_executed", "condition_approved"）
        """
        # 該当する契約の義務を取得
        obligations = await ObligationService.get_obligations_by_contract(db, contract_id)
        
        for obligation in obligations:
            # イベントタイプに応じてステータスを更新
            if event_type == "payment_executed" and obligation.type == ObligationType.PAYMENT:
                # 支払が実行された場合、支払義務を完了にする
                obligation.status = ObligationStatus.COMPLETED
                obligation.completed_at = datetime.now()
                
            elif event_type == "contract_signed":
                # 契約署名時に更新義務などの基準日を設定
                if obligation.trigger_condition and "契約開始日" in obligation.trigger_condition:
                    # トリガー条件をパースして期限を計算（簡易実装）
                    # 例: "契約開始日から30日前" → 30日前の日付を設定
                    pass  # TODO: より詳細な条件パースロジックを実装
        
        await db.commit()
    
    @staticmethod
    async def check_due_soon_obligations(db: AsyncSession) -> List[Obligation]:
        """
        期限が近い義務をチェックし、ステータスを更新
        7日以内に期限が来る義務を DUE_SOON に更新
        
        Args:
            db: データベースセッション
            
        Returns:
            期限間近の義務リスト
        """
        now = datetime.now()
        seven_days_later = now + timedelta(days=7)
        
        # 7日以内に期限が来る義務を取得
        result = await db.execute(
            select(Obligation)
            .where(
                Obligation.due_date.isnot(None),
                Obligation.due_date <= seven_days_later,
                Obligation.due_date > now,
                Obligation.status == ObligationStatus.PENDING
            )
        )
        due_soon_obligations = result.scalars().all()
        
        # ステータスを DUE_SOON に更新
        for obligation in due_soon_obligations:
            obligation.status = ObligationStatus.DUE_SOON
        
        await db.commit()
        
        return due_soon_obligations
    
    @staticmethod
    async def check_overdue_obligations(db: AsyncSession) -> List[Obligation]:
        """
        期限超過の義務をチェックし、ステータスを更新
        
        Args:
            db: データベースセッション
            
        Returns:
            期限超過の義務リスト
        """
        now = datetime.now()
        
        # 期限を過ぎた義務を取得
        result = await db.execute(
            select(Obligation)
            .where(
                Obligation.due_date.isnot(None),
                Obligation.due_date < now,
                Obligation.status.in_([ObligationStatus.PENDING, ObligationStatus.DUE_SOON])
            )
        )
        overdue_obligations = result.scalars().all()
        
        # ステータスを OVERDUE に更新
        for obligation in overdue_obligations:
            obligation.status = ObligationStatus.OVERDUE
        
        await db.commit()
        
        return overdue_obligations


# サービスインスタンスをエクスポート
obligation_service = ObligationService()
