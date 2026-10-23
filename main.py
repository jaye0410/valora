from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from app.api.endpoints import router as api_router

load_dotenv()

app = FastAPI(title="valora")

# 静的ファイルの配信設定
app.mount("/static", StaticFiles(directory="static"), name="static")

# APIルーターの登録
app.include_router(api_router)

# ルートアクセス時に index.html を返す
@app.get("/")
def read_root():
  return FileResponse("static/index.html")