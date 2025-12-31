"""
LexFlow Protocol - Signature API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from app.core.database import get_db
from app.services.signature_service import signature_service
from app.services.version_service import version_service
from app.models.models import Signature, VersionStatus

router = APIRouter(prefix="/signatures", tags=["signatures"])

class SignatureCreate(BaseModel):
    version_id: str
    signer: str
    role: str
    signature: str # Full hex signature
    timestamp: int

class SignatureResponse(BaseModel):
    id: str
    signer: str
    role: str
    doc_hash: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.post("", response_model=SignatureResponse)
async def submit_signature(
    data: SignatureCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    版に対するEIP-712署名を提出し、検証して保存する
    """
    # 1. バージョン情報の取得
    version = await version_service.get_version_by_id(db, data.version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # 2. 署名の検証
    is_valid, error_msg, recovered_addr = signature_service.verify_eip712_signature(
        signer_address=data.signer,
        signature=data.signature,
        case_id=version.case_id,
        version_num=version.version,
        doc_hash=version.doc_hash,
        timestamp=data.timestamp
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Invalid signature",
                "message": error_msg,
                "recovered": recovered_addr,
                "expected": data.signer
            }
        )
    
    # 3. 署名の分割 (r, s, v)
    try:
        r, s, v = signature_service.split_signature(data.signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature format error: {str(e)}")
    
    # 4. データベースへの保存
    new_sig = Signature(
        id=str(uuid.uuid4()),
        version_id=version.id,
        case_id=version.case_id,
        version=version.version,
        doc_hash=version.doc_hash,
        signer=data.signer,
        role=data.role,
        signature_r=r,
        signature_s=s,
        signature_v=v,
        timestamp=data.timestamp
    )
    
    db.add(new_sig)
    
    # ステータスを SIGNED に更新（ビジネスロジックにより調整）
    version.status = VersionStatus.SIGNED
    
    await db.commit()
    await db.refresh(new_sig)
    
    return new_sig

@router.get("/version/{version_id}", response_model=List[SignatureResponse])
async def list_signatures(
    version_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    版に紐づくすべての署名を取得する
    """
    from sqlalchemy import select
    result = await db.execute(
        select(Signature).where(Signature.version_id == version_id)
    )
    return list(result.scalars().all())
