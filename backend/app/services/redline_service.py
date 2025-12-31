"""
LexFlow Protocol - Redline Service
契約書の差分解析とAIリスク評価を実行するサービス
"""
from typing import List, Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import difflib
import json
import os
import re

from app.core.config import settings
from app.services.contract_parser import contract_parser


class ChangeItem(BaseModel):
    """個々の変更箇所を表すモデル"""
    change_type: str = Field(description="変更タイプ: add, delete, modify")
    location: str = Field(description="変更箇所の位置情報")
    old_text: Optional[str] = Field(default=None, description="変更前のテキスト")
    new_text: Optional[str] = Field(default=None, description="変更後のテキスト")
    risk_level: str = Field(default="low", description="リスクレベル: high, medium, low")
    risk_reason: Optional[str] = Field(default=None, description="リスク判定の理由")
    recommendation: Optional[str] = Field(default=None, description="AIからの提案")


class RiskAssessment(BaseModel):
    """リスク評価の全体サマリー"""
    high_risk_count: int = Field(default=0, description="高リスク変更の件数")
    medium_risk_count: int = Field(default=0, description="中リスク変更の件数")
    low_risk_count: int = Field(default=0, description="低リスク変更の件数")
    overall_risk: str = Field(default="low", description="全体リスクレベル: high, medium, low")
    summary: str = Field(default="", description="リスク評価のサマリー")


class RedlineResult(BaseModel):
    """差分解析の全体結果"""
    old_version_id: str
    new_version_id: str
    changes: List[ChangeItem] = Field(default=[])
    summary: str = Field(default="", description="AI生成の変更要約")
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    recommendations: List[str] = Field(default=[], description="AIからの全体的な提案")
    diff_html: str = Field(default="", description="HTML形式の差分表示")


class RedlineService:
    """
    契約書の差分解析とAIリスク評価を行うサービス
    """
    
    def __init__(self):
        """サービスの初期化"""
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            api_key=settings.OPENAI_API_KEY,
        )
    
    def compute_text_diff(self, old_text: str, new_text: str) -> List[Dict[str, Any]]:
        """
        2つのテキスト間の差分を計算し、ブロック単位でまとめる
        """
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        blocks = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
                
            block = {
                'type': tag, # 'replace', 'delete', 'insert'
                'old_text': "\n".join(old_lines[i1:i2]) if tag in ['replace', 'delete'] else None,
                'new_text': "\n".join(new_lines[j1:j2]) if tag in ['replace', 'insert'] else None,
                'location': f"L{i1+1}-{i2}" if i1 != i2 else f"L{j1+1}-{j2}"
            }
            blocks.append(block)
        
        return blocks
    
    def generate_diff_html(self, old_text: str, new_text: str) -> str:
        """
        HTML形式の差分表示を生成し、ナビゲーションマーカーを番号バッジに置き換える
        """
        differ = difflib.HtmlDiff(wrapcolumn=80)
        html = differ.make_table(
            old_text.splitlines(),
            new_text.splitlines(),
            fromdesc='旧バージョン',
            todesc='新バージョン',
            context=True,
            numlines=3
        )
        
        # <tr>単位で分割して処理
        rows = re.findall(r'<tr.*?>.*?</tr>', html, re.DOTALL)
        count = 1
        processed_rows = []
        
        for row in rows:
            # 変更が含まれる行（diff_add, diff_sub, diff_chg）かどうかを確認
            is_change_row = 'class="diff_add"' in row or 'class="diff_sub"' in row or 'class="diff_chg"' in row
            
            # ナビゲーションリンク (f, n, p, t) を探す
            if is_change_row and re.search(r'>(f|n|p|t)</a>', row):
                # 変更行のマーカーを番号付きバッジに置換
                badge_html = f'><span style="background-color: #4f46e5; color: white; border-radius: 50%; width: 18px; height: 18px; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; margin: 0 2px;">{count}</span></a>'
                row = re.sub(r'>(f|n|p|t)</a>', badge_html, row)
                count += 1
            elif re.search(r'>(f|n|p|t)</a>', row):
                # 変更ではない行にあるナビゲーションマーカー（先頭ジャンプなど）は非表示にする
                row = re.sub(r'>(f|n|p|t)</a>', '></a>', row)
                
            processed_rows.append(row)
            
        # 再構築（theadやcolgroupなどは維持し、tbodyの中身を差し替え）
        # 面倒なので全置換された行リストで再結合するが、make_tableの返り値全体に対して行う
        # findallで取得した全trを順番に置換していく
        result_html = html
        for original, processed in zip(rows, processed_rows):
            if original != processed:
                result_html = result_html.replace(original, processed, 1)
                
        return result_html
    
    async def analyze_changes_with_ai(
        self, 
        old_text: str, 
        new_text: str,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        変更箇所をAIで解析し、リスク評価を行う
        
        Args:
            old_text: 旧バージョンの全文
            new_text: 新バージョンの全文
            changes: 差分情報のリスト
            
        Returns:
            AI解析結果（リスク評価、提案など）
        """
        # 変更内容を文字列化
        changes_summary = "\n".join([
            f"- {'削除' if c['type'] == 'delete' else '追加'}: {c.get('old_text') or c.get('new_text')}"
            for c in changes[:50]  # 最大50件に制限
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """あなたは法務専門のAIアシスタントです。契約書の変更点を分析し、リスク評価を行います。
            
            以下の形式でJSON形式の出力を生成してください：
            
            {{
            "summary": "変更内容の要約（日本語、2-3文）",
            "changes": [
                {{
                    "index": 1,
                    "description": "変更内容の説明",
                    "change_type": "modify/add/delete",
                    "risk_level": "high/medium/low",
                    "risk_reason": "リスク判定の理由",
                    "recommendation": "対応の提案"
                }}
            ],
            "overall_risk": "high/medium/low",
            "overall_summary": "全体的なリスク評価のサマリー",
            "recommendations": ["提案1", "提案2"]
            }}

            リスク判定基準：
            - high（高）: 支払条件、責任制限、契約解除、損害賠償に関する重大な変更
            - medium（中）: 期限、通知義務、秘密保持に関する変更
            - low（低）: 軽微な文言修正、形式的な変更"""),
            ("human", """以下の契約書の変更点を分析してください。
            
            【変更箇所一覧】
            {changes}
            
            【旧バージョン全文（抜粋）】
            {old_text}

            【新バージョン全文（抜粋）】
            {new_text}

            上記の変更について、法務観点からのリスク評価と提案をJSON形式で出力してください。""")
        ])
        
        formatted_prompt = prompt.format_messages(
            changes=changes_summary,
            old_text=old_text[:5000],  # 文字数制限
            new_text=new_text[:5000]
        )
        
        try:
            response = await self.llm.ainvoke(formatted_prompt)
            content = response.content
            
            # JSON部分を抽出
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content)
            return result
            
        except Exception as e:
            print(f"❌ AI analysis failed: {e}")
            return {
                "summary": "AI解析に失敗しました。手動で確認してください。",
                "changes": [],
                "overall_risk": "medium",
                "overall_summary": "AI解析エラー",
                "recommendations": ["手動での確認を推奨します"]
            }
    
    async def compare_versions(
        self,
        old_file_content: bytes,
        new_file_content: bytes,
        old_version_id: str,
        new_version_id: str,
        old_filename: str = "old_document",
        new_filename: str = "new_document"
    ) -> RedlineResult:
        """
        2つのバージョンを比較し、差分とAI分析を返す
        """
        # 1. ファイルからテキスト抽出
        print(f"📄 Extracting text from old version ({old_filename})...")
        old_text = await contract_parser.extract_text_from_file(old_file_content, old_filename)
        
        print(f"📄 Extracting text from new version ({new_filename})...")
        new_text = await contract_parser.extract_text_from_file(new_file_content, new_filename)
        
        # 2. 差分計算
        print(f"🔍 Computing differences...")
        raw_changes = self.compute_text_diff(old_text, new_text)
        
        # 3. HTML形式の差分生成
        diff_html = self.generate_diff_html(old_text, new_text)
        
        # 4. AI解析
        print(f"🤖 Analyzing changes with AI...")
        ai_analysis = await self.analyze_changes_with_ai(old_text, new_text, raw_changes)
        
        # 5. 結果の構築
        changes = []
        ai_changes = ai_analysis.get("changes", [])
        
        # インデックスに基づいて整理
        for i, ai_change in enumerate(ai_changes):
            idx = ai_change.get("index", i + 1)
            changes.append(ChangeItem(
                change_type=ai_change.get("change_type", "modify"),
                location=f"変更箇所 {idx}",
                old_text=None,
                new_text=None,
                risk_level=ai_change.get("risk_level", "low"),
                risk_reason=ai_change.get("risk_reason", ""),
                recommendation=ai_change.get("recommendation", "")
            ))
        
        # リスクカウント
        high_count = sum(1 for c in changes if c.risk_level == "high")
        medium_count = sum(1 for c in changes if c.risk_level == "medium")
        low_count = sum(1 for c in changes if c.risk_level == "low")
        
        risk_assessment = RiskAssessment(
            high_risk_count=high_count,
            medium_risk_count=medium_count,
            low_risk_count=low_count,
            overall_risk=ai_analysis.get("overall_risk", "low"),
            summary=ai_analysis.get("overall_summary", "")
        )
        
        result = RedlineResult(
            old_version_id=old_version_id,
            new_version_id=new_version_id,
            changes=changes,
            summary=ai_analysis.get("summary", ""),
            risk_assessment=risk_assessment,
            recommendations=ai_analysis.get("recommendations", []),
            diff_html=diff_html
        )
        
        return result


# シングルトンインスタンス
redline_service = RedlineService()
