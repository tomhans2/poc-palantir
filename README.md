# 动态图谱洞察沙盘 POC (Palantir Ontology Simulator)

模拟 Palantir 核心理念的动态业务推演沙盘。上传 JSON 知识图谱文件，后端 OntologyEngine 解析图拓扑并通过可注入的 Python Action 函数执行涟漪推演，前端自适应渲染三栏布局（控制台 + 图谱画布 + 情报叙事流），支持 What-If 模拟与结构化多类型智能洞察输出。

**系统完全领域无关** — 切换 JSON 即可切换业务沙盘。

## 架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                         Browser (5173)                           │
│  ┌────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ControlPanel│  │   GraphCanvas    │  │    InsightFeed       │ │
│  │  - 属性面板 │  │  (AntV G6 5.x)  │  │  - 结构化洞察流      │ │
│  │  - 动作按钮 │  │  - 力导向布局     │  │  - 按类型/严重度渲染  │ │
│  │  - 图例     │  │  - 涟漪动画      │  │  - 联动高亮          │ │
│  └────────────┘  └──────────────────┘  └──────────────────────┘ │
│                React 19 + TypeScript + Ant Design 6              │
└───────────────────────────┬──────────────────────────────────────┘
                            │  Vite Proxy /api → :8000
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (8000)                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ REST API: /load  /simulate  /reset  /history  /samples     │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              OntologyEngine (核心引擎)                     │    │
│  │  NetworkX DiGraph · DSL 路径解析 · 条件求值 · 涟漪传导     │    │
│  └──────────┬───────────────────┬───────────────────────────┘    │
│             ▼                   ▼                                 │
│  ┌──────────────────┐  ┌──────────────────────┐                  │
│  │  ActionRegistry  │  │    EventQueue        │                  │
│  │  @register_action│  │  模拟事件历史记录     │                  │
│  │  函数注入 + 覆盖  │  │                      │                  │
│  └──────────────────┘  └──────────────────────┘                  │
│  Pydantic 2.x 数据模型 · Python Action 函数 (L1/L2/L3 三层智能) │
└──────────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + Vite 7 |
| UI 组件库 | Ant Design 6 + @ant-design/icons |
| 图谱渲染 | AntV G6 5.x (力导向布局 + 涟漪动画) |
| 后端 | Python 3.11+ + FastAPI |
| 图计算 | NetworkX (有向图) |
| 数据校验 | Pydantic 2.x |
| API 文档 | Swagger UI (FastAPI 自动生成) |
| 容器化 | Docker + Docker Compose + Nginx |

## 快速开始

### 前提条件

- Python 3.11+
- Node.js 20+
- npm 9+

### 方式一：一键启动 (推荐)

```bash
# 克隆仓库
git clone <repo-url>
cd palantir-poc

# 一键启动前后端
./start.sh
```

启动后访问：
- 前端界面: http://localhost:5173
- API 文档 (Swagger): http://localhost:8000/docs

### 方式二：手动分别启动

**启动后端：**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**启动前端（新终端窗口）：**

```bash
cd frontend
npm install
npm run dev
```

### 方式三：Docker Compose 部署 (无需本地环境)

```bash
# 构建并启动
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

启动后访问：
- 前端界面: http://localhost:3000
- API 文档 (Swagger): http://localhost:3000/docs (通过 nginx 代理)
- 后端直连: http://localhost:8000

自定义端口 (通过 `.env` 文件):

```bash
# .env
FRONTEND_PORT=8080
BACKEND_PORT=9000
```

停止并清理：

```bash
docker-compose down
```

### 使用流程

1. 浏览器访问 http://localhost:5173
2. 从下拉选择器选择内置示例 `private_banking`，或拖拽上传自定义 JSON（可同时上传配套 Python 动作文件）
3. 点击图谱节点查看属性，选中 Event 节点后点击动作按钮执行 What-If 模拟
4. 观察涟漪传导动画和右侧结构化情报洞察

## 目录结构

```
palantir-poc/
├── README.md                  # 本文件
├── start.sh                   # 一键启动脚本
├── docker-compose.yml         # Docker Compose 编排
├── backend/
│   ├── README.md              # 后端文档
│   ├── Dockerfile             # 后端容器镜像
│   ├── .dockerignore
│   ├── requirements.txt       # Python 依赖
│   ├── app/
│   │   ├── main.py            # FastAPI 入口 (CORS, 路由注册)
│   │   ├── api/
│   │   │   └── routes.py      # REST API 路由 (/load, /simulate, /reset, /history, /samples)
│   │   ├── engine/
│   │   │   ├── graph_engine.py    # OntologyEngine 核心引擎
│   │   │   ├── action_registry.py # ActionRegistry 函数注册表
│   │   │   └── event_queue.py     # EventQueue 事件队列
│   │   ├── actions/
│   │   │   └── action_functions.py # L1/L2/L3 三层智能函数
│   │   └── models/                # Pydantic 数据模型
│   │       ├── ontology.py        # NodeTypeDef, EdgeTypeDef, OntologyDef
│   │       ├── graph.py           # GraphNode, GraphEdge, GraphData
│   │       ├── action.py          # Action, RippleRule, ActionEngine
│   │       ├── workspace.py       # Metadata, WorkspaceConfig
│   │       └── api.py             # SimulateRequest/Response, InsightItem
│   ├── samples/
│   │   ├── private_banking.json  # 内置示例：私行高净值客户经营沙盘
│   │   └── private_banking.py    # 私行领域自定义 Action 函数
│   └── tests/                 # pytest 测试套件
├── frontend/
│   ├── README.md              # 前端文档
│   ├── Dockerfile             # 前端容器镜像 (多阶段构建)
│   ├── .dockerignore
│   ├── nginx.conf             # Nginx 反向代理配置
│   ├── package.json
│   ├── vite.config.ts         # Vite 配置 (端口 5173, API 代理)
│   └── src/
│       ├── types/index.ts     # TypeScript 类型定义 (对齐后端模型)
│       ├── services/api.ts    # API 调用封装 (axios)
│       ├── hooks/
│       │   ├── useWorkspace.ts    # 全局状态管理 (Context + useReducer)
│       │   └── useSimulation.ts   # 推演逻辑封装
│       └── components/
│           ├── Layout/AppLayout.tsx    # 三栏布局壳
│           ├── FileUploader/          # 文件上传 + 示例选择
│           ├── GraphCanvas/           # AntV G6 图谱画布
│           ├── ControlPanel/          # 左侧控制台
│           └── InsightFeed/           # 右侧情报叙事流
└── scripts/                   # 开发脚本与工具
```

## API 接口摘要

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/workspace/samples` | 获取可用示例列表 |
| POST | `/api/v1/workspace/load` | 加载知识图谱 (文件上传或内置示例) |
| POST | `/api/v1/workspace/simulate` | 执行 What-If 推演 |
| POST | `/api/v1/workspace/reset` | 重置工作区状态 |
| GET | `/api/v1/workspace/history` | 获取推演历史 |

完整 API 文档请访问 http://localhost:8000/docs (Swagger UI)。

## 核心概念

- **知识图谱 (Ontology)**: JSON 定义节点类型、边类型及其视觉样式
- **Action 函数**: 通过 `@register_action` 装饰器注入的业务逻辑函数
- **涟漪传导 (Ripple)**: 按 DSL 路径 (如 `<-[EDGE_TYPE]- NodeType`) 沿图拓扑传播影响
- **三层智能**: L1 数据层 (属性更新) → L2 信息层 (计算推导) → L3 智能层 (图拓扑分析)
- **结构化洞察 (Insight)**: 每次推演生成多类型、多严重度的情报条目

## 文档

- [开发者指南](docs/DEVELOPER.md) — 项目结构、技术栈、环境搭建、本地运行
- [使用者指南](docs/USER_GUIDE.md) — JSON/Python 编写规范、上传操作、推演使用

## License

Private / POC
