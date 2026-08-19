# 景区导览 AI 数字人 — 部署指南

第十五届中国软件杯 · A5 赛题 — 基于 Docker Compose 的一键部署方案。

---

## 架构概览

```
                    ┌─────────────┐
  浏览器 ──────────►│   Nginx:80  │
                    │  静态前端    │
                    │  反向代理    │
                    └──────┬──────┘
                           │ /api  /static
                    ┌──────▼──────┐     ┌─────────┐
                    │ Backend:8000│────►│  Redis  │
                    │ FastAPI     │     └─────────┘
                    │ uvicorn     │
                    └─────────────┘
                           │
                    SQLite + Chroma
                    （持久化数据卷）
```

| 服务 | 说明 | 对外端口 |
|------|------|----------|
| **nginx** | 游客端 Vue + 管理后台 React 静态资源；反向代理 API | 80 |
| **backend** | FastAPI + uvicorn；RAG / ASR / TTS | 内部 8000 |
| **redis** | 会话记忆缓存 | 内部 6379 |

---

## 前置要求

- **Docker** 20.10+
- **Docker Compose** v2（`docker compose` 命令）
- **Bash**（Linux / macOS 原生；Windows 请用 **Git Bash** 或 **WSL2**）
- 磁盘空间 ≥ **8 GB**（含 PyTorch、嵌入模型 `BAAI/bge-m3`）
- 内存建议 ≥ **4 GB**

---

## 快速开始

### 1. 准备示范景区资料包

将[官方示范景区公开资料包](https://www.cnsoftbei.com/uploadfile/2026/0323/20260323113204906.zip)解压到项目根目录：

```
A5/
├── 示范景区公开资料包/    ← 资料放这里（支持 .txt / .md / .pdf / .docx）
├── backend/
├── web-client/
├── admin-web/
├── deploy.sh
└── docker-compose.yml
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，**Docker 部署至少关注以下项**：

| 变量 | Docker 推荐值 | 说明 |
|------|---------------|------|
| `LLM_PROVIDER` | `mock` 或 `openai` | 大模型提供商 |
| `LLM_API_KEY` | 你的 API Key | 使用 DeepSeek 等时必填 |
| `LLM_API_BASE` | `https://api.deepseek.com/v1` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `ADMIN_API_TOKEN` | 自定义强密码 | 管理后台 API 鉴权 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 自定义 | 管理后台登录 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 向量嵌入模型（默认即可） |
| `ASR_PROVIDER` | `faster-whisper` | 语音识别 |
| `TTS_VOICE` | `zh-CN-XiaoxiaoNeural` | 语音合成音色 |

> Docker Compose 会自动覆盖 `REDIS_HOST`、`REDIS_URL`、`DATABASE_URL`、`CORS_ORIGINS` 等容器内网络配置，无需手动修改。

可选：在项目根目录创建 `.env` 供 Compose 使用：

```bash
# .env（项目根目录，可选）
HTTP_PORT=80
PUBLIC_BASE_URL=http://localhost
FORCE_REINDEX=false
RESET_INDEX=false
```

### 3. 一键部署

**Windows PowerShell（推荐）：**

```powershell
cd C:\Users\Lenovo\Desktop\A5
.\deploy.ps1
```

> PowerShell **不需要** `chmod`，直接运行即可。若提示无法执行脚本，先运行：
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Linux / macOS / Git Bash：**

```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会自动：

1. 检查 Docker 环境
2. 生成 `backend/.env`（若不存在）
3. 将 `示范景区公开资料包/` 同步到 `backend/data/scenic_docs/`
4. 构建镜像并启动 Redis、Backend、Nginx
5. **容器启动时**执行向量库初始化（下载嵌入模型 + 建立 Chroma 索引）

### 4. 访问地址

| 页面 | URL |
|------|-----|
| 游客端（AI 数字人） | http://localhost/ |
| 管理后台 | http://localhost/admin/ |
| API 文档 | http://localhost/docs |
| 健康检查 | http://localhost/health |

管理后台默认 Token（与 `backend/.env` 中 `ADMIN_API_TOKEN` 一致）：

```
scenic-admin-token-2026
```

---

## deploy.sh 常用命令

```bash
./deploy.sh              # 构建并启动（默认）
./deploy.sh --reindex    # 资料更新后，强制重建向量索引
./deploy.sh --reset      # 清空向量库后完全重建
./deploy.sh --down       # 停止容器（保留数据卷）
./deploy.sh --logs       # 跟踪日志
./deploy.sh --help       # 帮助
```

---

## 向量库初始化说明

初始化在 **backend 容器首次启动** 时自动执行（`docker_init.py`）：

1. 从挂载目录 `/demo-materials`（即宿主机 `示范景区公开资料包/`）同步文件
2. 扫描 `data/scenic_docs/` 下所有 `.txt` / `.md` / `.pdf` / `.docx`
3. 分块（500 字 / 重叠 50）并向量化写入 Chroma

**首次启动较慢**（需下载 `BAAI/bge-m3` 模型，约 5~15 分钟），可通过日志查看进度：

```bash
docker compose logs -f backend
```

手动在容器内重建索引：

```bash
docker compose exec backend python init_vector_store.py --reset
```

---

## 数据持久化

| 数据卷 | 内容 |
|--------|------|
| `backend_data` | SQLite 数据库、Chroma 向量库、TTS 缓存、上传文件 |
| `redis_data` | Redis 会话数据 |
| `hf_cache` | HuggingFace 模型缓存 |

删除所有数据（慎用）：

```bash
docker compose down -v
```

---

## 本地开发（非 Docker）

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env
python init_vector_store.py
python main.py

# 游客端
cd web-client && npm install && npm run dev    # :5173

# 管理后台
cd admin-web && npm install && npm run dev    # :5174
```

---

## 常见问题

### Q: 构建时报 `failed to fetch anonymous token` / 连接 registry.docker.io 超时？

**原因：** 无法访问 Docker Hub（国内网络或防火墙常见）。

**解决（推荐）：配置镜像加速**

1. 打开 **Docker Desktop → Settings → Docker Engine**
2. 在 JSON 中加入 `registry-mirrors`（可参考项目内 `docker/daemon-mirror.example.json`）：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
  ]
}
```

3. 点击 **Apply & Restart**
4. 重新运行 `.\deploy.ps1`

也可尝试：切换网络、开 VPN，或改用下方「本地开发」方式不依赖 Docker。

### Q: 首次启动 backend 一直 restarting？

向量库初始化或模型下载中。查看日志：

```bash
docker compose logs backend
```

若内存不足，请确保 Docker 分配 ≥ 4GB RAM。

### Q: 更新了示范资料包如何重新索引？

```bash
./deploy.sh --reindex
```

### Q: Windows 下 deploy.sh 无法执行？

使用 **Git Bash** 或 **WSL**：

```bash
bash deploy.sh
```

### Q: 如何更换对外端口？

在项目根 `.env` 中设置：

```
HTTP_PORT=8080
```

然后重新 `./deploy.sh`。

### Q: 如何接入 DeepSeek？

编辑 `backend/.env`：

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-你的密钥
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

重启 backend：

```bash
docker compose restart backend
```

---

## 项目结构

```
A5/
├── deploy.sh                 # 一键部署脚本
├── docker-compose.yml        # Compose 编排
├── docker/nginx/             # Nginx 配置与多阶段构建
├── 示范景区公开资料包/        # 官方知识库资料（需自行下载）
├── backend/                  # FastAPI 后端
│   ├── Dockerfile
│   ├── docker-entrypoint.sh  # 启动：初始化 + uvicorn
│   ├── docker_init.py        # 资料同步 + 向量库索引
│   └── init_vector_store.py  # 手动索引脚本
├── web-client/               # 游客端 Vue3
└── admin-web/                # 管理后台 React
```

---

## 许可证

本项目为软件杯竞赛参赛代码，示范景区资料包版权归主办方所有。
