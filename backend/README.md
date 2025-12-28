# LexFlow Protocol Backend

Python FastAPI バックエンド

## セットアップ

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

## 環境変数

`.env.example` を `.env` にコピーして設定:

```bash
cp .env.example .env
```

## 開発サーバー起動

```bash
uvicorn app.main:app --reload --port 8000
```

## APIドキュメント

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
