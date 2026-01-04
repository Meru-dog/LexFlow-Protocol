"""
LexFlow Protocol - Authentication Service (V3)
パスワードハッシュ化、JWT生成、ウォレット署名検証を提供
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import uuid

from passlib.context import CryptContext
from jose import jwt, JWTError
from eth_account.messages import encode_defunct
from web3 import Web3

from app.core.config import settings

# パスワードハッシュ化設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT設定は settings から取得するように変更


class AuthService:
    """認証サービスクラス"""
    
    # ===== パスワード関連 =====
    
    @staticmethod
    def _pre_hash(password: str) -> str:
        """Bcryptの72バイト制限を回避するためにSHA-256でプレハッシュ化(hex)"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def hash_password(password: str) -> str:
        """パスワードをハッシュ化 (Bcrypt + SHA-256)"""
        # SHA-256(hex)は常に64文字なのでBcryptの72バイト制限に常に収まる
        return pwd_context.hash(AuthService._pre_hash(password))
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """パスワードを検証"""
        try:
            # 1. 新しい方式（プレハッシュあり）で検証
            try:
                if pwd_context.verify(AuthService._pre_hash(plain_password), hashed_password):
                    return True
            except Exception:
                pass
            
            # 2. 旧方式（プレハッシュなし）でも確認（移行期間/既存ユーザー用）
            # Bcrypt limit check to avoid crash if hashed_password was created without pre-hashing
            if len(plain_password.encode()) <= 72:
                try:
                    return pwd_context.verify(plain_password, hashed_password)
                except Exception:
                    return False
            
            return False
        except Exception:
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """パスワード強度を検証"""
        if len(password) < 8:
            return False, "パスワードは8文字以上である必要があります"
        if not any(c.isupper() for c in password):
            return False, "パスワードには大文字を含む必要があります"
        if not any(c.islower() for c in password):
            return False, "パスワードには小文字を含む必要があります"
        if not any(c.isdigit() for c in password):
            return False, "パスワードには数字を含む必要があります"
        if len(password.encode()) > 72:
            return False, "パスワードが長すぎます。72バイト以内にしてください（半角英数72文字、和文24文字程度）。"
        return True, ""
    
    # ===== JWT関連 =====
    
    @staticmethod
    def create_access_token(user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
        """アクセストークンを生成"""
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "type": "access"
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """リフレッシュトークンを生成"""
        expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "refresh",
            "jti": str(uuid.uuid4())  # ユニークID（失効管理用）
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """トークンをデコード"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def verify_access_token(token: str) -> Optional[str]:
        """アクセストークンを検証し、user_idを返す"""
        payload = AuthService.decode_token(token)
        if payload and payload.get("type") == "access":
            return payload.get("sub")
        return None
    
    # ===== ウォレット署名関連 =====
    
    @staticmethod
    def generate_nonce() -> str:
        """署名用のnonceを生成"""
        return secrets.token_hex(16)
    
    @staticmethod
    def create_sign_message(nonce: str, workspace_id: Optional[str] = None, purpose: str = "wallet_link") -> str:
        """署名対象のメッセージを生成"""
        timestamp = datetime.utcnow().isoformat()
        message = f"LexFlow Protocol\n\nPurpose: {purpose}\nNonce: {nonce}\nTimestamp: {timestamp}"
        if workspace_id:
            message += f"\nWorkspace: {workspace_id}"
        return message
    
    @staticmethod
    def verify_wallet_signature(message: str, signature: str, expected_address: str) -> bool:
        """ウォレット署名を検証"""
        try:
            w3 = Web3()
            message_hash = encode_defunct(text=message)
            recovered_address = w3.eth.account.recover_message(message_hash, signature=signature)
            return recovered_address.lower() == expected_address.lower()
        except Exception as e:
            print(f"署名検証エラー: {e}")
            return False
    
    # ===== メール確認トークン =====
    
    @staticmethod
    def create_email_verification_token(user_id: str, email: str) -> str:
        """メール確認トークンを生成"""
        expire = datetime.utcnow() + timedelta(hours=24)
        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "type": "email_verification"
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def verify_email_verification_token(token: str) -> Optional[Tuple[str, str]]:
        """メール確認トークンを検証し、(user_id, email)を返す"""
        payload = AuthService.decode_token(token)
        if payload and payload.get("type") == "email_verification":
            return payload.get("sub"), payload.get("email")
        return None
    
    # ===== パスワードリセットトークン =====
    
    @staticmethod
    def create_password_reset_token(user_id: str) -> str:
        """パスワードリセットトークンを生成"""
        expire = datetime.utcnow() + timedelta(hours=1)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "password_reset",
            "jti": str(uuid.uuid4())
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def verify_password_reset_token(token: str) -> Optional[str]:
        """パスワードリセットトークンを検証し、user_idを返す"""
        payload = AuthService.decode_token(token)
        if payload and payload.get("type") == "password_reset":
            return payload.get("sub")
        return None


# シングルトンインスタンス
auth_service = AuthService()
