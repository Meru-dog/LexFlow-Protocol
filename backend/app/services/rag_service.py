"""
LexFlow Protocol - RAG (Retrieval-Augmented Generation) サービス
契約書のベクトル化、検索、およびコンテキスト抽出を担当
"""
import os
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Any, Optional

from app.core.config import settings

class RAGService:
    """
    RAGサービス
    ChromaDBを使用してドキュメントのインデックス作成と検索を行う
    """
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        # 永続化ストレージのパス設定
        self.persist_directory = os.path.join(os.getcwd(), "chroma_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # ChromaDB クライアントの初期化
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        print(f"📦 RAG サービスの初期化: {self.persist_directory}")

    def _get_vectorstore(self, workspace_id: str):
        """
        ワークスペースごとのベクターストアを取得
        コレクション名は workspace_id をベースにする
        """
        collection_name = f"workspace_{workspace_id.replace('-', '_')}"
        
        return Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    async def index_contract(self, contract_id: str, workspace_id: str, text: str, metadata: Dict[str, Any] = None):
        """
        契約書をチャンク分割してベクトルDBに登録
        """
        if not text or len(text.strip()) < 10:
            print(f"⚠️ {contract_id}: テキストが短すぎます")
            return
            
        print(f"🔍 {contract_id}: ベクトルDBに登録中...")
        
        # テキスト分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
            is_separator_regex=False,
        )
        
        chunks = text_splitter.split_text(text)
        print(f"✂️ {contract_id}: {len(chunks)} チャンクに分割しました")
        
        # メタデータの準備
        final_metadata = {
            "contract_id": contract_id,
            "workspace_id": workspace_id,
        }
        if metadata:
            final_metadata.update(metadata)
            
        # ベクターストアの取得
        vectorstore = self._get_vectorstore(workspace_id)
        
        # 既存の当該コントラクト情報を削除（再インデックス用）
        try:
            vectorstore.delete(where={"contract_id": contract_id})
        except Exception:
            pass # 未登録の場合はエラーになるが無視
            
        # 登録
        vectorstore.add_texts(
            texts=chunks,
            metadatas=[final_metadata] * len(chunks)
        )
        
        print(f"✅ {contract_id}: ベクトルDBに登録しました")

    async def search_relevant_context(self, workspace_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        クエリに関連するコンテキストを検索
        """
        vectorstore = self._get_vectorstore(workspace_id)
        
        results = vectorstore.similarity_search_with_score(query, k=limit)
        
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
            
        return formatted_results

    async def query_with_context(self, workspace_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        RAG検索を実行し、OpenAI APIを使用して質問に対する回答を生成
        
        Returns:
            answer: AIの回答テキスト
            sources: 引用元の契約書情報とチャンク内容のリスト
        """
        from openai import AsyncOpenAI
        
        # 関連コンテキストを検索
        contexts = await self.search_relevant_context(workspace_id, query, limit=limit)
        
        if not contexts:
            return {
                "answer": "申し訳ございませんが、関連する契約書の情報が見つかりませんでした。別の表現で質問してみてください。",
                "sources": []
            }
        
        # コンテキストをプロンプト用にフォーマット
        context_texts = []
        for idx, ctx in enumerate(contexts, 1):
            title = ctx["metadata"].get("title", "不明な契約書")
            content = ctx["content"]
            context_texts.append(f"【契約書 {idx}: {title}】\n{content}")
        
        combined_context = "\n\n".join(context_texts)
        
        # OpenAI APIを呼び出し
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        system_prompt = """あなたは契約書の専門家アシスタントです。以下の契約書の抜粋を参照して、ユーザーの質問に正確に答えてください。

【重要な指示】
- 必ず提供された契約書の内容のみに基づいて回答してください
- 回答の根拠となる契約書名や条項を明記してください
- 不確実な場合や契約書に記載がない場合は、「契約書には明記されていません」と正直に答えてください
- 簡潔で分かりやすい日本語で回答してください
- 箇条書きを使って整理された回答を心がけてください"""

        user_prompt = f"""契約書の抜粋:
{combined_context}

ユーザーの質問: {query}"""

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # コスト効率の良いモデル
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # 一貫性のある回答のため低めに設定
                max_tokens=800
            )
            
            answer = response.choices[0].message.content
            
            # ソース情報を整形
            sources = []
            for ctx in contexts:
                sources.append({
                    "contract_id": ctx["metadata"].get("contract_id"),
                    "title": ctx["metadata"].get("title", "不明な契約書"),
                    "excerpt": ctx["content"][:200] + "..." if len(ctx["content"]) > 200 else ctx["content"],
                    "relevance_score": 1.0 / (1.0 + ctx["score"])  # スコアを0-1の範囲に正規化
                })
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            print(f"❌ OpenAI API Error: {e}")
            return {
                "answer": f"申し訳ございません。回答の生成中にエラーが発生しました: {str(e)}",
                "sources": [
                    {
                        "contract_id": ctx["metadata"].get("contract_id"),
                        "title": ctx["metadata"].get("title", "不明な契約書"),
                        "excerpt": ctx["content"][:200] + "...",
                        "relevance_score": 1.0 / (1.0 + ctx["score"])
                    }
                    for ctx in contexts
                ]
            }

# シングルトンインスタンス
rag_service = RAGService()
