
import asyncio
import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv(".env")

from app.core.config import settings
from app.services.contract_parser import contract_parser

async def test_parsing():
    print(f"DEBUG: OPENAI_API_KEY is {'set' if settings.OPENAI_API_KEY else 'NOT set'}")
    
    # ダミーのPDFコンテンツ（実際には読み込めないのでテキスト抽出だけテストするか、適当なバイト列）
    # ここでは実際のPDFファイルがあればそれを使いたいが、とりあえず空のバイト列でテスト
    dummy_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    
    print("Testing compute_hash...")
    h = contract_parser.compute_hash(dummy_pdf)
    print(f"Hash: {h}")
    
    print("Testing parse_contract (this will call OpenAI)...")
    try:
        # 実際のPDFファイルがあればそれを使う
        pdf_path = None
        # カレントディレクトリにあるPDFを探す
        for f in os.listdir("."):
            if f.endswith(".pdf"):
                pdf_path = f
                break
        
        if pdf_path:
            print(f"Using found PDF: {pdf_path}")
            with open(pdf_path, "rb") as f:
                content = f.read()
            result = await contract_parser.parse_contract(content)
            print("✅ Parsing successful!")
            print(f"Title: {result.title}")
        else:
            print("No PDF file found to test parsing.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_parsing())
