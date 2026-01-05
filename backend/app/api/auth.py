"""
LexFlow Protocol - Authentication API (V3)
サインアップ、ログイン、ウォレット連携のエンドポイント
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
import json
from app.core.database import get_db
from app.models.models import User, Wallet, UserStatus, AuditEventType
from app.services.auth_service import auth_service
from app.services.audit_service import audit_service


router = APIRouter(prefix="/auth", tags=["認証 (Authentication)"])


# ===== リクエスト/レスポンススキーマ =====

class SignupRequest(BaseModel):
    """サインアップリクエスト"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)
    display_name: Optional[str] = None


class SignupResponse(BaseModel):
    """サインアップレスポンス"""
    user_id: str
    email: str
    message: str


class LoginRequest(BaseModel):
    """ログインリクエスト"""
    email: EmailStr
    password: str = Field(..., max_length=256)


class LoginResponse(BaseModel):
    """ログインレスポンス"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    is_new_user: Optional[bool] = False


class WalletNonceRequest(BaseModel):
    """ウォレットnonce取得リクエスト"""
    address: str = Field(..., pattern="^0x[a-fA-F0-9]{40}$")


class WalletNonceResponse(BaseModel):
    """ウォレットnonceレスポンス"""
    nonce: str
    message: str


class WalletVerifyRequest(BaseModel):
    """ウォレット署名検証リクエスト"""
    address: str = Field(..., pattern="^0x[a-fA-F0-9]{40}$")
    signature: str
    message: str


class WalletVerifyResponse(BaseModel):
    """ウォレット署名検証レスポンス"""
    success: bool
    wallet_id: Optional[str] = None
    message: str


class PasswordResetRequest(BaseModel):
    """パスワードリセットリクエスト"""
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """パスワードリセット確認リクエスト"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=256)


class TokenRefreshRequest(BaseModel):
    """トークンリフレッシュリクエスト"""
    refresh_token: str


# ===== 一時的なnonce保存（本番環境ではRedis等を使用） =====
_nonce_store: dict = {}


# ===== 認証依存関係 =====

from app.core.logging_config import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

async def get_current_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """現在のユーザーIDを取得する依存関係"""
    if not token:
        logger.warning("Authentication failed: No token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証トークンが必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = auth_service.verify_access_token(token)
    if not user_id:
        logger.warning(f"Authentication failed: Invalid or expired token: {token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンまたは期限切れです",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


# ===== エンドポイント =====

@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    """
    新規ユーザー登録
    
    - メールアドレスとパスワードで登録
    - パスワード強度を検証
    - メール確認トークンを生成（実際の送信は別途実装）
    """
    # パスワード強度チェック
    is_valid, error_msg = auth_service.validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # メールアドレス重複チェック
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="このメールアドレスは既に登録されています")
    
    # ユーザー作成
    user_id = str(uuid.uuid4())
    password_hash = auth_service.hash_password(request.password)
    
    new_user = User(
        id=user_id,
        email=request.email,
        password_hash=password_hash,
        display_name=request.display_name,
        status=UserStatus.PENDING
    )
    db.add(new_user)
    await db.commit()
    
    # メール確認トークン生成（実際の送信は別途実装）
    verification_token = auth_service.create_email_verification_token(user_id, request.email)
    print(f"[DEBUG] Email verification token for {request.email}: {verification_token}")
    
    return SignupResponse(
        user_id=user_id,
        email=request.email,
        message="ユーザー登録が完了しました。メールを確認してください。"
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    ログイン
    
    - メールアドレスとパスワードで認証
    - JWTアクセストークンとリフレッシュトークンを発行
    """
    # ユーザー取得
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user:
        await audit_service.log_event(
            db, AuditEventType.AUTH_LOGIN_FAILED,
            detail={"email": request.email, "reason": "ユーザーが見つかりません"}
        )
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")
    
    # パスワード検証
    if not auth_service.verify_password(request.password, user.password_hash):
        await audit_service.log_event(
            db, AuditEventType.AUTH_LOGIN_FAILED,
            actor_id=user.id,
            detail={"email": request.email, "reason": "パスワードが正しくありません"}
        )
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")
    
    # ステータスチェック
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="このアカウントは停止されています")
    if user.status == UserStatus.DELETED:
        raise HTTPException(status_code=403, detail="このアカウントは削除されています")
    
    # トークン生成
    access_token = auth_service.create_access_token(user.id, user.email)
    refresh_token = auth_service.create_refresh_token(user.id)
    
    # 監査ログ
    await audit_service.log_event(
        db, AuditEventType.AUTH_LOGIN,
        actor_id=user.id,
        detail={"email": user.email}
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email
    )


@router.post("/logout")
async def logout(current_user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    """
    ログアウト
    
    - クライアント側でトークンを破棄
    - サーバー側ではリフレッシュトークンの失効を行う（将来実装）
    """
    await audit_service.log_event(db, AuditEventType.AUTH_LOGOUT, actor_id=current_user_id)
    return {"message": "ログアウトしました"}


@router.post("/token/refresh", response_model=LoginResponse)
async def refresh_token(request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    トークンリフレッシュ
    
    - リフレッシュトークンを使って新しいアクセストークンを発行
    """
    payload = auth_service.decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="無効なリフレッシュトークンです")
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="ユーザーが見つかりません")
    
    access_token = auth_service.create_access_token(user.id, user.email)
    new_refresh_token = auth_service.create_refresh_token(user.id)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user_id=user.id,
        email=user.email
    )


@router.post("/wallet/nonce", response_model=WalletNonceResponse)
async def get_wallet_nonce(request: WalletNonceRequest):
    """
    ウォレット署名用のnonceを取得
    
    - 署名対象のメッセージとnonceを返す
    - nonceは一時的に保存（本番ではRedis等を使用）
    """
    nonce = auth_service.generate_nonce()
    message = auth_service.create_sign_message(nonce, purpose="wallet_link")
    
    # nonceを一時保存
    _nonce_store[request.address.lower()] = {
        "nonce": nonce,
        "message": message,
        "expires_at": datetime.utcnow().timestamp() + 300  # 5分間有効
    }
    
    return WalletNonceResponse(
        nonce=nonce,
        message=message
    )


@router.post("/wallet/verify", response_model=WalletVerifyResponse)
async def verify_wallet(
    request: WalletVerifyRequest,
    authorization: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    ウォレット署名を検証してユーザーに紐付け
    
    - 署名を検証
    - 既存ユーザーにウォレットを紐付け
    """
    address_lower = request.address.lower()
    
    # nonce検証
    stored = _nonce_store.get(address_lower)
    if not stored:
        raise HTTPException(status_code=400, detail="nonceが見つかりません。再度nonceを取得してください。")
    
    if datetime.utcnow().timestamp() > stored["expires_at"]:
        del _nonce_store[address_lower]
        raise HTTPException(status_code=400, detail="nonceが期限切れです。再度nonceを取得してください。")
    
    if request.message != stored["message"]:
        raise HTTPException(status_code=400, detail="メッセージが一致しません")
    
    # 署名検証
    if not auth_service.verify_wallet_signature(request.message, request.signature, request.address):
        raise HTTPException(status_code=400, detail="署名が無効です")
    
    # nonce削除
    del _nonce_store[address_lower]
    
    # 既存ウォレットチェック
    result = await db.execute(
        select(Wallet).where(Wallet.address == address_lower).options(selectinload(Wallet.user))
    )
    existing_wallet = result.scalar_one_or_none()
    
    if existing_wallet and existing_wallet.user_id:
        # ウォレットに紐付いたユーザーがいる場合はログイン
        user = existing_wallet.user
        access_token = auth_service.create_access_token(user.id, user.email)
        refresh_token = auth_service.create_refresh_token(user.id)
        
        logger.info(f"メタマスクでのログイン成功: {address_lower}, user: {user.id}")
        
        # 監査ログ
        await audit_service.log_event(
            db, AuditEventType.AUTH_LOGIN,
            actor_id=user.id,
            actor_wallet=address_lower,
            detail={"method": "metamask"}
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            email=user.email,
            is_new_user=False
        )
    
    # ウォレットが未登録またはユーザー未紐付けの場合
    # ログイン中のユーザーがいれば紐付け、いなければ新規作成またはエラー
    # ※今回は簡略化のため、署名検証成功のみを返す
    
    return WalletVerifyResponse(
        success=True,
        wallet_id=existing_wallet.id if existing_wallet else None,
        message="署名が検証されました。ログイン後にウォレットを紐付けできます。"
    )


@router.post("/password-reset")
async def request_password_reset(request: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """
    パスワードリセットリクエスト
    
    - メールアドレスに対してリセットトークンを生成
    - 実際のメール送信は別途実装
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user:
        # セキュリティ上、ユーザーが存在しなくても同じレスポンスを返す
        return {"message": "パスワードリセットのメールを送信しました（登録されている場合）"}
    
    reset_token = auth_service.create_password_reset_token(user.id)
    print(f"[DEBUG] Password reset token for {request.email}: {reset_token}")
    
    return {"message": "パスワードリセットのメールを送信しました（登録されている場合）"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(request: PasswordResetConfirmRequest, db: AsyncSession = Depends(get_db)):
    """
    パスワードリセット確認
    
    - トークンを検証して新しいパスワードを設定
    """
    user_id = auth_service.verify_password_reset_token(request.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="無効または期限切れのトークンです")
    
    # パスワード強度チェック
    is_valid, error_msg = auth_service.validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="ユーザーが見つかりません")
    
    user.password_hash = auth_service.hash_password(request.new_password)
    await db.commit()
    
    return {"message": "パスワードが正常に変更されました"}
