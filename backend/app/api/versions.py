"""
LexFlow Protocol - Version API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.services.version_service import version_service
from app.models.models import VersionStatus

router = APIRouter(prefix="/versions", tags=["versions"])

class VersionResponse(BaseModel):
    id: str
    case_id: str
    version: int
    doc_hash: str
    file_url: str
    title: Optional[str]
    summary: Optional[str]
    status: VersionStatus
    created_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True

@router.post("", response_model=VersionResponse)
async def create_version(
    case_id: str = Form(...),
    title: str = Form("New Version"),
    summary: Optional[str] = Form(None),
    creator_address: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    新しい契約版をアップロードして作成する
    """
    try:
        content = await file.read()
        version = await version_service.create_version(
            db=db,
            case_id=case_id,
            file_content=content,
            creator_address=creator_address,
            title=title,
            summary=summary,
            filename=file.filename
        )
        return version
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create version: {str(e)}"
        )

@router.get("/case/{case_id}", response_model=List[VersionResponse])
async def list_versions(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    案件に紐づくすべての版を取得する
    """
    return await version_service.get_versions_by_case(db, case_id)
