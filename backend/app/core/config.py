"""
LexFlow Protocol - 環境設定
Pydantic Settingsを使用した環境変数の読み込みと設定管理
"""
from pydantic_settings import BaseSettings  # Pydantic設定基底クラス
from typing import List  # 型ヒント用
import os  # OS操作用


class Settings(BaseSettings):
    """
    アプリケーション設定クラス
    環境変数から設定値を自動的に読み込む
    """
    
    # ===== アプリケーション基本設定 =====
    APP_NAME: str = "LexFlow Protocol"  # アプリケーション名
    APP_VERSION: str = "1.0.0"  # バージョン番号
    DEBUG: bool = False  # デバッグモード（本番環境ではFalse）
    
    # ===== OpenAI API設定 =====
    # GPT-4による契約書解析と判定に使用
    OPENAI_API_KEY: str = ""  # OpenAI APIキー
    
    # ===== データベース設定 =====
    # PostgreSQL非同期接続URL (デフォルトをSQLiteに変更)
    DATABASE_URL: str = "sqlite+aiosqlite:///./lexflow.db"
    
    # ===== ブロックチェーン設定 =====
    # Ethereum RPC URL（Infura、Alchemy等のプロバイダー）
    ETHEREUM_RPC_URL: str = "https://sepolia.infura.io/v3/YOUR_KEY"
    # エスクロースマートコントラクトのアドレス
    ESCROW_CONTRACT_ADDRESS: str = ""
    # JPYCトークンコントラクトのアドレス (Sepolia)
    JPYC_CONTRACT_ADDRESS: str = "0x138D4810c6D977eE490f67D9659Cb26A89d630f9"
    # 支払いの受取先アドレス（テスラや運営費などのプール）
    TREASURY_ADDRESS: str = "0x18c151c219b4B0B8D2E88B8c4F9A8b83596bf7Bb"
    # トランザクション署名用の秘密鍵（安全に管理すること！）
    PRIVATE_KEY: str = ""
    
    # ===== セキュリティ設定 =====
    # JWT（JSON Web Token）認証用の秘密鍵
    JWT_SECRET_KEY: str = "change-this-in-production"  # 本番環境では変更必須
    JWT_ALGORITHM: str = "HS256"  # JWTのアルゴリズム
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # アクセストークンの有効期限（分）
    
    # ===== CORS設定 =====
    # クロスオリジンリクエストを許可するURL（カンマ区切り）
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000,https://lexflow-frontend.vercel.app"
    
    # ===== オンチェーン設定 =====
    @property
    def cors_origins_list(self) -> List[str]:
        """
        CORS_ORIGINSをリストに変換
        カンマ区切りの文字列をリストに分割して返す
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        """Pydantic設定クラスの内部設定"""
        env_file = ".env"  # 環境変数ファイルのパス
        case_sensitive = True  # 環境変数名の大文字小文字を区別


# グローバル設定インスタンス
# アプリケーション全体でこのインスタンスを使用
settings = Settings()
