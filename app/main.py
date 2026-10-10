import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.v1 import chat
from app.api.v1 import oss
from app.common.logger import setup_logging

# 初始化日志配置
setup_logging()

app = FastAPI(
    title="Personal Chief API",
    description="私厨",
    version="0.1.0"
)

# 1.挂载路由（前端与 API 同源，不需要 CORS）
app.include_router(chat.router, prefix="/api/v1", tags=["对话"])
app.include_router(oss.router, prefix="/api/v1", tags=["申请上传签名url"])

# 2.挂载前端资源
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # 启动命令：python -m app.main
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
