"""
LexFlow Protocol - Judgment API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.models import Condition, Judgment, Transaction, ConditionStatus
from app.schemas.schemas import (
    EvidenceSubmit, JudgmentResponse, ApprovalRequest, TransactionResponse
)
from app.services.judgment_service import judgment_service
from app.services.blockchain_service import blockchain_service

# APIルーター
router = APIRouter(prefix="/judgments", tags=["Judgments"])

# 条項の証拠を提出
@router.post("/conditions/{condition_id}/evidence", response_model=JudgmentResponse)
async def submit_evidence(
    condition_id: str,
    evidence: EvidenceSubmit,
    db: AsyncSession = Depends(get_db),
):
    """
    条項の証拠を提出してAI判断を実行
    
    - AI評価
    - AI評価結果を返す
    - 条項の最終実行を要求する
    """
    # 条項を取得
    result = await db.execute(
        select(Condition).where(Condition.id == condition_id)
    )
    condition = result.scalar_one_or_none()
    
    if not condition:
        raise HTTPException(status_code=404, detail="Condition not found")
    
    if condition.status != ConditionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Condition is not in pending status")
    
    # 証拠が提供されていることを確認
    if not evidence.evidence_text and not evidence.evidence_url:
        raise HTTPException(status_code=400, detail="At least one evidence field (text or url) must be provided")
    
    # AI評価
    judgment_result = await judgment_service.evaluate_evidence(
        condition_description=condition.description,
        condition_amount=condition.payment_amount,
        evidence_text=evidence.evidence_text,
        evidence_url=evidence.evidence_url,
    )
    
    # 判決レコードを作成
    judgment_id = f"jdg_{uuid.uuid4().hex[:12]}"
    judgment = Judgment(
        id=judgment_id,
        condition_id=condition_id,
        evidence_url=evidence.evidence_url,
        ai_result=judgment_result.result,
        ai_reason=judgment_result.reason,
        ai_confidence=judgment_result.confidence,
        judged_at=datetime.utcnow(),
    )
    
    db.add(judgment)
    
    # 条項ステータスを更新
    condition.status = ConditionStatus.JUDGING
    
    await db.commit()
    await db.refresh(judgment)
    
    # on-chainに証拠を提出
    if evidence.evidence_text or evidence.evidence_url:
        evidence_data = evidence.evidence_text or evidence.evidence_url
        await blockchain_service.submit_evidence(
            contract_id=condition.contract_id,
            condition_id=condition_id,
            evidence_data=evidence_data,
        )
    
    return JudgmentResponse(
        condition_id=condition_id,
        ai_result=judgment_result.result,
        ai_reason=judgment_result.reason,
        ai_confidence=judgment_result.confidence,
        judged_at=judgment.judged_at,
    )

# 条項の判決を取得
@router.get("/conditions/{condition_id}", response_model=JudgmentResponse)
async def get_judgment(
    condition_id: str,
    db: AsyncSession = Depends(get_db),
):
    """条項の判決を取得"""
    try:
        result = await db.execute(
            select(Judgment).where(Judgment.condition_id == condition_id)
        )
        judgment = result.scalar_one_or_none()
        
        if not judgment:
            raise HTTPException(status_code=404, detail="Judgment not found for this condition")
        
        return JudgmentResponse(
            condition_id=judgment.condition_id,
            ai_result=judgment.ai_result,
            ai_reason=judgment.ai_reason,
            ai_confidence=judgment.ai_confidence,
            judged_at=judgment.judged_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting judgment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get judgment: {str(e)}")

# 条項の承認
@router.post("/conditions/{condition_id}/approve", response_model=TransactionResponse)
async def approve_condition(
    condition_id: str,
    approval: ApprovalRequest,
    lawyer_address: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    条項の承認
    
    - 承認されたらオンチェーンで支払いを実行
    - トランザクション詳細を記録
    - 条項のステータスを更新
    """
    # 条項と判決を取得
    result = await db.execute(
        select(Condition)
        .options(selectinload(Condition.contract))
        .where(Condition.id == condition_id)
    )
    condition = result.scalar_one_or_none()
    
    if not condition:
        raise HTTPException(status_code=404, detail="Condition not found")
    
    if condition.status not in [ConditionStatus.JUDGING, ConditionStatus.PENDING]:
        raise HTTPException(status_code=400, detail="Condition cannot be approved")
    
    # 判決を取得
    jdg_result = await db.execute(
        select(Judgment).where(Judgment.condition_id == condition_id)
    )
    judgment = jdg_result.scalar_one_or_none()
    
    if judgment:
        judgment.final_result = approval.result
        judgment.approved_by = lawyer_address
        judgment.comment = approval.comment
        judgment.approved_at = datetime.utcnow()
    
    if approval.result == "approved":
        # on-chainの支払いを実行
        tx_result = await blockchain_service.approve_condition(
            contract_id=condition.contract_id,
            condition_id=condition_id,
        )
        
        if "error" in tx_result:
            raise HTTPException(status_code=500, detail=tx_result["error"])
        
        # トランザクションレコードを作成
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        transaction = Transaction(
            id=tx_id,
            condition_id=condition_id,
            tx_hash=tx_result["tx_hash"],
            amount=condition.payment_amount,
            from_address=condition.contract.payer_address if condition.contract else "",
            to_address=condition.recipient_address,
            block_number=tx_result.get("block_number"),
            gas_used=tx_result.get("gas_used"),
        )
        
        db.add(transaction)
        
        # 条項のステータスを更新
        condition.status = ConditionStatus.EXECUTED
        condition.executed_at = datetime.utcnow()
        
        # 契約のreleased_amountを更新
        condition.contract.released_amount += condition.payment_amount
        
        # すべての支払いが完了している場合、契約をcompletedに
        if condition.contract.released_amount >= condition.contract.total_amount:
            condition.contract.status = "completed"
        
        await db.commit()
        await db.refresh(transaction)
        
        return TransactionResponse(
            id=transaction.id,
            condition_id=transaction.condition_id,
            tx_hash=transaction.tx_hash,
            amount=transaction.amount,
            from_address=transaction.from_address,
            to_address=transaction.to_address,
            block_number=transaction.block_number,
            executed_at=transaction.executed_at,
        )
    else:
        # 条項を拒否
        condition.status = ConditionStatus.REJECTED
        await db.commit()
        
        raise HTTPException(
            status_code=200,
            detail={
                "message": "Condition rejected",
                "reason": approval.comment,
            }
        )

# 条項のトランザクションを取得
@router.get("/transactions/{condition_id}", response_model=TransactionResponse)
async def get_transaction(
    condition_id: str,
    db: AsyncSession = Depends(get_db),
):
    """条項のトランザクションを取得"""
    result = await db.execute(
        select(Transaction).where(Transaction.condition_id == condition_id)
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return TransactionResponse(
        id=transaction.id,
        condition_id=transaction.condition_id,
        tx_hash=transaction.tx_hash,
        amount=transaction.amount,
        from_address=transaction.from_address,
        to_address=transaction.to_address,
        block_number=transaction.block_number,
        executed_at=transaction.executed_at,
    )
