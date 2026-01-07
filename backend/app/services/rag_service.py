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

    async def query_with_context(self, workspace_id: str, query: str) -> Dict[str, Any]:
        """
        コンテキストを検索し、それに基づいた回答を生成するための準備
        （実際のLLM呼び出しは judgment_service 等のプロンプトで利用することを想定）
        """
        contexts = await self.search_relevant_context(workspace_id, query)
        combined_context = "\n\n".join([c["content"] for c in contexts])
        
        return {
            "query": query,
            "context": combined_context,
            "source_documents": [c["metadata"].get("contract_id") for c in contexts]
        }

# シングルトンインスタンス
rag_service = RAGService()
