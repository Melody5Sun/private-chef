from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest
from app.agents.AI_PrivateKitchen import search_recipes, get_messages, clear_messages
from app.api.v1.oss import UPLOAD_URL_PREFIX
from fastapi.responses import StreamingResponse
router = APIRouter()


@router.post("/chat/stream")
async def chat_endpoint(request: ChatRequest):
    """流式对话"""
    # 只接受本服务签发的上传地址，避免让模型去抓取任意外部URL
    if request.image_url and not request.image_url.startswith(UPLOAD_URL_PREFIX):
        raise HTTPException(status_code=400, detail="图片地址不合法")
    return StreamingResponse(
        search_recipes(request.message, request.image_url, request.thread_id),
        # 输出是纯文本片段，不是SSE的 data: 帧
        media_type="text/plain; charset=utf-8"
    )


@router.get("/chat/messages")
def get_chat_messages(thread_id: str):
    """获取历史消息"""
    messages = get_messages(thread_id)
    return {"messages": messages}


@router.delete("/chat/messages")
def clear_chat_messages(thread_id: str):
    """清空历史消息"""
    clear_messages(thread_id)
    return {"success": True}