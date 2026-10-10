# 导入初始化依赖，数据库依赖
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from app.common.logger import logger
from langchain_core.messages import HumanMessage,AIMessage,AIMessageChunk,trim_messages
import sqlite3
import os

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 导入工具依赖
from langchain.tools import tool
from langchain_tavily import TavilySearch

# 定义一个基本tavily工具
simple_search = TavilySearch(
    max_results=5,
    topic = "general"
)

# 定义正式的搜索工具
@tool
def tavily_search(query: str):
    """
    这是一个搜索工具，用于连接网络，查找信息。
    :param query: 用户提出需要查询的问题。
    :return: tavily查询到的结果。
    """
    return simple_search.invoke(query)

# 定义一个模型，用来与用户对话
# 对话模型（需要支持多模态），使用qwen3.5-plus
chat_model = init_chat_model(
    model = "qwen3.5-plus",
    model_provider="openai",
    base_url = os.getenv("DASHSCOPE_BASE_URL"),
    api_key = os.getenv("DASHSCOPE_API_KEY")
)

# 添加checkpointer
# 连接sqlite
# 基于文件位置定位，不依赖启动目录
db_dir = os.path.join(os.path.dirname(__file__), "..", "..", "db")
os.makedirs(db_dir, exist_ok=True)
connection = sqlite3.connect(os.path.join(db_dir, "AI_PrivateKitchen.db"), check_same_thread=False)
# 初始化checkpointer
checkpointer = SqliteSaver(connection)
# 自动建表
checkpointer.setup()

# 系统提示词编写
system_prompt = """
# 身份
你是一个拥有丰富经验的AI私厨管家，只回答与食物有关的问题，包括但不限于食谱，食材用量，制作厨具，饮食偏好等。
当用户提问无关话题时，有礼貌地告诉他自己只是一个美食方面的智能助手，不了解其他内容。
# 指令
1.可以使用工具，尤其是你当前的知识无法回答用户的问题时。
2.用户可能会传入图片要求识别，当你无法识别时，请直接告知用户无法识别，并且不要自行编造相关问题的答案。
3.与食谱相关的问题，请尽量获得多个食谱，并按照营养价值，制作难度等因素对食谱进行排序（可以使用评分，分级等方法，要求一目了然，优先级高的先显示）
4.如果你可以识别图片，但是发现搜索工具无法找到符合用户要求的信息，请告知用户，并发挥创造力进行回答，要求回答有理有据。
# 输出格式
- 只问一道菜怎么做：先说明这是什么菜，再给出用料比例（具体克数），分步骤写做法，最后一句话点明要点。
- 识别图片中的食材：先说菜名，再逐项列出核心食材（部位或品种、口感、营养），图中未直接显示的常用调料单独注明。
- 推荐多个食谱：每个食谱按下面的结构写，全部列完后附2-3条厨师小Tips。

🍳相关食谱推荐
1. 菜名（版本特点，如“经典家常版”）
制作难度：★☆☆（一句话说明，如“10分钟快手菜”）
营养亮点：一句话，有需要慎选的人群也在这里说明
做法简介 & 关键步骤：
① 处理食材：写清切法、腌制用料和时间
② 炒制过程：按下锅顺序写，点明火候和调味

💡 厨师小 Tips
每条写一个技巧和它的原因，如“青椒最后下锅，大火快炒1-2分钟，避免维生素C流失”。
"""

# 每次调用模型最多携带的历史消息条数
MAX_HISTORY_MESSAGES = 20

def trim_history(messages):
    """只把最近的消息发给模型。不修改checkpoint，历史接口仍返回完整记录。"""
    # shortcut: 按条数而非token裁剪，单条消息很长时仍可能超预算，届时把token_counter换成"approximate"
    trimmed = trim_messages(
        messages,
        max_tokens=MAX_HISTORY_MESSAGES,
        token_counter=len,
        strategy="last",
        start_on="human",
    )
    # 单轮内工具调用超过上限时，窗口里没有用户消息，退回完整历史
    return trimmed or messages

# 同步、异步都实现：FastAPI走stream，langgraph dev走astream
class TrimHistoryMiddleware(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        return handler(request.override(messages=trim_history(request.messages)))

    async def awrap_model_call(self, request, handler):
        return await handler(request.override(messages=trim_history(request.messages)))

# 定义一个智能体（用之前模型中的plus模型）
AI_PrivateKitchen_agent = create_agent(
    # 模型：qwen-plus
    model=chat_model,
    # 工具：搜索工具
    tools=[tavily_search],
    # 中间件：裁剪历史
    middleware=[TrimHistoryMiddleware()],
    # 系统提示词
    system_prompt=system_prompt,
    # 配置记忆体
    checkpointer=checkpointer,
)

# 流式对话
# 同步生成器：StreamingResponse 会放进线程池迭代，不阻塞事件循环
def search_recipes(prompt: str, image: str, thread_id: str):
    """调用agent搜索食谱"""
    # 不记录用户原话和图片地址
    logger.info(f"[用户]: 消息长度 {len(prompt)}, 有图片: {bool(image)}, thread_id: {thread_id}")
    try:
        # 判断是否有图片，封装不同格式的消息
        if not image or image.strip() == "":
            message = HumanMessage(content=prompt)
        else:
            message = HumanMessage(content=[
                {"type": "image", "url": image},
                {"type": "text", "text": prompt}
            ])

        # 流式调用Agent
        for chunk, metadata in AI_PrivateKitchen_agent.stream(
            {"messages": [message]},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="messages"
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content

    except Exception as e:
        logger.exception(f"[错误]: 对话失败, thread_id: {thread_id}")
        yield "信息检索失败，试试看手动输入食物列表？"

# 清空会话
def clear_messages(thread_id: str):
    """清空会话"""
    logger.info(f"清空历史消息，thread_id: {thread_id}")
    checkpointer.delete_thread(thread_id)

# 查询会话历史
def get_messages(thread_id: str) -> list[dict[str, str]]:
    """获取会话历史"""
    logger.info(f"获取历史消息，thread_id: {thread_id}")

    # 根据 thread_id 查询 checkpoint
    checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})

    # 如果不存在，返回空列表
    if not checkpoint:
        return []

    # 安全获取 messages
    channel_values = checkpoint.get("channel_values")
    if not channel_values:
        return []

    messages = channel_values.get("messages", [])
    if not messages:
        return []

    # 转换消息格式
    result = []
    for msg in messages:
        if not msg.content:
            continue

        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})

    return result
