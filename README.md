<div align="center">

# 🏯 景区导览 AI 数字人系统

**第十五届中国软件杯 · A5 赛题 参赛作品**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D)](https://vuejs.org/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![ChromaDB](https://img.shields.io/badge/Chroma-FF6B6B?style=for-the-badge&logo=chroma&logoColor=white)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-Competition-blue.svg?style=for-the-badge)](#许可证)

> **基于 RAG + Live2D + 多模态交互的一站式智慧景区解决方案**

</div>

---

## 📋 目录

- [✨ 项目亮点](#-项目亮点)
- [🏗️ 系统架构](#️-系统架构)
- [🧩 功能模块](#-功能模块)
- [🛠️ 技术栈](#️-技术栈)
- [📁 项目结构](#-项目结构)
- [🚀 快速开始](#-快速开始)
  - [Docker 一键部署（推荐）](#docker-一键部署推荐)
  - [本地开发模式](#本地开发模式)
- [🔧 配置说明](#-配置说明)
- [🖥️ 访问地址](#️-访问地址)
- [💡 常见问题](#-常见问题)
- [📄 许可证](#-许可证)

---

## ✨ 项目亮点

| 亮点 | 说明 |
|------|------|
| 🎭 **Live2D 数字人** | 实时 2D 数字人渲染，支持口型同步、表情动画、动作切换 |
| 🧠 **RAG 知识增强** | 基于 ChromaDB + BGE-M3 的检索增强生成，回答有据可依 |
| 🎙️ **多模态交互** | 语音识别（Faster-Whisper）+ 语音合成（Edge-TTS）+ 文本输入 |
| 🗺️ **智能路线推荐** | 基于兴趣标签的个性化游览路线生成 + 地图可视化 |
| 📊 **运营数据大屏** | ECharts 可视化 + 游客感受度情感分析 + 知识命中统计 |
| 📚 **知识库管理** | 支持 PDF/Word/TXT/Markdown 一键上传，自动分块向量化索引 |
| 🐳 **Docker 编排** | Compose 一键部署，包含 Nginx 反向代理 + Redis 缓存 |
| 🎛️ **双端架构** | 游客端 Vue3 + 管理后台 React，各司其职 |

---

## 🏗️ 系统架构

```
                        ┌─────────────────────┐
                        │      浏览器 / H5     │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │     Nginx :80       │
                        │  ┌───────────────┐  │
                        │  │  静态前端      │  │
                        │  │  (Vue/React)   │  │
                        │  └───────┬───────┘  │
                        │          │ /api      │
                        └──────────┼──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Backend :8000      │
                        │  ┌───────────────┐  │
                        │  │   FastAPI     │  │
                        │  │  ┌─────────┐  │  │
                        │  │  │ RAG Svc │  │  │
                        │  │  ├─────────┤  │  │
                        │  │  │ ASR/TTS │  │  │
                        │  │  ├─────────┤  │  │
                        │  │  │ Avatar  │  │  │
                        │  │  └─────────┘  │  │
                        │  └───────┬───────┘  │
                        └──────────┼──────────┘
                    ┌──────────────┼──────────────┐
           ┌────────▼────────┐   ┌─▼──────────┐  ┌──────────────┐
           │  Redis :6379    │   │  SQLite    │  │  ChromaDB    │
           │  会话记忆缓存    │   │  业务数据  │  │  向量知识库  │
           └─────────────────┘   └────────────┘  └──────────────┘
```

| 服务 | 职责 | 对外端口 |
|------|------|----------|
| **Nginx** | 静态资源托管 + 反向代理 + 负载均衡 | `80` |
| **Backend** | FastAPI 服务：RAG / ASR / TTS / 数字人驱动 / 推荐算法 | 内部 `8000` |
| **Redis** | 会话记忆缓存、热点数据 | 内部 `6379` |
| **SQLite** | 用户、知识库、日志等业务数据持久化 | 本地文件 |
| **ChromaDB** | 景区知识向量化存储与检索 | 本地文件 |

---

## 🧩 功能模块

### 👥 游客交互端 (C 端)

| 模块 | 功能 | 核心能力 |
|------|------|----------|
| **M1 · 数字人交互** | 🎬 形象渲染 · 👄 口型同步 · 😊 表情驱动 · 🔊 语音播放 · 💬 字幕同步 | Live2D + WebSocket |
| **M2 · 多模态输入** | ⌨️ 文本输入 · 🎤 按住说话 · 🔄 模式切换 · 🌐 多语言支持 | Faster-Whisper 流式识别 |
| **M3 · 智能问答** | 🧠 景区问答 · 📚 RAG 增强 · 🔗 多轮上下文 · 📌 来源引用 · 🎭 情感化回复 | BGE-M3 + LLM |
| **M4 · 个性推荐** | 🏷️ 兴趣偏好 · 🗺️ 路线生成 · ⏱️ 时长估算 · 📍 POI 可视化 · 🚶 避堵优化 | 标签匹配算法 |

### 🛠️ 管理后台 (B 端)

| 模块 | 功能 | 核心能力 |
|------|------|----------|
| **M5 · 知识库管理** | 📤 文档上传 · ✂️ 自动分块 · 📝 FAQ 维护 · 🔍 命中测试 · 🔄 重建索引 | ChromaDB + BGE-M3 |
| **M6 · 数字人配置** | 👤 形象选择 · 👕 服装配饰 · 🎵 音色试听 · ⚡ 语速调节 · 👋 欢迎语 | 在线配置 + 实时预览 |
| **M7 · 感受度分析** | 📈 情感趋势 · ☁️ 热词词云 · 📊 话题分类 | 情感分析模型 |
| **M8 · 数据大屏** | 📉 流量统计 · 💬 对话热力 · 📚 知识命中 · 🏆 运营排行 | ECharts 可视化 |

---

## 🛠️ 技术栈

### 🔙 后端

| 类别 | 技术选型 |
|------|----------|
| **Web 框架** | FastAPI + Uvicorn (ASGI) |
| **ORM / 数据库** | SQLAlchemy 2.0 + SQLite / aiosqlite |
| **向量库** | ChromaDB |
| **嵌入模型** | `BAAI/bge-m3` (Sentence-Transformers) |
| **LLM 推理** | OpenAI 兼容接口（DeepSeek / 本地模型均可接入） |
| **语音识别** | Faster-Whisper |
| **语音合成** | Edge-TTS |
| **缓存** | Redis |
| **认证** | python-jose (JWT) + passlib (bcrypt) |
| **文档解析** | PyPDF2 + python-docx + openpyxl + pandas |

### 💻 游客端 (Vue 3)

| 类别 | 技术选型 |
|------|----------|
| **框架** | Vue 3 + TypeScript + Vite |
| **状态管理** | Pinia |
| **样式** | Tailwind CSS |
| **数字人** | PixiJS + pixi-live2d-display |
| **地图** | Leaflet |
| **视频流** | flv.js |
| **HTTP** | Axios |

### 🎛️ 管理后台 (React 18)

| 类别 | 技术选型 |
|------|----------|
| **框架** | React 18 + TypeScript + Vite |
| **UI 组件库** | Ant Design 5 |
| **路由** | React Router 6 |
| **图表可视化** | ECharts 5 + echarts-for-react |
| **词云** | echarts-wordcloud |
| **图标** | @ant-design/icons |
| **HTTP** | Axios |

### 🐳 部署 / 运维

- **Docker Compose** 编排
- **Nginx** 多阶段构建 + 反向代理
- 数据卷持久化（SQLite / Chroma / Redis / HF Cache）

---

## 📁 项目结构

```
软件/
├── 53014670源码/                     # 项目核心源码
│   ├── backend/                       # 🔙 FastAPI 后端
│   │   ├── app/
│   │   │   ├── api/v1/                # 路由：chat/asr/tts/recommend/admin
│   │   │   ├── core/                  # 配置、数据库、依赖注入、安全
│   │   │   ├── models/                # SQLAlchemy 模型
│   │   │   ├── schemas/               # Pydantic 数据模型
│   │   │   ├── services/              # 业务服务层 (RAG/ASR/TTS/Avatar...)
│   │   │   └── utils/                 # 通用工具
│   │   ├── data/
│   │   │   ├── scenic_docs/           # 景区文档（PDF/Word/TXT...）
│   │   │   ├── chroma_db/             # Chroma 向量库（git 忽略）
│   │   │   └── tts_cache/             # TTS 音频缓存（git 忽略）
│   │   ├── scripts/                   # 数据处理脚本
│   │   ├── Dockerfile
│   │   ├── docker_init.py             # 容器启动时向量库初始化
│   │   ├── init_vector_store.py       # 手动索引脚本
│   │   ├── requirements.txt
│   │   └── main.py
│   │
│   ├── web-client/                    # 💻 游客端（Vue 3）
│   │   ├── public/live2d/             # Live2D 模型资源
│   │   ├── src/
│   │   │   ├── components/            # AvatarDisplay / ChatInterface 等
│   │   │   ├── composables/           # useLive2D 等组合函数
│   │   │   ├── stores/                # Pinia 状态
│   │   │   ├── services/              # API 服务
│   │   │   └── utils/                 # 工具函数
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── admin-web/                     # 🎛️ 管理后台（React 18）
│   │   ├── src/
│   │   │   ├── layouts/AdminLayout.tsx
│   │   │   └── pages/                 # Dashboard / KnowledgeManage / SentimentAnalysis
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── docker/                        # 🐳 部署配置
│   │   └── nginx/                     # Nginx Dockerfile + nginx.conf
│   ├── 示范景区公开资料包/              # 📚 官方知识库资料
│   ├── 口型同步/                       # 参考实现（Live2d-TTS-Audio-LipSync）
│   ├── docker-compose.yml
│   ├── deploy.ps1                     # Windows 一键部署脚本
│   ├── deploy.sh                      # Linux/macOS 一键部署脚本
│   └── README.md                      # 部署指南
│
├── 53014670介绍/                       # 📑 项目介绍、功能规格书、演示视频
├── 53014670报名/                       # 📝 报名资料
├── .gitignore                          # 根目录忽略规则
└── README.md                           # 👈 本文件
```

---

## 🚀 快速开始

### Docker 一键部署（推荐）

> 适用于 Windows / Linux / macOS，3 分钟启动整套服务。

#### 前置要求

- **Docker** 20.10+ 与 **Docker Compose** v2
- 磁盘空间 ≥ **8 GB**（含 PyTorch + BGE-M3 嵌入模型）
- 内存 ≥ **4 GB**

#### 步骤

**① 配置环境变量**

```powershell
# Windows PowerShell
cd 53014670源码
Copy-Item backend\.env.example backend\.env
# 然后编辑 backend\.env 填入你的密钥（如 DeepSeek API Key）
```

```bash
# Linux / macOS
cd 53014670源码
cp backend/.env.example backend/.env
```

**② 一键启动**

```powershell
# Windows PowerShell（推荐）
.\deploy.ps1
```

```bash
# Linux / macOS / Git Bash
chmod +x deploy.sh
./deploy.sh
```

脚本会自动：检查 Docker → 生成配置 → 同步资料 → 构建镜像 → 启动服务 → 初始化向量库。

> ⏳ **首次启动较慢**：需要下载 `BAAI/bge-m3` 模型（约 5~15 分钟），可用 `docker compose logs -f backend` 查看进度。

---

### 本地开发模式

不使用 Docker，分别启动各服务。

#### 🔙 后端

```bash
cd 53014670源码/backend
pip install -r requirements.txt
cp .env.example .env        # Windows: Copy-Item
python init_vector_store.py  # 初始化向量库
python main.py               # 启动：http://localhost:8000
```

#### 💻 游客端

```bash
cd 53014670源码/web-client
npm install
npm run dev      # http://localhost:5173
```

#### 🎛️ 管理后台

```bash
cd 53014670源码/admin-web
npm install
npm run dev      # http://localhost:5174
```

---

## 🔧 配置说明

### `backend/.env` 关键项

| 变量 | 示例值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `openai` / `mock` | 大模型提供商，mock 用于无 API Key 时演示 |
| `LLM_API_KEY` | `sk-xxxxxx` | DeepSeek / OpenAI 兼容 API Key |
| `LLM_API_BASE` | `https://api.deepseek.com/v1` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `ADMIN_API_TOKEN` | 自定义强密码 | 管理后台 API 鉴权 Token |
| `ADMIN_USERNAME` | `admin` | 管理后台登录用户名 |
| `ADMIN_PASSWORD` | 自定义 | 管理后台登录密码 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 向量嵌入模型（建议保持默认） |
| `ASR_PROVIDER` | `faster-whisper` | 语音识别引擎 |
| `TTS_VOICE` | `zh-CN-XiaoxiaoNeural` | 语音合成音色 |

### `deploy.sh` / `deploy.ps1` 常用参数

```bash
./deploy.sh              # 构建并启动（默认）
./deploy.sh --reindex    # 资料更新后强制重建向量索引
./deploy.sh --reset      # 清空向量库后完全重建
./deploy.sh --down       # 停止容器（保留数据卷）
./deploy.sh --logs       # 实时跟踪日志
```

---

## 🖥️ 访问地址

部署完成后，可通过以下地址访问各服务：

| 服务 | 地址 | 默认凭据 / Token |
|------|------|-------------------|
| **游客端 (C 端)** | http://localhost/ | — |
| **管理后台 (B 端)** | http://localhost/admin/ | `admin` / 自定义密码 |
| **API 文档 (Swagger)** | http://localhost/docs | — |
| **健康检查** | http://localhost/health | — |
| **管理后台 API Token** | — | `scenic-admin-token-2026`（或自定义） |

---

## 💡 常见问题

### ❓ 构建 Docker 镜像时连接 registry.docker.io 超时？

配置 Docker 镜像加速：打开 **Docker Desktop → Settings → Docker Engine**，添加：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
  ]
}
```

点击 **Apply & Restart** 后重新部署。

### ❓ 首次启动 backend 一直 restarting？

大概率是向量库初始化或模型下载中。查看日志确认：

```bash
docker compose logs backend
```

同时确保 Docker Desktop 分配的内存 ≥ **4GB**。

### ❓ 更新了示范景区资料包，如何重建知识库？

```bash
./deploy.sh --reindex        # 增量式重建
./deploy.sh --reset          # 完全清空后重建
```

### ❓ 如何接入 DeepSeek / Kimi / 本地大模型？

所有 OpenAI 兼容接口均可一键接入，示例（DeepSeek）：

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

保存后 `docker compose restart backend` 即可。

### ❓ Windows 下 `.sh` 脚本无法执行？

使用 PowerShell 版本：

```powershell
.\deploy.ps1
```

或使用 Git Bash 执行 `bash deploy.sh`。

---

## 📄 许可证

本项目为 **第十五届中国软件杯 A5 赛题** 参赛代码。

- 项目源代码：仅供学习交流与竞赛评审使用
- 示范景区资料包：版权归大赛主办方所有
- Live2D 模型资源：版权归各原作者所有

---

<div align="center">

**如果本项目对你有帮助，欢迎点个 ⭐ Star 支持一下！**

Made with ❤️ using FastAPI · Vue · React · Docker

</div>
