"""
LexFlow Protocol - Logging Configuration
本番環境に最適化されたロギング設定
"""
import logging
import sys
from typing import Optional

# ログフォーマット
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
JSON_LOG_FORMAT = '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'


def setup_logging(
    level: str = "INFO",
    use_json: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    アプリケーション全体のロギングを設定
    
    Args:
        level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: JSON形式でログを出力するか
        log_file: ログファイルのパス（Noneの場合は標準出力のみ）
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    log_format = JSON_LOG_FORMAT if use_json else LOG_FORMAT
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 既存のハンドラをクリア
    root_logger.handlers.clear()
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラ（指定された場合）
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)
    
    # サードパーティライブラリのログレベルを調整
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    モジュール用のロガーを取得
    
    Args:
        name: ロガー名（通常は __name__ を使用）
    
    Returns:
        設定済みのロガー
    """
    return logging.getLogger(name)
