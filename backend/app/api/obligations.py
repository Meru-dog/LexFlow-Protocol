"""
LexFlow Protocol - 義務管理APIエンドポイント (Version 2: F2)

契約上の義務を管理するためのRESTful APIエンドポイント
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.services.obligation_service import obligation_service
from app.models.models import Obligation, ObligationType, PartyType, RiskLevel, ObligationStatus, Contract
from sqlalchemy import select
from app.core.x402 import PaymentVerifier
import os

# ルーター初期化
router = APIRouter(prefix="/obligations", tags=["obligations"])
logger = get_logger(__name__)


# ===== Pydanticスキーマ定義 =====

class ObligationCreate(BaseModel):
    """義務作成時のリクエストボディ"""
    contract_id: str = Field(..., description="契約ID")
    title: str = Field(..., description="義務タイトル")
    type: str = Field(..., description="義務タイプ")
    due_date: Optional[datetime] = Field(None, description="期限日")
    trigger_condition: Optional[str] = Field(None, description="トリガー条件")
    responsible_party: str = Field(..., description="責任者")
    action: str = Field(..., description="実行すべきアクション")
    evidence_required: List[str] = Field(default_factory=list, description="必要な証跡")
    risk_level: str = Field(..., description="リスクレベル")
    confidence: Optional[float] = Field(None, description="AI抽出の確度")
    clause_reference: Optional[str] = Field(None, description="根拠条項")
    notes: Optional[str] = Field(None, description="備考")


class ObligationUpdate(BaseModel):
    """義務更新時のリクエストボディ"""
    title: Optional[str] = None
    type: Optional[str] = None
    due_date: Optional[datetime] = None
    trigger_condition: Optional[str] = None
    responsible_party: Optional[str] = None
    action: Optional[str] = None
    evidence_required: Optional[List[str]] = None
    risk_level: Optional[str] = None
    confidence: Optional[float] = None
    clause_reference: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    edited_by: str = Field(..., description="編集者のウォレットアドレス")


class ObligationResponse(BaseModel):
    """義務レスポンス"""
    id: str
    contract_id: str
    title: str
    type: str
    due_date: Optional[datetime]
    trigger_condition: Optional[str]
    responsible_party: str
    action: str
    evidence_required: List[str]
    risk_level: str
    confidence: Optional[float]
    clause_reference: Optional[str]
    status: str
    completed_at: Optional[datetime]
    completed_by: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
    
    # Pydantic v1のvalidatorを使用 (FastAPIはPydantic v1を使用)
    from pydantic import validator
    
    @validator('evidence_required', pre=True)
    def parse_evidence_required(cls, value):
        """JSON文字列をリストに変換"""
        if isinstance(value, str):
            try:
                import json
                return json.loads(value)
            except Exception as e:
                logger.warning(f"evidence_required の解析に失敗しました: {str(e)}")
                return []
        elif isinstance(value, list):
            return value
        return []


class ObligationExtractRequest(BaseModel):
    """義務抽出リクエスト"""
    contract_id: str = Field(..., description="契約ID")
    contract_text: Optional[str] = Field(None, description="契約書の全文テキスト（省略時は保存されたファイルから読み込み）")


# ===== APIエンドポイント =====

@router.post("/extract", response_model=List[ObligationResponse])
async def extract_obligations(
    request: ObligationExtractRequest,
    req: Request, # ヘッダーにアクセスするためにリクエストオブジェクトを必要とする
    db: AsyncSession = Depends(get_db),
    # F8: x402 Paywall (100 JPYC)
    payment_verified: bool = Depends(PaymentVerifier(amount=100.0))
):
    """
    契約書から義務を自動抽出
    
    OpenAI APIを使用して契約書テキストから義務を抽出し、データベースに保存
    """
    try:
        # テキストが提供されていない場合はファイルから読み込む
        text_to_analyze = request.contract_text
        if not text_to_analyze:
            # 契約情報を取得
            result = await db.execute(select(Contract).where(Contract.id == request.contract_id))
            contract = result.scalar_one_or_none()
            
            if not contract:
                raise HTTPException(status_code=404, detail="契約が見つかりません")
                
            if not contract.file_url:
                raise HTTPException(status_code=400, detail="契約書ファイルが見つかりません")
                
            # ファイルを読み込む
            file_path = contract.file_url
            
            # 先頭の/がある場合は削除（環境によるパス解釈の違いを吸収）
            if file_path.startswith('/uploads/'):
                file_path = file_path[1:]
                
            if not os.path.exists(file_path):
                 # uploadsディレクトリ内を探す（後方互換性）
                 alt_path = os.path.join("uploads", os.path.basename(file_path))
                 if os.path.exists(alt_path):
                     file_path = alt_path
                 else:
                    raise HTTPException(status_code=400, detail=f"契約書ファイルが見つかりません: {file_path}")

            try:
                with open(file_path, "rb") as f:
                    file_content = f.read()
                
                # ファイル形式に応じてテキスト抽出
                from app.services.contract_parser import contract_parser
                # ファイル名を取得（パスから）
                filename = os.path.basename(file_path)
                text_to_analyze = await contract_parser.extract_text_from_file(file_content, filename)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"ファイル読み込みエラー: {str(e)}")

        # AIで義務を抽出
        logger.info(f"🤖 契約書から義務を抽出: {request.contract_id}")
        extracted_obligations = await obligation_service.extract_obligations_from_contract(
            contract_text=text_to_analyze,
            contract_id=request.contract_id
        )
        logger.info(f"✅ AI分析完了。抽出候補数: {len(extracted_obligations)}")
        
        # 抽出された義務をデータベースに保存
        created_obligations = []
        import json
        for i, ob_data in enumerate(extracted_obligations):
            try:
                logger.debug(f"💾 義務を保存: {i+1}/{len(extracted_obligations)}: {ob_data.get('title')}")
                obligation = await obligation_service.create_obligation(
                    db=db,
                    contract_id=request.contract_id,
                    title=ob_data.get("title"),
                    type=ob_data.get("type"),
                    due_date=None,  # 文字列の日付をパースする場合は別途実装
                    trigger_condition=ob_data.get("trigger_condition"),
                    responsible_party=ob_data.get("responsible_party"),
                    action=ob_data.get("action"),
                    evidence_required=ob_data.get("evidence_required", []),
                    risk_level=ob_data.get("risk_level", "low"),
                    confidence=ob_data.get("confidence"),
                    clause_reference=ob_data.get("clause_reference")
                )
                created_obligations.append(obligation)
            except Exception as e:
                logger.error(f"❌ 義務保存失敗: {i+1}: {str(e)}", exc_info=True)
                # 個別保存のエラーは続行する
                continue
                
            created_obligations.append(obligation)

        logger.info(f"✅ {len(created_obligations)} 義務をDBに保存しました")
        return created_obligations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"義務抽出エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"義務抽出エラー: {str(e)}"
        )


@router.post("/", response_model=ObligationResponse, status_code=status.HTTP_201_CREATED)
async def create_obligation(
    obligation_data: ObligationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    新しい義務を作成
    
    手動で義務を追加する場合に使用
    """
    try:
        obligation = await obligation_service.create_obligation(
            db=db,
            contract_id=obligation_data.contract_id,
            title=obligation_data.title,
            type=obligation_data.type,
            due_date=obligation_data.due_date,
            trigger_condition=obligation_data.trigger_condition,
            responsible_party=obligation_data.responsible_party,
            action=obligation_data.action,
            evidence_required=obligation_data.evidence_required,
            risk_level=obligation_data.risk_level,
            confidence=obligation_data.confidence,
            clause_reference=obligation_data.clause_reference,
            notes=obligation_data.notes
        )
        return obligation
    except Exception as e:
        logger.error(f"義務作成エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"義務作成エラー: {str(e)}"
        )


@router.get("/contract/{contract_id}", response_model=List[ObligationResponse])
async def get_obligations_by_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    特定の契約に紐づく義務を全て取得
    
    期限順にソートして返す
    """
    try:
        obligations = await obligation_service.get_obligations_by_contract(
            db=db,
            contract_id=contract_id
        )
        
        # evidence_requiredをJSON文字列からリストに変換
        import json
        for ob in obligations:
            if ob.evidence_required:
                try:
                    ob.evidence_required = json.loads(ob.evidence_required)
                except Exception as e:
                    logger.warning(f"证据を解析できません: {str(e)}")
                    ob.evidence_required = []
            else:
                ob.evidence_required = []
        
        return obligations
    except Exception as e:
        logger.error(f"義務取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"義務取得エラー: {str(e)}"
        )


@router.put("/{obligation_id}", response_model=ObligationResponse)
async def update_obligation(
    obligation_id: str,
    update_data: ObligationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    既存の義務を更新
    
    編集履歴を自動的に記録
    """
    try:
        # 更新するフィールドを辞書に変換
        updated_fields = update_data.model_dump(exclude_unset=True, exclude={"edited_by"})
        
        # evidence_requiredがある場合はJSON文字列に変換
        import json
        if "evidence_required" in updated_fields:
            updated_fields["evidence_required"] = json.dumps(
                updated_fields["evidence_required"],
                ensure_ascii=False
            )
        
        # 義務を更新
        obligation = await obligation_service.update_obligation(
            db=db,
            obligation_id=obligation_id,
            updated_fields=updated_fields,
            edited_by=update_data.edited_by
        )
        
        if not obligation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="義務が見つかりません"
            )
        
        # evidence_requiredをリストに変換
        if obligation.evidence_required:
            try:
                obligation.evidence_required = json.loads(obligation.evidence_required)
            except Exception as e:
                logger.warning(f"证据を解析できません: {str(e)}")
                obligation.evidence_required = []
        else:
            obligation.evidence_required = []
        
        return obligation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"義務更新エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"義務更新エラー: {str(e)}"
        )


@router.post("/{obligation_id}/complete", response_model=ObligationResponse)
async def complete_obligation(
    obligation_id: str,
    completed_by: str,
    db: AsyncSession = Depends(get_db)
):
    """
    義務を完了状態にする
    
    Args:
        obligation_id: 義務ID
        completed_by: 完了者のウォレットアドレス
    """
    try:
        obligation = await obligation_service.update_obligation(
            db=db,
            obligation_id=obligation_id,
            updated_fields={
                "status": ObligationStatus.COMPLETED.value,
                "completed_at": datetime.now(),
                "completed_by": completed_by
            },
            edited_by=completed_by
        )
        
        if not obligation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="義務が見つかりません"
            )
        
        # evidence_requiredをリストに変換
        import json
        if obligation.evidence_required:
            try:
                obligation.evidence_required = json.loads(obligation.evidence_required)
            except Exception as e:
                logger.warning(f"证据を解析できません: {str(e)}")
                obligation.evidence_required = []
        else:
            obligation.evidence_required = []
        
        return obligation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"義務完了エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"義務完了エラー: {str(e)}"
        )


@router.get("/due-soon", response_model=List[ObligationResponse])
async def get_due_soon_obligations(
    db: AsyncSession = Depends(get_db)
):
    """
    期限が近い義務を取得
    
    7日以内に期限が来る義務を返す
    """
    try:
        obligations = await obligation_service.check_due_soon_obligations(db)
        
        # evidence_requiredをリストに変換
        import json
        for ob in obligations:
            if ob.evidence_required:
                try:
                    ob.evidence_required = json.loads(ob.evidence_required)
                except Exception as e:
                    logger.warning(f"证据を解析できません: {str(e)}")
                    ob.evidence_required = []
            else:
                ob.evidence_required = []
        
        return obligations
    except Exception as e:
        logger.error(f"期限間近義務取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"期限間近義務取得エラー: {str(e)}"
        )


@router.get("/overdue", response_model=List[ObligationResponse])
async def get_overdue_obligations(
    db: AsyncSession = Depends(get_db)
):
    """
    期限超過の義務を取得
    """
    try:
        obligations = await obligation_service.check_overdue_obligations(db)
        
        # evidence_requiredをリストに変換
        import json
        for ob in obligations:
            if ob.evidence_required:
                try:
                    ob.evidence_required = json.loads(ob.evidence_required)
                except Exception as e:
                    logger.warning(f"证据を解析できません: {str(e)}")
                    ob.evidence_required = []
            else:
                ob.evidence_required = []
        
        return obligations
    except Exception as e:
        logger.error(f"期限超過義務取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"期限超過義務取得エラー: {str(e)}"
        )
