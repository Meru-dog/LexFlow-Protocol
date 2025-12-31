"""
LexFlow Protocol - Version Service
Contract Version Management and File Handling
"""
import os
import uuid
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.models.models import ContractVersion, VersionStatus, Contract
from app.services.signature_service import signature_service

class VersionService:
    """
    契約書の版管理（バージョン管理）を統括するサービス
    """
    
    async def create_version(
        self,
        db: AsyncSession,
        case_id: str,
        file_content: bytes,
        creator_address: str,
        title: str = "New Version",
        summary: str = None,
        filename: str = "document.pdf"
    ) -> ContractVersion:
        """
        新しい契約版を作成する
        
        1. ファイルハッシュ計算
        2. ファイル保存 (現在の簡易実装は /uploads/versions/)
        3. データベース記録
        """
        # 1. ハッシュ計算
        doc_hash = signature_service.calculate_doc_hash(file_content)
        
        # 2. 最新のバージョン番号を取得
        current_max = await db.execute(
            select(ContractVersion.version)
            .where(ContractVersion.case_id == case_id)
            .order_by(desc(ContractVersion.version))
            .limit(1)
        )
        last_version = current_max.scalar_one_or_none() or 0
        new_version_num = last_version + 1
        
        # 3. ファイル保存
        # 保存先ディレクトリの作成
        upload_dir = "uploads/versions"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        # 拡張子の決定
        print(f"📁 Version file saving: received filename='{filename}'")
        original_ext = os.path.splitext(filename)[1].lower()
        if not original_ext:
            # ファイル名自体が拡張子のみの場合（例: .txt）
            if filename.startswith('.'):
                original_ext = filename.lower()
            else:
                original_ext = ".pdf" # Default
        
        print(f"🔧 Determined extension: '{original_ext}'")
            
        file_name = f"{case_id}_v{new_version_num}_{uuid.uuid4().hex[:8]}{original_ext}"
        file_path = os.path.join(upload_dir, file_name)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        # 4. 前のバージョンがあれば SUPERSEDED に更新
        if last_version > 0:
            # 実際はビジネスロジックにより異なるが、ここでは単純化
            pass

        # 5. レコード作成
        new_version = ContractVersion(
            id=str(uuid.uuid4()),
            case_id=case_id,
            version=new_version_num,
            doc_hash=doc_hash,
            file_url=f"/uploads/versions/{file_name}",
            title=title,
            summary=summary,
            status=VersionStatus.PENDING_SIGNATURE,
            created_by=creator_address
        )
        
        db.add(new_version)
        await db.commit()
        await db.refresh(new_version)
        
        return new_version

    async def get_versions_by_case(
        self,
        db: AsyncSession,
        case_id: str
    ) -> List[ContractVersion]:
        """特定案件の全バージョンを取得"""
        result = await db.execute(
            select(ContractVersion)
            .where(ContractVersion.case_id == case_id)
            .order_by(desc(ContractVersion.version))
        )
        return list(result.scalars().all())

    async def get_version_by_id(
        self,
        db: AsyncSession,
        version_id: str
    ) -> Optional[ContractVersion]:
        """IDでバージョンを取得"""
        result = await db.execute(
            select(ContractVersion).where(ContractVersion.id == version_id)
        )
        return result.scalar_one_or_none()

# インスタンス化
version_service = VersionService()
