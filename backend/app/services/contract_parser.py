"""
LexFlow Protocol - 契約書解析サービス
LangGraphとOpenAIを使用したAI搭載の契約書分析
"""
from typing import Dict, Any, List, Optional  # 型ヒント用
from langchain_openai import ChatOpenAI  # OpenAI ChatGPTインターフェース
from langchain_core.prompts import ChatPromptTemplate  # プロンプトテンプレート
from langchain_core.output_parsers import PydanticOutputParser  # 出力パーサー
from pydantic import BaseModel, Field  # Pydanticモデル
import json  # JSON処理
from pypdf import PdfReader  # PDF読み込み
import io  # バイトストリーム処理
import hashlib  # ハッシュ生成

from app.core.config import settings  # 設定のインポート


class ExtractedClause(BaseModel):
    """
    抽出された条項のモデル
    契約書から抽出された個々の条項を表現する
    """
    clause_id: str = Field(default="unknown", description="条項の一意識別子")  # 条項ID
    clause_type: str = Field(default="general", description="種類: payment（支払）, milestone（マイルストーン）, obligation（義務）, deadline（期限）")
    title: str = Field(default="Untitled Clause", description="条項の簡潔なタイトル")  # 条項タイトル
    description: str = Field(default="", description="条項の完全な説明")  # 詳細説明
    amount: Optional[float] = Field(default=0.0, description="支払金額（該当する場合、日本円）")  # 金額
    deadline: Optional[str] = Field(default=None, description="期限（該当する場合、ISO形式）")  # 期限
    parties_involved: List[str] = Field(default=[], description="この条項に関わる当事者")  # 関係者
    is_payment_condition: bool = Field(default=False, description="支払トリガーとなるかどうか")  # 支払条件フラグ


class ParsedContract(BaseModel):
    """
    解析された契約書のモデル
    契約書全体の構造化データを表現する
    """
    title: str = Field(default="Untitled Contract", description="契約書タイトル")  # 契約タイトル
    parties: List[str] = Field(default=[], description="契約のすべての当事者")  # 当事者リスト
    effective_date: Optional[str] = Field(default=None, description="契約発効日")  # 発効日
    clauses: List[ExtractedClause] = Field(default=[], description="抽出された条項のリスト")  # 条項リスト
    total_value: float = Field(default=0.0, description="契約の総額（日本円）")  # 契約総額
    summary: str = Field(default="", description="契約の簡潔な要約")  # 要約
    payment_conditions: List[Dict[str, Any]] = Field(
        default=[], 
        description="支払をトリガーする条件"
    )  # 支払条件リスト


class ContractParserService:
    """
    契約書解析サービスクラス
    AIを使用してPDF契約書を解析し、構造化データを抽出する
    """
    
    def __init__(self):
        """
        サービスの初期化
        OpenAI GPT-4モデルとPydanticパーサーを設定
        """
        # GPT-4 Turboモデルを使用（高精度な契約書解析のため）
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",  # 使用するモデル
            temperature=0,  # 決定論的な出力（創造性を抑える）
            api_key=settings.OPENAI_API_KEY,  # APIキー
        )
        # Pydanticモデルへの出力パーサー
        self.parser = PydanticOutputParser(pydantic_object=ParsedContract)
    
    async def extract_pdf_text(self, pdf_content: bytes) -> str:
        """
        PDFファイルからテキストを抽出
        """
        # バイトストリームからPDFを読み込み
        reader = PdfReader(io.BytesIO(pdf_content))
        text = ""
        # 全ページのテキストを結合
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    async def extract_text_from_file(self, content: bytes, filename: str) -> str:
        """
        ファイル形式に応じてテキストを抽出
        Support: .pdf, .txt, .md
        """
        lower_name = filename.lower()
        
        if lower_name.endswith('.pdf'):
            return await self.extract_pdf_text(content)
        
        # Text based formats
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to other encodings if needed, or try ignore
            return content.decode('utf-8', errors='ignore')
    
    def compute_hash(self, content: bytes) -> str:
        """
        コンテンツのSHA256ハッシュを計算
        ファイルの整合性検証に使用
        
        Args:
            content: ハッシュ化するバイナリデータ
            
        Returns:
            0xプレフィックス付きの16進数ハッシュ文字列
        """
        return "0x" + hashlib.sha256(content).hexdigest()
    
    async def parse_contract(self, file_content: bytes, filename: str = "contract.pdf") -> ParsedContract:
        """
        契約書ファイルを解析して構造化データを抽出
        
        Args:
            file_content: ファイルのバイナリデータ
            filename: ファイル名（拡張子判定用）
            
        Returns:
            ParsedContract: 解析された契約書データ
        """
        
        # ファイルからテキストを抽出
        print(f"📄 Extracting text from file: {filename} ({len(file_content)} bytes)...")
        contract_text = await self.extract_text_from_file(file_content, filename)
        print(f"📖 Extracted {len(contract_text)} characters")
        
        # 契約書解析用のプロンプトを作成
        # システムプロンプトで役割と出力形式を定義
        prompt = ChatPromptTemplate.from_messages([
            ("system", """あなたは契約書分析に特化した法務AIアシスタントです。
            契約書テキストから構造化された情報を抽出することが任務です。

            以下の義務を必ず守ってください：
            1. 契約書の要約 (summary) を必ず作成してください。これは契約の全体像（目的、主要なマイルストーン、総額、期限）を2-3文で説明するものである必要があります。
            2. 関係するすべての当事者 (parties) を特定してください。
            3. 支払条件 (payment_conditions) と金額を抽出してください。
            4. マイルストーンと期限を発見してください。
            5. 義務と成果物を明確にしてください。

            金額（日本円に変換）と日付（ISO形式を使用）を正確に記載してください。
            契約書の金額は通常、日本円（円またはJPY）で記載されています。

            {format_instructions}"""),
            ("human", """以下の契約書を分析し、関連するすべての情報を抽出してください：

            ---契約書テキスト---
            {contract_text}
            ---契約書終了---

            すべての条項、特に支払、マイルストーン、条件に関連するものを抽出してください。""")
        ])
        
        # プロンプトをフォーマット
        formatted_prompt = prompt.format_messages(
            format_instructions=self.parser.get_format_instructions(),  # 出力形式の指示
            contract_text=contract_text[:15000]  # テキスト長を制限（トークン制限対策）
        )
        
        # AIからの応答を取得
        print("☁️ Sending request to OpenAI API...")
        try:
            response = await self.llm.ainvoke(formatted_prompt)
            print("📩 Received response from OpenAI API")
        except Exception as api_error:
            print(f"❌ OpenAI API call failed: {api_error}")
            raise api_error
        
        # 応答をPydanticモデルにパース
        try:
            parsed = self.parser.parse(response.content)
        except Exception as e:
            print(f"⚠️ AI parsing failed: {e}")
            # 解析失敗時のフォールバック
            parsed = ParsedContract(
                title="Untitled Contract (Parsing Failed)",
                summary="AIによる詳細な解析に失敗しました。手動で内容を確認してください。"
            )
        
        # 支払条件を抽出してリスト化
        parsed.payment_conditions = [
            {
                "clause_id": clause.clause_id,  # 条項ID
                "description": clause.description,  # 説明
                "amount": clause.amount,  # 金額
                "deadline": clause.deadline,  # 期限
                "type": clause.clause_type,  # 種類
            }
            for clause in parsed.clauses
            if clause.is_payment_condition and clause.amount  # 支払条件かつ金額があるもの
        ]
        
        return parsed
    
    async def generate_condition_schema(
        self, 
        parsed_contract: ParsedContract
    ) -> List[Dict[str, Any]]:
        """
        スマートコントラクト用の条件スキーマを生成
        解析された契約書からブロックチェーン実行可能な形式に変換
        
        Args:
            parsed_contract: 解析された契約書データ
            
        Returns:
            スマートコントラクト用の条件リスト
        """
        conditions = []
        
        # 各支払条件を処理
        for i, payment in enumerate(parsed_contract.payment_conditions):
            conditions.append({
                "condition_id": f"cond_{i+1}",  # 条件ID
                "clause_reference": payment["clause_id"],  # 元の条項への参照
                "description": payment["description"],  # 説明
                "amount": payment["amount"],  # 金額
                "deadline": payment["deadline"],  # 期限
                "type": payment["type"],  # 種類
                "status": "pending",  # 初期状態は「保留中」
            })
        
        return conditions


# シングルトンインスタンス
# アプリケーション全体で同じインスタンスを使用
contract_parser = ContractParserService()
