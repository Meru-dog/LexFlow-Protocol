"""
LexFlow Protocol - x402 Payment Middleware
"""
from fastapi import Request, HTTPException, status, Depends
from typing import Optional, Dict
import json
from app.services.blockchain_service import blockchain_service
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import PaymentLog
from sqlalchemy import select
from datetime import datetime

class PaymentVerifier:
    def __init__(self, amount: float, token_symbol: str = "JPYC", token_address: str = None, recipient_address: str = None):
        from app.core.config import settings
        self.amount = amount
        self.token_symbol = token_symbol
        self.token_address = token_address or settings.JPYC_CONTRACT_ADDRESS
        self.recipient_address = recipient_address or settings.TREASURY_ADDRESS

    async def __call__(self, request: Request, db: AsyncSession = Depends(get_db)):
        """
        Dependency callable to verify x402 payment
        """
        # 1. PAYMENT-SIGNATURE ヘッダーを検索 (Format: "tx_hash=0x...")
        signature_header = request.headers.get("PAYMENT-SIGNATURE")

        if not signature_header:
            return await self._raise_payment_required()

        try:
            # 2. PAYMENT-SIGNATURE ヘッダーを解析 (Simple MVP: expecting just tx_hash)
            # Example header: "tx_hash=0x123abc..."
            tx_data = {}
            for part in signature_header.split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    tx_data[k] = v
            
            tx_hash = tx_data.get("tx_hash", "").strip()
            
            # 再帰的に tx_hash= を除去する（事故防止）
            while tx_hash.startswith("tx_hash="):
                tx_hash = tx_hash[8:]
            
            if not tx_hash or not tx_hash.startswith("0x"):
                 return await self._raise_payment_required()

            # 長さチェック（0x + 64文字 = 66文字）
            if len(tx_hash) > 66:
                tx_hash = tx_hash[:66]

            # 2. すでに使用されているかチェック (Double Spend Protection)
            # Idempotency: 同じトランザクションを短時間（10分以内）に同じエンドポイントで再送した場合は許可する
            existing_result = await db.execute(select(PaymentLog).where(PaymentLog.tx_hash == tx_hash))
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                 # 同一エンドポイントかつ10分以内なら、AI処理の再試行とみなして許可
                 time_diff = (datetime.utcnow() - existing.created_at.replace(tzinfo=None)).total_seconds()
                 if existing.endpoint == request.url.path and time_diff < 600:
                     print(f"ℹ️ Idempotency: Re-using payment for {tx_hash} (endpoint match)")
                     return True
                 else:
                     raise HTTPException(status_code=403, detail="トランザクションは既に使用されています")

            # 3. ブロックチェーン上でトランザクションを検証
            # RPCのインデックス遅延を考慮し、内部で数回リトライする
            import asyncio
            max_retries = 3
            retry_count = 0
            valid = False
            details = {}

            while retry_count < max_retries:
                valid, details = await blockchain_service.verify_token_transfer(
                    tx_hash=tx_hash,
                    expected_recipient=self.recipient_address,
                    expected_amount=self.amount,
                    token_address=self.token_address
                )
                if valid:
                    break
                
                # 「確認が取れない」系のエラーの場合のみリトライ
                err_msg = details.get("error", "")
                if "確認が取れませんでした" in err_msg or "not found" in err_msg.lower():
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"🔄 決済検証リトライ ({retry_count}/{max_retries}) for {tx_hash}...")
                        await asyncio.sleep(3) # 3秒待機
                    continue
                else:
                    # それ以外の致命的なエラー（受取人違い、金額不足等）は即時終了
                    break

            if not valid:
                error_msg = details.get("error", "決済検証に失敗しました")
                print(f"❌ 決済検証失敗: {error_msg}")
                # シグネチャはあるが無効な場合は、ヘッダーを含めず402エラー（または400）を投げる
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"決済検証エラー: {error_msg}"
                )

            # 4. トランザクションを記録
            log = PaymentLog(
                tx_hash=tx_hash,
                endpoint=request.url.path,
                amount=self.amount,
                token=self.token_symbol,
                payer=details.get("from", "unknown"),
                created_at=datetime.utcnow()
            )
            db.add(log)
            await db.commit()
            
            return True

        except HTTPException:
            raise
        except Exception as e:
            print(f"支払い検証処理中に予期せぬエラーが発生しました: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"支払い検証システムの内部エラー: {str(e)}"
            )

    async def _raise_payment_required(self):
        """ヘッダーに支払い情報を含めて402を投げる (初期要求時のみ)"""
        payment_info = json.dumps({
            "price": self.amount,
            "currency": self.token_symbol,
            "network": "sepolia", 
            "recipient": self.recipient_address,
            "token_address": self.token_address
        })
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="支払いが必要です",
            headers={"PAYMENT-REQUIRED": payment_info}
        )

