from typing import Optional

from pydantic import BaseModel, Field

# --- 2. 数据模型 ---
class ChatRequest(BaseModel):
    # 长度上限：历史按条数裁剪，单条消息不设限会撑爆token预算
    message: str = Field(min_length=1, max_length=4000)
    image_url: Optional[str] = None
    thread_id: str = Field(min_length=1, max_length=64)
