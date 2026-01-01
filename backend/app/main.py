"""
LexFlow Protocol - メインFastAPIアプリケーション
AI搭載の契約解析とブロックチェーン統合のためのAPIサーバー
"""
from fastapi import FastAPI, Request, HTTPException  # FastAPIフレームワーク
from fastapi.responses import JSONResponse  # JSONレスポンス
from fastapi.middleware.cors import CORSMiddleware  # CORSミドルウェア
import traceback  # スタックトレース取得用
from contextlib import asynccontextmanager  # 非同期コンテキストマネージャー

from app.core.config import settings  # アプリケーション設定の読み込み
from app.core.database import engine, Base  # データベースエンジンとベースモデル
from app.api import contracts, judgments, obligations, versions, signatures, redline, zk_proofs  # APIルーターのインポート（V2: ...に加えzk_proofsを追加）


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフサイクル管理
    起動時にデータベーステーブルを作成し、終了時にクリーンアップを行う
    """
    # 起動時: データベーステーブルの作成（接続可能な場合）
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)  # 全テーブルを作成
        print("✅ Database connected and tables created")
    except Exception as e:
        # データベース未接続でも起動を継続（開発用）
        print(f"⚠️ Database connection failed: {e}")
        print("   Running without database - some features will be unavailable")
    
    yield  # アプリケーション実行中
    
    # 終了時: データベース接続のクリーンアップ
    try:
        await engine.dispose()
    except Exception:
        pass


# FastAPIアプリケーションのインスタンス作成
app = FastAPI(
    title=settings.APP_NAME,  # アプリケーション名
    version=settings.APP_VERSION,  # バージョン
    description="""
    LexFlow Protocol API - AI搭載の契約実行とEthereumスマートコントラクト、JPYC決済

    ## 機能
    - 📄 PDF契約書のアップロードとAI解析
    - 🤖 AI搭載のエビデンス判定
    - ⚖️ 弁護士承認ワークフロー
    - 💰 Ethereum経由の自動JPYC決済
    - 🔗 オンチェーン取引追跡
    """,
    lifespan=lifespan,  # ライフサイクル管理関数を設定
)

# CORSミドルウェアの設定
# フロントエンドからのAPIアクセスを許可するために必要
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # 許可するオリジン
    allow_credentials=True,  # 認証情報（Cookie等）の送信を許可
    allow_methods=["*"],  # 全HTTPメソッドを許可
    allow_headers=["*"],  # 全ヘッダーを許可
    expose_headers=["*"], # 全てのエクスポートヘッダーを許可
)

# グローバル例外ハンドラ
# エラー発生時にもCORSヘッダーを確実に返し、JSONでエラー内容を伝える
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    すべての未捕捉例外をキャッチするハンドラ
    """
    # エラー内容のログ出力（スタックトレース含む）
    print(f"❌ Unhandled Exception: {str(exc)}")
    traceback.print_exc()
    
    # 500エラーのレスポンス
    status_code = 500
    detail = str(exc)
    
    # HTTPExceptionの場合はそのステータスコードと詳細を使用
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
    
    response = JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "type": type(exc).__name__,
            "path": request.url.path
        }
    )
    
    # CORSヘッダーを明示的に付与（ミドルウェアが効かない場合への対策）
    origin = request.headers.get("origin")
    if origin in settings.cors_origins_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
    return response

# APIルーターの登録
# /api/v1 プレフィックスで各ルーターを登録
from fastapi.staticfiles import StaticFiles
import os

app.include_router(contracts.router, prefix="/api/v1")  # 契約管理API
app.include_router(judgments.router, prefix="/api/v1")  # 判定・承認API
app.include_router(obligations.router, prefix="/api/v1")  # V2: 義務管理API（F2）
app.include_router(versions.router, prefix="/api/v1")     # V2: 契約版管理API（F3）
app.include_router(signatures.router, prefix="/api/v1")   # V2: 署名API（F3）
app.include_router(redline.router, prefix="/api/v1")      # V2: Redline比較API（F4）
app.include_router(zk_proofs.router, prefix="/api/v1")    # V2: ZK証跡API（F7/F9）

# 静的ファイルの提供 (PDF表示用)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    """
    ルートエンドポイント
    アプリケーションの基本情報を返す
    """
    return {
        "name": settings.APP_NAME,  # アプリケーション名
        "version": settings.APP_VERSION,  # バージョン
        "status": "running",  # 稼働状態
        "docs": "/docs",  # Swagger UIへのリンク
    }


@app.get("/health")
async def health_check():
    """
    ヘルスチェックエンドポイント
    システムの稼働状態とブロックチェーン接続状態を確認
    """
    from app.services.blockchain_service import blockchain_service
    
    return {
        "status": "healthy",  # システム状態
        "blockchain_connected": blockchain_service.is_connected(),  # ブロックチェーン接続状態
        "chain_id": blockchain_service.get_chain_id() if blockchain_service.is_connected() else None,  # チェーンID
    }


@app.get("/api/v1/blockchain/status")
async def blockchain_status():
    """
    ブロックチェーン接続状態の詳細を取得
    Ethereumネットワークとスマートコントラクトのアドレスを返す
    """
    from app.services.blockchain_service import blockchain_service
    
    return {
        "connected": blockchain_service.is_connected(),  # 接続状態
        "chain_id": blockchain_service.get_chain_id() if blockchain_service.is_connected() else None,  # チェーンID
        "escrow_address": settings.ESCROW_CONTRACT_ADDRESS,  # エスクローコントラクトアドレス
        "jpyc_address": settings.JPYC_CONTRACT_ADDRESS,  # JPYCトークンアドレス
    }


@app.get("/api/v1/config")
async def get_config():
    """
    フロントエンドと同期すべき公開設定を取得
    """
    return {
        "chainId": 11155111, # Sepolia
        "escrowAddress": settings.ESCROW_CONTRACT_ADDRESS or "0x0000000000000000000000000000000000000000",
        "jpycAddress": settings.JPYC_CONTRACT_ADDRESS,
        "appName": settings.APP_NAME
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
