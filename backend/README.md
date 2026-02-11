# 后端 - 动态图谱洞察沙盘 (FastAPI + NetworkX)

## 安装与启动

```bash
cd backend

# 安装 Python 依赖
pip install -r requirements.txt

# 启动开发服务器 (支持热重载)
uvicorn app.main:app --reload --port 8000
```

启动后：
- API 服务: http://localhost:8000
- Swagger 文档: http://localhost:8000/docs
- ReDoc 文档: http://localhost:8000/redoc

## API 接口文档

### GET /health
健康检查。

**响应**: `{"status": "ok"}`

### GET /api/v1/workspace/samples
获取可用的内置示例列表。

**响应**:
```json
[
  {
    "name": "corporate_acquisition",
    "description": "基于投资与收购事件的风险传导推演沙盘"
  }
]
```

### POST /api/v1/workspace/load
加载知识图谱工作区。支持两种方式：

**方式一 — 文件上传 (multipart/form-data)**:
```bash
curl -X POST http://localhost:8000/api/v1/workspace/load \
  -F "file=@my_graph.json"
```

**方式二 — 内置示例 (query parameter)**:
```bash
curl -X POST "http://localhost:8000/api/v1/workspace/load?sample=corporate_acquisition"
```

**可选参数**: `action_file` — 上传自定义 Python Action 函数文件。

**响应**: `{metadata, ontology_def, graph_data, actions, registered_functions, warnings}`

### POST /api/v1/workspace/simulate
执行 What-If 推演。

**请求体**:
```json
{
  "action_id": "trigger_acquisition_failure",
  "node_id": "E_ACQ_101"
}
```

**响应**: `{status, delta_graph, ripple_path, insights}`

### POST /api/v1/workspace/reset
重置工作区到初始状态（清除推演历史）。

**响应**: 重置后的 graph_data。

### GET /api/v1/workspace/history
获取推演事件历史列表。

**响应**: `[{timestamp, action_id, target_node_id, ripple_path, insights, delta_graph}, ...]`

## 如何编写自定义 Action 函数

系统支持通过 `@register_action` 装饰器注入自定义业务逻辑函数。

### 函数签名

所有 Action 函数必须遵循统一签名：

```python
from app.engine.action_registry import register_action, ActionContext, ActionResult

@register_action
def my_custom_function(ctx: ActionContext) -> ActionResult:
    """自定义业务逻辑函数。"""
    # ctx.target_node: dict — 目标节点属性
    # ctx.source_node: dict — 源节点属性
    # ctx.params: dict — 动作参数
    # ctx.graph: nx.DiGraph — NetworkX 图实例

    old_value = ctx.target_node.get("my_field", 0)
    new_value = old_value * 2

    return ActionResult(
        updated_properties={"my_field": new_value},
        old_values={"my_field": old_value},
    )
```

### ActionContext 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `target_node` | `dict` | 目标节点的属性字典 |
| `source_node` | `dict` | 源节点 (触发推演的节点) 的属性字典 |
| `target_id` | `str` | 目标节点 ID |
| `source_id` | `str` | 源节点 ID |
| `params` | `dict` | 动作参数 (来自 JSON 中 `effect_on_target.parameters`) |
| `graph` | `nx.DiGraph` | NetworkX 有向图实例 (可用于图拓扑分析) |

### 注入方式

1. **约定目录**: 在 `samples/` 目录下创建与 JSON 同名的 `.py` 文件（如 `samples/my_scenario.py`），加载 JSON 时自动检测并加载
2. **API 上传**: 通过 `POST /load` 的 `action_file` 参数上传 `.py` 文件
3. **覆盖机制**: 自定义函数与内置同名函数冲突时，自定义版本优先

### 内置函数库

| 函数名 | 层级 | 描述 |
|--------|------|------|
| `set_property` | L1 数据层 | 设置节点属性值 |
| `adjust_numeric` | L1 数据层 | 按比例调整数值属性 |
| `update_risk_status` | L1 数据层 | 更新风险状态字段 |
| `recalculate_valuation` | L2 信息层 | 基于冲击因子重算估值 |
| `compute_margin_gap` | L2 信息层 | 计算保证金缺口 |
| `graph_weighted_exposure` | L3 智能层 | 沿图拓扑计算加权风险敞口 |

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

## 目录结构

```
backend/
├── requirements.txt
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── api/routes.py      # REST API 路由
│   ├── engine/
│   │   ├── graph_engine.py    # OntologyEngine 核心引擎
│   │   ├── action_registry.py # 函数注册表
│   │   └── event_queue.py     # 事件队列
│   ├── actions/
│   │   └── action_functions.py # 内置 L1/L2/L3 函数
│   └── models/                # Pydantic 数据模型
├── samples/
│   └── corporate_acquisition.json
└── tests/                     # 174+ 测试
```
