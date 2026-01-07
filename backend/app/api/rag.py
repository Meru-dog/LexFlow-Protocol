"""
LexFlow Protocol - RAG API Routes
契約書横断検索およびAI問合せ用エンドポイント
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.services.rag_service import rag_service
from app.api.auth import get_current_user_id

router = APIRouter(prefix="/rag", tags=["RAG"])

class SearchQuery(BaseModel):
    query: str
    workspace_id: str
    limit: Optional[int] = 5

class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float

class QueryResponse(BaseModel):
    query: str
    context: str
    source_documents: List[str]

@router.post("/search", response_model=List[SearchResult])
async def search_contracts(
    search_query: SearchQuery,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    指定されたワークスペース内の契約書から関連箇所を検索
    """
    try:
        results = await rag_service.search_relevant_context(
            workspace_id=search_query.workspace_id,
            query=search_query.query,
            limit=search_query.limit
        )
        return results
    except Exception as e:
        print(f"❌ RAG 検索エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResponse)
async def query_with_context(
    search_query: SearchQuery,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    関連するコンテキストを抽出し、回答生成のための情報を返す
    """
    try:
        result = await rag_service.query_with_context(
            workspace_id=search_query.workspace_id,
            query=search_query.query
        )
        return result
    except Exception as e:
        print(f"❌ RAG クエリエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))
