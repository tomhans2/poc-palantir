# 开发者指南 — 动态图谱洞察沙盘 POC

> 本文档面向开发者，介绍项目结构、技术栈、依赖安装和本地开发环境搭建。

---

## 1. 项目概述

本项目是一个**领域无关的动态图谱推演沙盘**，模拟 Palantir Ontology 核心理念：

- 用户通过 **JSON 配置文件**定义知识图谱（节点、边、动作规则）
- 用户通过 **Python 文件**编写自定义动作函数（业务逻辑）
- 前端可视化图谱，支持 What-If 模拟推演，沿图拓扑传导影响
- 每次推演生成结构化洞察（多类型、多严重度的情报条目）

**切换 JSON + Python 文件即可切换任意业务沙盘场景。**

---

## 2. 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **前端框架** | React + TypeScript | React 19, TS 5.9 |
| **构建工具** | Vite | 7.x |
| **UI 组件库** | Ant Design + @ant-design/icons | Antd 6.x |
| **图谱渲染** | AntV G6 | 5.x |
| **HTTP 客户端** | Axios | 1.x |
| **后端框架** | FastAPI (Python) | 最新版 |
| **图计算引擎** | NetworkX | 最新版 |
| **数据校验** | Pydantic | 2.x |
| **文件上传** | python-multipart | 最新版 |
| **容器化** | Docker + Docker Compose + Nginx | — |

---

## 3. 目录结构

```
palantir-poc/
├── README.md                     # 项目概览
├── docs/
│   ├── DEVELOPER.md              # 本文档（开发者指南）
│   └── USER_GUIDE.md             # 使用者指南
├── start.sh                      # 一键启动脚本
├── docker-compose.yml            # Docker Compose 编排
│
├── backend/                      # Python 后端
│   ├── Dockerfile
│   ├── requirements.txt          # Python 依赖
│   ├── app/
│   │   ├── main.py               # FastAPI 应用入口（CORS、路由注册、生命周期）
│   │   ├── api/
│   │   │   └── routes.py         # REST API 路由定义
│   │   ├── engine/
│   │   │   ├── graph_engine.py   # OntologyEngine 核心引擎
│   │   │   ├── action_registry.py # ActionRegistry 函数注册表
│   │   │   └── event_queue.py    # EventQueue 推演事件历史
│   │   ├── actions/
│   │   │   ├── __init__.py       # 包初始化（空文件）
│   │   │   └── action_functions.py # 内置通用 Action 函数（L1/L2/L3）
│   │   └── models/               # Pydantic 数据模型
│   │       ├── workspace.py      # WorkspaceConfig（顶层配置）
│   │       ├── ontology.py       # OntologyDef（节点/边类型定义）
│   │       ├── graph.py          # GraphData（图数据）
│   │       ├── action.py         # Action, RippleRule, ActionEngine
│   │       └── api.py            # API 请求/响应模型
│   ├── samples/
│   │   ├── private_banking.json  # 内置示例：私行高净值客户经营沙盘
│   │   └── private_banking.py    # 示例的自定义 Action 函数
│   └── tests/                    # pytest 测试套件
│
├── frontend/                     # React 前端
│   ├── Dockerfile
│   ├── nginx.conf                # 生产环境 Nginx 配置
│   ├── package.json              # npm 依赖
│   ├── vite.config.ts            # Vite 配置（端口 5173，API 代理）
│   ├── tsconfig.json
│   └── src/
│       ├── types/index.ts        # TypeScript 接口（对齐后端 Pydantic 模型）
│       ├── services/api.ts       # API 调用封装（axios）
│       ├── hooks/
│       │   ├── useWorkspace.ts   # 全局状态管理（Context + useReducer）
│       │   └── useSimulation.ts  # 推演逻辑封装
│       └── components/
│           ├── WorkspaceProvider.tsx  # Context Provider
│           ├── Layout/AppLayout.tsx   # 三栏布局壳
│           ├── FileUploader/         # 文件上传（JSON + Python）
│           ├── GraphCanvas/          # AntV G6 图谱画布
│           ├── ControlPanel/         # 左侧控制台
│           └── InsightFeed/          # 右侧情报叙事流
│
└── scripts/                      # 辅助脚本
```

---

## 4. 环境要求

| 工具 | 最低版本 | 用途 |
|------|----------|------|
| **Python** | 3.11+ | 后端运行 |
| **Node.js** | 20+ | 前端构建 |
| **npm** | 9+ | 包管理 |
| **Docker** (可选) | 20+ | 容器化部署 |

---

## 5. 本地开发环境搭建

### 5.1 克隆项目

```bash
git clone <repo-url>
cd palantir-poc
```

### 5.2 启动后端

```bash
cd backend

# （推荐）创建 Python 虚拟环境
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（支持热重载）
uvicorn app.main:app --reload --port 8000
```

启动后可以访问：
- API 服务: http://localhost:8000
- Swagger 文档: http://localhost:8000/docs
- ReDoc 文档: http://localhost:8000/redoc

### 5.3 启动前端（新终端窗口）

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

启动后访问: http://localhost:5173

> Vite 开发服务器会自动将 `/api` 请求代理到 `http://localhost:8000`，无需额外配置。

### 5.4 一键启动（可选）

如果项目根目录有 `start.sh`，可以直接运行：

```bash
./start.sh
```

### 5.5 Docker Compose 部署（可选）

```bash
# 构建并启动
docker-compose up -d --build

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

Docker 部署后：
- 前端界面: http://localhost:3000
- API 文档: http://localhost:3000/docs（通过 Nginx 代理）
- 后端直连: http://localhost:8000

---

## 6. 后端依赖说明

`backend/requirements.txt` 内容：

| 包 | 用途 |
|------|------|
| `fastapi` | Web 框架，自动生成 OpenAPI 文档 |
| `uvicorn[standard]` | ASGI 服务器，支持热重载 |
| `pydantic>=2.0` | 数据校验与序列化 |
| `networkx` | 图数据结构与算法（有向图 DiGraph） |
| `python-multipart` | 处理 multipart/form-data 文件上传 |

### 运行测试

```bash
cd backend
pip install pytest httpx    # 测试额外依赖
python -m pytest tests/ -v
```

---

## 7. 前端依赖说明

核心依赖（`frontend/package.json`）：

| 包 | 用途 |
|------|------|
| `react` / `react-dom` | UI 框架 |
| `antd` / `@ant-design/icons` | UI 组件库与图标 |
| `@antv/g6` | 图谱可视化引擎 |
| `axios` | HTTP 客户端 |

### 构建生产版本

```bash
cd frontend
npm run build     # TypeScript 类型检查 + Vite 生产构建
npm run preview   # 预览生产构建
```

---

## 8. 核心架构

### 8.1 数据流

```
用户上传 JSON + Python
      │
      ▼
POST /api/v1/workspace/load
      │
      ├── JSON → Pydantic 校验 → WorkspaceConfig
      ├── Python → importlib 动态加载 → @register_action 函数注册
      │
      ▼
OntologyEngine.load_workspace()
      │
      ├── 构建 NetworkX DiGraph（节点 + 边）
      ├── 注册内置 Action 函数（source: builtin）
      ├── 注册自定义 Action 函数（source: custom，覆盖同名内置）
      │
      ▼
返回 {metadata, ontology_def, graph_data, actions, registered_functions, warnings}
      │
      ▼
前端 dispatch(LOAD_WORKSPACE) → 状态更新 → 图谱渲染
```

### 8.2 推演流（Simulate）

```
用户点击动作按钮
      │
      ▼
POST /api/v1/workspace/simulate {action_id, node_id}
      │
      ▼
OntologyEngine.execute_action()
      │
      ├── 1. 应用 direct_effect（直接修改目标节点属性）
      ├── 2. 遍历 ripple_rules:
      │       ├── 解析 DSL 路径（如 "<-[FACES]- Customer"）
      │       ├── 过滤匹配的邻居节点
      │       ├── 评估条件表达式
      │       ├── 调用注册的 Action 函数
      │       └── 生成结构化洞察
      │
      ▼
返回 {delta_graph, ripple_path, insights, updated_graph_data}
      │
      ▼
前端涟漪动画 → 图谱更新 → 洞察流渲染
```

### 8.3 Action 函数注册机制

函数通过 `@register_action` 装饰器标记，系统通过 `ActionRegistry` 统一管理：

1. **内置函数**（`backend/app/actions/action_functions.py`）: `set_property`, `adjust_numeric`, `update_risk_status`, `recalculate_valuation`, `compute_margin_gap`, `graph_weighted_exposure`
2. **自定义函数**（用户上传的 `.py` 文件 或 `samples/<name>.py`）: 覆盖同名内置函数

加载优先级：
- 内置函数先注册（source: `"builtin"`）
- 自定义函数后注册，自动覆盖同名内置（source: `"custom"`）

### 8.4 Vite 代理配置

`frontend/vite.config.ts` 配置了 API 代理：

```typescript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

前端所有 `/api/*` 请求自动转发到后端 `localhost:8000`。

---

## 9. API 接口总览

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/workspace/samples` | 获取可用内置示例列表 |
| POST | `/api/v1/workspace/load` | 加载工作区（JSON 文件 / 内置示例 + 可选 Python 文件） |
| POST | `/api/v1/workspace/simulate` | 执行 What-If 推演 |
| POST | `/api/v1/workspace/reset` | 重置工作区状态 |
| GET | `/api/v1/workspace/history` | 获取推演事件历史 |

完整 API 文档请启动后端后访问 http://localhost:8000/docs（Swagger UI）。

---

## 10. 常见问题

### 前端启动后显示空白页面
确认后端已启动在 `localhost:8000`。前端依赖后端 API 加载数据。

### 上传 JSON 返回 422 错误
JSON 文件缺少必填字段。必须包含 `metadata`, `ontology_def`, `graph_data`, `action_engine` 四个顶层字段。详见 [使用者指南](./USER_GUIDE.md)。

### Python 文件上传后函数未注册
确保 Python 文件中的函数使用了 `@register_action` 装饰器，并且函数签名为 `(ctx: ActionContext) -> ActionResult`。

### Docker 构建失败
确保 Docker 和 Docker Compose 已安装且版本符合要求。检查 `.dockerignore` 是否排除了不必要的文件。
