"""
LexFlow Protocol - Contract API Routes
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import json
import os
import shutil

from app.core.database import get_db
from app.models.models import Contract, Condition, ContractStatus, ConditionStatus, Workspace, WorkspaceUser
from app.schemas.schemas import (
    ContractCreate, ContractResponse, ContractDetail,
    ConditionCreate, ConditionResponse, ContractParseResponse
)
from app.services.contract_parser import contract_parser
from app.services.blockchain_service import blockchain_service
from app.services.version_service import version_service  # V2: F3機能
from app.api.auth import get_current_user_id

# ルーターの定義
router = APIRouter(prefix="/contracts", tags=["Contracts"])

# コントラクトのアップロード
@router.post("/upload", response_model=ContractParseResponse)
async def upload_contract(
    file: UploadFile = File(...), # PDFファイルのアップロード
    title: Optional[str] = Form(None), # コントラクトのタイトルの指定 (Form)
    payer_address: Optional[str] = Form(None), # 支払者のアドレスの指定 (Form)
    lawyer_address: str = Form(...), # 裁判のアドレスの指定 (Form)
    total_amount: Optional[float] = Form(None), # 手動での総額指定 (Form)
    db: AsyncSession = Depends(get_db), # データベースセッション
    current_user_id: str = Depends(get_current_user_id),
):
    """
    AIを使用してPDFファイルを解析し、コントラクトをアップロードする
    
    - 条項、支払条件、当事者を抽出
    - 解析データをデータベースに保存
    - 構造化されたコントラクトデータを返す
    """
    filename = file.filename.lower()
    if not (filename.endswith(".pdf") or filename.endswith(".txt") or filename.endswith(".md")):
        raise HTTPException(status_code=400, detail="Only PDF, Text, and Markdown files are accepted")
    
    print(f"📄 Uploading file: {file.filename}")
    
    try:
        # ファイルの内容を読み込んで、ハッシュ値を計算
        file_content = await file.read()
        print(f"🔍 File read: {len(file_content)} bytes")
        file_hash = contract_parser.compute_hash(file_content)
        
        # AIを使用してコントラクトを解析して、解析結果を取得
        print("🤖 Starting AI parsing...")
        parsed = await contract_parser.parse_contract(file_content, filename=file.filename)
        print("✅ AI parsing completed")
        
        # コントラクトIDの生成
        contract_id = f"contract_{uuid.uuid4().hex[:12]}"
        
        # ユーザー指定の値を優先し、なければAI解析結果を使用
        contract_title = title if title and title.strip() != "" else parsed.title
        final_total_amount = total_amount if total_amount is not None else parsed.total_value
        
        # ファイルを保存
        # ファイル名を安全に扱う（ディレクトリトラバーサル対策などが必要だが、ここでは簡易的に）
        safe_filename = os.path.basename(file.filename)
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_filename)
        
        # PDFコンテンツを書き込む（既に読み込んでいるため、メモリから書き込み）
        with open(file_path, "wb") as f:
            f.write(file_content)
        print(f"📁 ファイルを保存: {file_path}")

        # コントラクトレコードの作成
        print("💾 databaseに保存...")
        # ユーザーの最初のワークスペースを取得
        ws_result = await db.execute(
            select(Workspace.id)
            .join(WorkspaceUser)
            .where(WorkspaceUser.user_id == current_user_id)
            .limit(1)
        )
        workspace_id = ws_result.scalar_one_or_none()
        
        # コントラクトオブジェクトを作成
        contract = Contract(
            id=contract_id,
            workspace_id=workspace_id,  # ワークスペースIDを設定
            title=parsed.title or title or "Untitled Contract",
            parties=json.dumps(parsed.parties),
            payer_address=payer_address if payer_address and payer_address != "" else None,
            lawyer_address=lawyer_address if lawyer_address and lawyer_address != "" else None,
            total_amount=final_total_amount if final_total_amount is not None else parsed.total_value,
            summary=parsed.summary,
            status=ContractStatus.PENDING,
            parsed_data=json.dumps(parsed.model_dump()),
            file_url=file_path, # Add file_url back
            file_hash=file_hash, # Add file_hash back
        )
        
        # コントラクトレコードをデータベースに保存
        db.add(contract)
        
        # V2: F3 初期バージョンの作成
        print("📁 Creating initial version record...")
        await version_service.create_version(
            db=db,
            case_id=contract_id,
            file_content=file_content,
            creator_address=lawyer_address if lawyer_address and lawyer_address != "" else "0x0000000000000000000000000000000000000000",
            title="Initial Uploaded Version",
            summary=parsed.summary[:500] if parsed.summary else "Initial version",
            filename=file.filename
        )
        
        # コミット
        await db.commit()
        print(f"🎉 Contract saved with ID: {contract_id}")
        
    except Exception as e:
        print(f"❌ Error during contract upload: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    
    return ContractParseResponse(
        contract_id=contract_id,
        title=contract_title,
        parties=parsed.parties,
        clauses=[
            {
                "clause_id": c.clause_id,
                "clause_type": c.clause_type,
                "description": c.description,
                "amount": c.amount,
                "deadline": c.deadline,
                "parties": c.parties_involved,
            }
            for c in parsed.clauses
        ],
        total_value=final_total_amount,
        summary=parsed.summary,
    )

# コントラクト一覧の取得
@router.get("/", response_model=List[ContractResponse])
async def list_contracts(
    status: str = None,
    workspace_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Contract).options(selectinload(Contract.conditions))
    # 状態が指定されている場合は、その状態のコントラクトのみを取得
    if status:
        query = query.where(Contract.status == status)
    
    # ワークスペースが指定されている場合は、そのワークスペースのコントラクトのみを取得
    if workspace_id:
        query = query.where(Contract.workspace_id == workspace_id)

    # 作成日時で降順でソート
    query = query.order_by(Contract.created_at.desc())
    
    # クエリを実行して、結果を取得
    result = await db.execute(query)
    # コントラクトレコードを取得
    contracts = result.scalars().all()
    
    return [
        ContractResponse(
            id=c.id,
            title=c.title,
            file_url=c.file_url,
            payer_address=c.payer_address,
            lawyer_address=c.lawyer_address,
            total_amount=c.total_amount,
            released_amount=c.released_amount,
            status=c.status,
            blockchain_tx_hash=c.blockchain_tx_hash,
            created_at=c.created_at,
            condition_count=len(c.conditions),
        )
        for c in contracts
    ]

# コントラクトの詳細を取得
@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
):
    # コントラクトIDでコントラクトレコードを取得
    result = await db.execute(
        select(Contract)
        .options(selectinload(Contract.conditions))
        .where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    # コントラクトレコードが存在しない場合は、404エラーを返す
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return ContractDetail(
        id=contract.id,
        title=contract.title,
        file_url=contract.file_url,
        payer_address=contract.payer_address,
        lawyer_address=contract.lawyer_address,
        total_amount=contract.total_amount,
        released_amount=contract.released_amount,
        status=contract.status,
        blockchain_tx_hash=contract.blockchain_tx_hash,
        created_at=contract.created_at,
        condition_count=len(contract.conditions),
        conditions=[
            ConditionResponse(
                id=cond.id,
                contract_id=cond.contract_id,
                condition_type=cond.condition_type,
                description=cond.description,
                payment_amount=cond.payment_amount,
                recipient_address=cond.recipient_address,
                status=cond.status,
                created_at=cond.created_at,
                executed_at=cond.executed_at,
            )
            for cond in contract.conditions
        ],
        parsed_data=json.loads(contract.parsed_data) if contract.parsed_data else None,
    )

# コントラクトをアクティベート
@router.post("/{contract_id}/activate")
async def activate_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
):
    # コントラクトIDでコントラクトレコードを取得
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if contract.status != ContractStatus.PENDING:
        raise HTTPException(status_code=400, detail="Contract is not in pending status")
    
    # オンチェーンのエスクローコントラクトを作成
    tx_result = await blockchain_service.create_escrow_contract(
        contract_id=contract_id,
        lawyer_address=contract.lawyer_address,
        amount_jpyc=contract.total_amount,
    )
    
    if "error" in tx_result:
        raise HTTPException(status_code=500, detail=tx_result["error"])
    
    # コントラクトステータスを更新
    contract.status = ContractStatus.ACTIVE
    # ブロックチェーントランザクションハッシュを更新
    contract.blockchain_tx_hash = tx_result["tx_hash"]
    # データベースをコミット
    await db.commit()
    
    return {
        "message": "Contract activated successfully",
        "tx_hash": tx_result["tx_hash"],
        "etherscan_url": blockchain_service.get_etherscan_url(tx_result["tx_hash"]),
    }

# 条項を追加
@router.post("/{contract_id}/conditions", response_model=ConditionResponse)
async def add_condition(
    contract_id: str,
    condition: ConditionCreate,
    db: AsyncSession = Depends(get_db),
):
    # コントラクトIDでコントラクトレコードを取得
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    condition_id = f"cond_{uuid.uuid4().hex[:12]}"
    
    new_condition = Condition(
        id=condition_id,
        contract_id=contract_id,
        condition_type=condition.condition_type,
        description=condition.description,
        payment_amount=condition.payment_amount,
        recipient_address=condition.recipient_address,
        status=ConditionStatus.PENDING,
    )
    
    db.add(new_condition)
    await db.commit()
    await db.refresh(new_condition)
    
    # コントラクトがアクティブな場合は、チェーン上に条件を追加
    if contract.status == ContractStatus.ACTIVE:
        tx_result = await blockchain_service.add_condition(
            contract_id=contract_id,
            condition_id=condition_id,
            payee_address=condition.recipient_address,
            amount_jpyc=condition.payment_amount,
        )
        if "error" not in tx_result:
            # ブロックチェーンのトランザクションハッシュを更新
            pass
    
    return ConditionResponse(
        id=new_condition.id,
        contract_id=new_condition.contract_id,
        condition_type=new_condition.condition_type,
        description=new_condition.description,
        payment_amount=new_condition.payment_amount,
        recipient_address=new_condition.recipient_address,
        status=new_condition.status,
        created_at=new_condition.created_at,
        executed_at=new_condition.executed_at,
    )
@router.get("/{contract_id}/text")
async def get_contract_text(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    契約書PDFからテキストを抽出して返す
    """
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if not os.path.exists(contract.file_url):
         raise HTTPException(status_code=404, detail="File not found")
         
    with open(contract.file_url, "rb") as f:
        file_content = f.read()
        
    text = await contract_parser.extract_text_from_file(file_content, filename=os.path.basename(contract.file_url))
    
    return {"text": text}
