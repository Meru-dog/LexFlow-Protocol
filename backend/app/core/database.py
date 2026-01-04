"""
LexFlow Protocol - Database Configuration
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Base class for models
Base = declarative_base()

# データベースURLの決定（PostgreSQLが利用できない場合はSQLiteを使用）
DATABASE_URL = settings.DATABASE_URL

# Render/Herokuなどの PostgreSQL URL (postgres://) を SQLAlchemy の asyncpg 形式 (postgresql+asyncpg://) に変換
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# SQLiteの場合はスレッド間共有を許可する設定を追加
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    **engine_args
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency to get database session
async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
