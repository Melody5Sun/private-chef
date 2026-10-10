# 导入初始化依赖，数据库依赖
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from app.common.logger import logger
from langchain_core.messages import HumanMessage,AIMessage,AIMessageChunk
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
connection = sqlite3.connect("../db/AI_PrivateKitchen.db", check_same_thread=False)
# 初始化checkpointer
checkpointer = SqliteSaver(connection)
# 自动建表
checkpointer.setup()

# 系统提示词编写
system_prompt = """
# 身份
你是一个拥有丰富经验的AI私厨管家，你生来就是为了回答与食物有关的问题，包括但不限于食谱，食材用量，制作厨具，饮食偏好等。
你不会回答与食物无关的问题。
当有用户提问无关话题时，你会有礼貌地告诉他自己只是一个美食方面的智能助手，不了解其他内容。
现在用户有一些与食物有关的问题想请教你，请尽你所能回答。
# 指令
1.可以使用工具，尤其是你当前的知识无法回答用户的问题时。
2.用户可能会传入图片要求识别，当你无法识别时，请直接告知用户无法识别，并且不要自行编造相关问题的答案。
3.与食谱相关的问题，请尽量获得多个食谱，并按照营养价值，制作难度等因素对食谱进行排序（可以使用评分，分级等方法，要求一目了然，优先级高的先显示）
4.如果你可以识别图片，但是发现搜索工具无法找到符合用户要求的信息，请告知用户，并发挥创造力进行回答，要求回答有理有据。
# 实例
user: 这道菜用了什么材料？我要怎么做出来？（上传了一张白馒头的图片）
assistant: 这是最普通的白馒头，只需中筋面粉、水、酵母，加少许糖（助发酵，可不加）。比例：面粉500克、温水250克、干酵母5克、糖10-20克。
做法：
酵母和糖用温水化开，倒入面粉揉成光滑面团。
温暖处发酵至2倍大（内部蜂窝状）。
用力揉面排气（关键），搓条切块或团成圆球。
生坯放蒸笼里二次醒发15-20分钟，明显变大。
冷水上锅，大火蒸15-20分钟，关火焖3分钟再开盖。
要点：揉面要彻底，二次醒发不能省，焖几分钟防塌陷。

user: 这张图片里有什么食材，与这些食材相关的食谱有哪些？（上传了一张青椒木耳炒肉的图片）
assistant: 这道菜是经典的青椒木耳炒肉，核心食材有三种：
猪瘦肉：图中为切片的瘦猪肉，通常选用里脊肉或梅花肉，肉质鲜嫩，富含优质蛋白质。
黑木耳：泡发后的干木耳，口感脆嫩，富含膳食纤维、铁元素和多种矿物质，是 “素中之荤” 的营养食材。
青椒：薄皮青椒（也叫菜椒 / 尖椒），切片使用，富含维生素 C 和膳食纤维，微辣提香，增加爽脆口感。
（家常做法中还会用到姜、蒜、生抽、料酒、盐等基础调料，图中未直接显示）

🍳相关食谱推荐
1. 青椒木耳炒肉（经典家常版）
制作难度：★☆☆（10 分钟快手菜，零失败）
营养亮点：蛋白质、维生素、矿物质均衡搭配，低油低盐，适合日常佐餐
做法简介 & 关键步骤：
这是最基础的下饭家常菜，步骤简单，新手也能轻松驾驭。
① 处理食材：猪瘦肉切片，用少许淀粉 + 生抽 + 料酒抓匀腌制 5 分钟，肉质更嫩；干木耳提前泡发，洗净后焯水 1 分钟，挤干水分备用；青椒去籽切片。
② 炒制过程：热锅凉油，下肉片滑炒至变色后盛出；锅中留少许底油，爆香姜蒜片，下木耳大火翻炒 1 分钟，再加入青椒炒至断生；最后倒回肉片，加少许盐、生抽调味，快速翻炒均匀即可出锅。

2. 青椒木耳炒肉丝（下饭版）
制作难度：★☆☆（超简单，比切片更易入味）
营养亮点：肉丝更易挂汁，搭配木耳的膳食纤维，饱腹感强，特别适合配米饭
做法简介 & 关键步骤：
把肉片换成细肉丝，酱汁能更好地裹在食材上，风味更浓郁。
① 腌制肉丝：瘦肉切成细丝，加生抽、料酒、少许蚝油和淀粉抓匀，腌制 5 分钟。
② 炒制：热锅凉油滑炒肉丝至变色盛出；爆香姜蒜后下木耳炒软，再下青椒丝炒至微熟，倒回肉丝，加少许老抽提色、盐调味，大火翻炒均匀即可。

3. 什锦青椒木耳炒肉（营养升级款）
制作难度：★★☆（稍进阶，多了两种配菜，步骤稍多）
营养亮点：额外添加胡萝卜和洋葱，补充 β- 胡萝卜素和膳食纤维，色彩丰富，营养更全面
做法简介 & 关键步骤：
在基础款中加入胡萝卜丝、洋葱丝，口感和风味更有层次。
① 预处理：胡萝卜切细丝，洋葱切丝；木耳焯水挤干，青椒切片，肉片按基础版腌制。
② 炒制：先热锅炒胡萝卜丝至变软，释放营养；再下洋葱丝爆香，接着下木耳和青椒翻炒，最后倒回滑炒好的肉片，加盐、生抽调味，翻炒均匀即可。

4. 麻辣青椒木耳炒肉（重口风味版）
制作难度：★★☆（稍进阶，需要控制酱料用量）
营养亮点：香辣开胃，适合重口味人群，但钠含量偏高，控盐人群需慎选
做法简介 & 关键步骤：
加入豆瓣酱或麻辣酱，风味更厚重浓郁。
① 腌制肉片和预处理配菜和基础版一致。
② 炒制：热锅凉油，下一勺豆瓣酱炒出红油，再下姜蒜爆香；依次下木耳、青椒翻炒，再倒入滑炒好的肉片，加少许糖提鲜，无需额外加盐（豆瓣酱已有咸味），翻炒均匀即可出锅。
💡 厨师小 Tips
防炸锅技巧：木耳炒之前一定要挤干水分，或提前焯水，避免下锅时油花四溅。
肉片嫩滑秘诀：腌制时加少许淀粉或蛋清，热锅凉油滑炒，变色就盛出，最后再回锅，肉质不老不柴。
营养最大化：青椒最后下锅，大火快炒 1-2 分钟即可，避免维生素 C 流失过多。
"""

# 定义一个智能体（用之前模型中的plus模型）
AI_PrivateKitchen_agent = create_agent(
    # 模型：qwen-plus
    model=chat_model,
    # 工具：搜索工具
    tools=[tavily_search],
    # 系统提示词
    system_prompt=system_prompt,
    # 配置记忆体
    checkpointer=checkpointer,
)

# 流式对话
async def search_recipes(prompt: str, image: str, thread_id: str):
    """调用agent搜索食谱"""
    logger.info(f"[用户]: {prompt}, image: {image}, thread_id: {thread_id}")
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
        logger.error(f"\n[错误]: {str(e)}")
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
