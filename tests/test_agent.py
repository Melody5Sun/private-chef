import os
import uuid

# 模块顶层会构造模型和Tavily客户端，导入前填上假的key
for key in ("DASHSCOPE_BASE_URL", "DASHSCOPE_API_KEY", "TAVILY_API_KEY"):
    os.environ.setdefault(key, "http://test.invalid")

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import empty_checkpoint

from app.agents.AI_PrivateKitchen import (
    MAX_HISTORY_MESSAGES,
    checkpointer,
    prune_checkpoints,
    trim_history,
)


def image_message(url):
    return HumanMessage(content=[
        {"type": "image", "url": url},
        {"type": "text", "text": "这是什么"},
    ])


def test_trim_history_keeps_recent_window():
    messages = []
    for i in range(30):
        messages += [HumanMessage(f"问{i}"), AIMessage(f"答{i}")]

    trimmed = trim_history(messages)

    assert len(trimmed) == MAX_HISTORY_MESSAGES
    assert isinstance(trimmed[0], HumanMessage)
    assert trimmed[-1].content == "答29"


def test_trim_history_keeps_only_latest_image():
    old, new = image_message("https://x/old.png"), image_message("https://x/new.png")
    messages = [old, AIMessage("答1"), new, AIMessage("答2"), HumanMessage("再问")]

    trimmed = trim_history(messages)

    assert trimmed[0].content == [
        {"type": "text", "text": "[图片]"},
        {"type": "text", "text": "这是什么"},
    ]
    assert trimmed[2].content == new.content
    # 只改发给模型的副本，checkpoint里的原消息不动
    assert old.content[0] == {"type": "image", "url": "https://x/old.png"}


def test_prune_checkpoints_keeps_latest():
    thread_id = f"test-{uuid.uuid4().hex}"
    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    try:
        for i in range(3):
            checkpoint = empty_checkpoint()
            checkpoint["id"] = f"0000000{i}"
            checkpoint["channel_values"] = {"messages": [HumanMessage(f"第{i}条")]}
            saved = checkpointer.put(config, checkpoint, {}, {})
            checkpointer.put_writes(saved, [("messages", "x")], task_id="t")

        prune_checkpoints(thread_id)

        with checkpointer.cursor() as cur:
            for table in ("checkpoints", "writes"):
                cur.execute(f"SELECT checkpoint_id FROM {table} WHERE thread_id = ?", (thread_id,))
                assert cur.fetchall() == [("00000002",)]
        latest = checkpointer.get({"configurable": {"thread_id": thread_id}})
        assert latest["channel_values"]["messages"][0].content == "第2条"
    finally:
        checkpointer.delete_thread(thread_id)
