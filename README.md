# AI 私厨：美食识别与食谱推荐

> 上传美食图片及问题，AI 自动识别食材并根据用户要求回答问题。

## 项目简介

AI 私厨是一个基于大模型的后端应用，系统可以根据用户上传的图片完成如下功能：
- 识别图片中的主要食材
- 分析烹饪方法
- 推荐相关食谱（支持网络搜索）

本项目后端使用 **LangChain** 框架构建智能体，调用通义千问多模态模型（Qwen-3.5-plus）进行图像识别，并集成 Tavily 搜索工具获取食谱信息。

## 技术栈

- **语言**：Python 3.13.7
- **框架**：LangChain 1.3+, FastAPI
- **大模型**：通义千问 Qwen-3.5-plus和Qwen-3.5-flash（通过 DashScope API）
- **依赖管理**：uv
- **工具集成**：Tavily Search API

## 本地运行

由于没有购买和配置CDN服务，因此该代码目前无法直接通过网址访问，但是可以通过免费注册阿里云账号，添加用户，创建Bucket来实现本地的网页访问。
如果不想注册阿里云使用，可以在notebooks文件夹内找到可在编译器上运行的版本。

### 环境要求
- Python 3.10 或更高版本
- uv (推荐) 

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/QHzzy035/AI-PrivateKitchen.git
   cd AI-PrivateKitchen
