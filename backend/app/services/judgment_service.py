"""
LexFlow Protocol - 判定サービス
AI搭載のエビデンス評価による条件検証
"""
from typing import Dict, Any, Optional  # 型ヒント用
from langchain_openai import ChatOpenAI  # OpenAI ChatGPTインターフェース
from langchain_core.prompts import ChatPromptTemplate  # プロンプトテンプレート（langchain_coreから）
from pydantic import BaseModel, Field  # Pydanticモデル
from datetime import datetime  # 日時処理
import uuid  # 一意ID生成
import json  # JSON処理

from app.core.config import settings  # 設定のインポート


class JudgmentResult(BaseModel):
    """
    AI判定結果のモデル
    エビデンス評価の結果を構造化して保持
    """
    result: str = Field(description="判定結果: 'approved'（承認）または 'rejected'（却下）")
    confidence: float = Field(description="信頼度スコア（0〜1）")
    reason: str = Field(description="判定の詳細な理由説明")
    key_factors: list[str] = Field(description="判定に影響を与えた主要因のリスト")


class JudgmentService:
    """
    AI搭載のエビデンス判定サービス
    条件達成に対するエビデンスを評価し、承認/却下を判定する
    """
    
    def __init__(self):
        """
        サービスの初期化
        GPT-4 Turboモデルを設定
        """
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",  # 高精度判定のためGPT-4を使用
            temperature=0,  # 決定論的な出力（一貫性重視）
            api_key=settings.OPENAI_API_KEY,  # APIキー
        )
    
    async def evaluate_evidence(
        self,
        condition_description: str,
        condition_amount: float,
        evidence_text: Optional[str] = None,
        evidence_url: Optional[str] = None,
    ) -> JudgmentResult:
        """
        AIを使用してエビデンスを条件に対して評価
        
        引数:
            condition_description: 達成すべき条件の説明
            condition_amount: 条件に関連する支払金額
            evidence_text: テキスト形式のエビデンス
            evidence_url: エビデンス文書へのURL
            
        戻り値:
            JudgmentResult: 承認判定と理由を含む結果オブジェクト
        """
        
        # エビデンス内容を準備
        evidence_content = evidence_text or f"エビデンスURL: {evidence_url}"
        
        # 判定用のプロンプトを作成
        prompt = ChatPromptTemplate.from_messages([
            ("system", """あなたは契約条件の履行評価に特化した法務AIアシスタントです。
            提供されたエビデンスが指定された条件を満たしているかどうかを客観的に評価することが任務です。

            以下のフィールドを含む有効なJSON形式で回答してください：
            - result: "approved"（承認）または "rejected"（却下）
            - confidence: 0〜1の間の数値
            - reason: 詳細な説明文字列
            - key_factors: 判定に影響を与えた主要ポイントの配列

           徹底的かつ公正に判断してください。以下を考慮してください：
            1. エビデンスは条件を直接的に証明していますか？
            2. エビデンスは本物で検証可能ですか？
            3. 不足点や矛盾点はありませんか？
            4. エビデンスに基づいて条件が明確に達成されていますか？

            エビデンスが不十分または不明確な場合は、却下寄りの判定を行い、不足している内容を説明してください。"""),
            ("human", """以下を評価してください：

            **達成すべき条件:**
            {condition_description}

            **関連する支払金額:**
            {amount} JPY

            **提供されたエビデンス:**
            {evidence}

            エビデンスを分析し、条件が達成されているかどうかを判定してください。JSON形式で判定結果を提供してください。""")
        ])
        
        # プロンプトをフォーマットしてLLMに送信
        messages = prompt.format_messages(
            condition_description=condition_description,  # 条件説明
            amount=condition_amount,  # 金額
            evidence=evidence_content  # エビデンス
        )
        
        # AIからの応答を取得
        response = await self.llm.ainvoke(messages)
        
        # JSON応答をパース
        try:
            result_dict = json.loads(response.content)
            # JudgmentResultオブジェクトを作成（reasonは文字列として保存）
            return JudgmentResult(
                result=result_dict.get("result", "rejected"),
                confidence=float(result_dict.get("confidence", 0.5)),
                reason=result_dict.get("reason", "判定理由を取得できませんでした"),
                key_factors=result_dict.get("key_factors", [])
            )
        except (json.JSONDecodeError, Exception) as e:
            # パース失敗時のフォールバック処理
            print(f"Failed to parse AI response: {e}")
            print(f"Response content: {response.content}")
            content = response.content.lower()
            is_approved = "approved" in content and "rejected" not in content
            return JudgmentResult(
                result="approved" if is_approved else "rejected",
                confidence=0.3,  # フォールバック時は低い信頼度
                reason=f"AI応答の解析に失敗しました。応答内容: {response.content[:300]}",
                key_factors=["AIパースフォールバック"]
            )
    
    def generate_judgment_id(self) -> str:
        """
        一意の判定IDを生成
        
        戻り値:
            jdg_プレフィックス付きのUUID文字列
        """
        return f"jdg_{uuid.uuid4().hex[:12]}"
    
    async def get_judgment_summary(
        self,
        condition_id: str,
        judgment_result: JudgmentResult,
    ) -> Dict[str, Any]:
        """
        判定のサマリーオブジェクトを作成
        データベース保存やAPI応答用の構造化データ
        
        引数:
            condition_id: 条件ID
            judgment_result: AI判定結果
            
        戻り値:
            判定サマリーの辞書
        """
        return {
            "judgment_id": self.generate_judgment_id(),  # 判定ID
            "condition_id": condition_id,  # 条件ID
            "ai_result": judgment_result.result,  # AI判定結果
            "ai_confidence": judgment_result.confidence,  # 信頼度
            "ai_reason": judgment_result.reason,  # 理由
            "key_factors": judgment_result.key_factors,  # 主要因
            "judged_at": datetime.utcnow().isoformat(),  # 判定日時
            "status": "awaiting_lawyer_approval",  # 状態: 弁護士承認待ち
        }


# シングルトンインスタンス
# アプリケーション全体で同じインスタンスを使用
judgment_service = JudgmentService()
