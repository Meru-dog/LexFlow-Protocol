"""
LexFlow Protocol - Redline API
契約書の差分解析APIエンドポイント
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from datetime import datetime
import os

from app.core.database import get_db
from app.services.redline_service import redline_service, RedlineResult, ChangeItem, RiskAssessment
from app.services.version_service import version_service

router = APIRouter(prefix="/redline", tags=["redline"])


class RedlineCompareRequest(BaseModel):
    """差分比較リクエスト"""
    old_version_id: str = Field(description="比較元バージョンID")
    new_version_id: str = Field(description="比較先バージョンID")


class ChangeItemResponse(BaseModel):
    """変更箇所レスポンス"""
    change_type: str
    location: str
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    risk_level: str
    risk_reason: Optional[str] = None
    recommendation: Optional[str] = None


class RiskAssessmentResponse(BaseModel):
    """リスク評価レスポンス"""
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    overall_risk: str
    summary: str


class RedlineCompareResponse(BaseModel):
    """差分比較レスポンス"""
    old_version_id: str
    new_version_id: str
    changes: List[ChangeItemResponse]
    summary: str
    risk_assessment: RiskAssessmentResponse
    recommendations: List[str]
    diff_html: str


@router.post("/compare", response_model=RedlineCompareResponse)
async def compare_versions(
    request: RedlineCompareRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    2つのバージョンを比較し、差分解析とAIリスク評価を返す
    """
    # 1. バージョン情報の取得
    old_version = await version_service.get_version_by_id(db, request.old_version_id)
    if not old_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Old version not found: {request.old_version_id}"
        )
    
    new_version = await version_service.get_version_by_id(db, request.new_version_id)
    if not new_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"New version not found: {request.new_version_id}"
        )
    
    # 2. 同じ案件のバージョンであることを確認
    if old_version.case_id != new_version.case_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare versions from different cases"
        )
    
    # 3. 同じバージョンの比較は無効
    if request.old_version_id == request.new_version_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare a version with itself"
        )
    
    # 4. PDFファイルの読み込み
    # file_url は /uploads/versions/xxx.pdf 形式
    old_file_path = old_version.file_url.lstrip('/')
    new_file_path = new_version.file_url.lstrip('/')
    
    if not os.path.exists(old_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Old version PDF file not found: {old_file_path}"
        )
    
    if not os.path.exists(new_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"New version PDF file not found: {new_file_path}"
        )
    
    with open(old_file_path, "rb") as f:
        old_file_content = f.read()
    
    with open(new_file_path, "rb") as f:
        new_file_content = f.read()
    
    # 5. 差分解析の実行
    print(f"🔄 Comparing versions: {old_version.version} -> {new_version.version}")
    result = await redline_service.compare_versions(
        old_file_content=old_file_content,
        new_file_content=new_file_content,
        old_version_id=request.old_version_id,
        new_version_id=request.new_version_id,
        old_filename=os.path.basename(old_file_path),
        new_filename=os.path.basename(new_file_path)
    )
    
    # 6. レスポンスの構築
    return RedlineCompareResponse(
        old_version_id=result.old_version_id,
        new_version_id=result.new_version_id,
        changes=[
            ChangeItemResponse(
                change_type=c.change_type,
                location=c.location,
                old_text=c.old_text,
                new_text=c.new_text,
                risk_level=c.risk_level,
                risk_reason=c.risk_reason,
                recommendation=c.recommendation
            )
            for c in result.changes
        ],
        summary=result.summary,
        risk_assessment=RiskAssessmentResponse(
            high_risk_count=result.risk_assessment.high_risk_count,
            medium_risk_count=result.risk_assessment.medium_risk_count,
            low_risk_count=result.risk_assessment.low_risk_count,
            overall_risk=result.risk_assessment.overall_risk,
            summary=result.risk_assessment.summary
        ),
        recommendations=result.recommendations,
        diff_html=result.diff_html
    )


@router.get("/versions/{case_id}")
async def get_comparable_versions(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    案件の比較可能なバージョン一覧を取得
    """
    versions = await version_service.get_versions_by_case(db, case_id)
    
    if len(versions) < 2:
        return {
            "message": "比較には2つ以上のバージョンが必要です",
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "title": v.title,
                    "created_at": v.created_at.isoformat() if v.created_at else None
                }
                for v in versions
            ]
        }
    
    return {
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "title": v.title,
                "created_at": v.created_at.isoformat() if v.created_at else None
            }
            for v in versions
        ]
    }
