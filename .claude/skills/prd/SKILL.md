---
name: prd
description: "动态图谱洞察沙盘 POC 的产品需求文档（PRD）管理技能。用于查阅、更新和追踪开发进度。PRD 以 prd.json 格式存储在 scripts/ralph/prd.json，每个 User Story 是一个独立的开发单元，按优先级执行。"
---

# PRD 管理 — 动态图谱洞察沙盘 POC

管理本项目的产品需求文档，追踪开发进度，确保每个 User Story 按序完成并通过验证。

---

## PRD 文件位置

- **PRD 文件**: `scripts/ralph/prd.json`
- **PRD 格式参考**: `scripts/ralph/prd.json.example`
- **开发方案详设**: Cursor Plans 中的 `动态图谱洞察沙盘_poc_952160cf.plan.md`
- **进度日志**: `scripts/ralph/progress.txt`

---

## 项目概览

**项目名称**: 动态图谱洞察沙盘 POC (Palantir Ontology Simulator)

**核心目标**: 模拟 Palantir 核心理念，构建领域无关的动态业务推演沙盘。上传 JSON 知识图谱文件，支持 What-If 涟漪推演模拟，输出结构化多类型智能洞察。

**技术栈**:
- 后端: FastAPI + NetworkX + Pydantic + Python 3.10+
- 前端: React 18 + TypeScript + AntV G6 5.x + Ant Design 5.x + Vite
- 数据: 标准 JSON 契约协议（无数据库）

**核心架构**:
- 后端 OntologyEngine 是纯调度器，业务逻辑通过 Python 函数注入（ActionRegistry）
- 前端零硬编码，所有渲染逻辑从 ontology_def 和 actions 动态读取
- 三层智能: L1 数据层(记录) -> L2 信息层(计算) -> L3 智能层(推理)

---

## User Story 分组

### 后端 (US-BE-001 ~ US-BE-007)
| 优先级 | ID | 标题 | 关键交付物 |
|---|---|---|---|
| 1 | US-BE-001 | 后端项目初始化与 Pydantic 数据模型 | backend/ 骨架, models/, main.py |
| 2 | US-BE-002 | ActionRegistry 函数注册表 | engine/action_registry.py |
| 3 | US-BE-003 | Action 函数库 (L1/L2/L3) | actions/action_functions.py |
| 4 | US-BE-004 | OntologyEngine 核心引擎 | engine/graph_engine.py |
| 5 | US-BE-005 | EventQueue 事件队列 | engine/event_queue.py |
| 6 | US-BE-006 | FastAPI 路由层 | api/routes.py (5 个接口) |
| 10 | US-BE-007 | 后端端到端集成验证 | 测试脚本通过 |

### 核心加载机制 (US-CORE-001 ~ US-CORE-002)
| 优先级 | ID | 标题 | 关键交付物 |
|---|---|---|---|
| 7 | US-CORE-001 | 知识图谱加载完整链路 | JSON 校验 → 构图 → 函数注入 → 内置示例服务 |
| 8 | US-CORE-002 | 自定义 Action 函数扩展机制 | 用户可上传自定义 .py 函数文件注入 |

### 示例数据 (US-DATA-001)
| 优先级 | ID | 标题 | 关键交付物 |
|---|---|---|---|
| 9 | US-DATA-001 | 收购事件风险传导场景 | samples/corporate_acquisition.json |

### 前端 (US-FE-001 ~ US-FE-007)
| 优先级 | ID | 标题 | 关键交付物 |
|---|---|---|---|
| 11 | US-FE-001 | 前端项目初始化 | frontend/ 骨架, types/, services/api.ts |
| 12 | US-FE-002 | 全局状态管理 | hooks/useWorkspace.ts, useSimulation.ts |
| 13 | US-FE-003 | 三栏布局壳与 FileUploader | components/Layout/, FileUploader/ |
| 14 | US-FE-004 | GraphCanvas 图谱渲染 | components/GraphCanvas/ (G6 自适应样式) |
| 15 | US-FE-005 | ControlPanel 动态控制台 | components/ControlPanel/ |
| 16 | US-FE-006 | InsightFeed 情报叙事流 | components/InsightFeed/ |
| 17 | US-FE-007 | 涟漪传导动画 | Ripple Animation in GraphCanvas |

### 部署与运行 (US-DEPLOY-001 ~ US-DEPLOY-002)
| 优先级 | ID | 标题 | 关键交付物 |
|---|---|---|---|
| 18 | US-DEPLOY-001 | 命令行开发模式运行与项目文档 | README.md, start.sh, Swagger UI |
| 19 | US-DEPLOY-002 | Docker Compose 容器化部署 | Dockerfile ×2, docker-compose.yml, nginx.conf |

### 集成验证 (US-INT-001)
| 优先级 | ID | 标题 | 关键交付物 |
|---|---|---|---|
| 20 | US-INT-001 | 前后端全链路集成验证 | 完整链路跑通 (CLI + Docker 两种方式) |

---

## 工作流程

### 执行单个 User Story

1. 读取 `scripts/ralph/prd.json`，找到最高优先级的 `passes: false` 的 Story
2. 参考 `动态图谱洞察沙盘_poc_952160cf.plan.md` 中的详细设计
3. 实现该 Story 的所有 Acceptance Criteria
4. 运行验证（每个 Story 的最后几条 AC 就是测试用例）
5. 验证通过后：
   - 提交代码: `feat: [Story ID] - [Story Title]`
   - 更新 prd.json 设置 `passes: true`
   - 追加进度到 `scripts/ralph/progress.txt`

### 验证标准

每个 User Story 的 `acceptanceCriteria` 最后几条以 "验证:" 开头，这些是必须通过的测试项：
- 后端 Story: 主要通过 Python 测试脚本或 curl 命令验证
- 前端 Story: 主要通过浏览器验证 + npm run build 无错误
- 集成 Story: 通过完整的用户操作流程验证

### 关键设计约束

1. **领域无关**: 前后端代码中不出现任何业务领域词汇（不写 "Company"、"valuation" 等）
2. **函数注入**: 引擎不实现业务逻辑，所有计算通过 ActionRegistry 注入的 Python 函数执行
3. **数据驱动渲染**: 前端节点样式/动作按钮/属性面板全部从 API 返回的数据动态生成
4. **结构化洞察**: Insight 是带 type + severity 的对象，前端差异化渲染

---

## 进度日志格式

追加到 `scripts/ralph/progress.txt`：

```
## [Date/Time] - [Story ID]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered
  - Gotchas encountered
  - Useful context
---
```
