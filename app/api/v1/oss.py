import alibabacloud_oss_v2 as oss
from fastapi import APIRouter, HTTPException
from datetime import timedelta
import os
import uuid
# 加载环境变量
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

# 从环境变量中加载凭证信息，用于身份验证
credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()

# 加载SDK的默认配置，并设置凭证提供者
cfg = oss.config.load_default()
cfg.credentials_provider = credentials_provider

# 方式一：只填写Region（推荐）
# 必须指定Region ID，SDK会根据Region自动构造HTTPS访问域名
cfg.region = 'cn-beijing'

# 使用配置好的信息创建OSS客户端
client = oss.Client(cfg)

# OSS 域名配置
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
OSS_BUCKET = os.getenv("OSS_BUCKET")
# 上传目录及其访问地址前缀，chat接口用后者校验image_url
UPLOAD_DIR = "uploads/"
UPLOAD_URL_PREFIX = f"https://{OSS_BUCKET}.{OSS_ENDPOINT}/{UPLOAD_DIR}"


@router.get("/oss/presign")
def chat_endpoint(filename: str):
    # 根据文件扩展名判断 Content-Type
    content_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    if ext not in content_type_map:
        raise HTTPException(status_code=400, detail="仅支持 jpg/jpeg/png/gif/webp 图片")
    content_type = content_type_map[ext]

    # key 由服务端生成，客户端传来的文件名只用来取扩展名，避免覆盖桶内已有对象
    name = f"{uuid.uuid4().hex}.{ext}"

    pre_result = client.presign(oss.PutObjectRequest(
        bucket=OSS_BUCKET,
        key=UPLOAD_DIR + name,
        content_type=content_type,
    ), expires=timedelta(seconds=300))

    # 返回上传 URL 和可访问的图片路径
    return {
        "uploadUrl": pre_result.url.strip('"'),
        "contentType": content_type,
        "accessUrl": UPLOAD_URL_PREFIX + name
    }
