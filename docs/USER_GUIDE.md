# 使用者指南 — 动态图谱洞察沙盘

> 本文档面向使用者，详细说明如何编写 JSON 配置文件和 Python 动作函数，上传到系统后进行图谱模拟推演。

---

## 目录

1. [快速上手](#1-快速上手)
2. [JSON 配置文件编写规范](#2-json-配置文件编写规范)
3. [Python 动作函数编写规范](#3-python-动作函数编写规范)
4. [上传操作指南](#4-上传操作指南)
5. [模拟推演操作](#5-模拟推演操作)
6. [完整案例：从零构建一个业务沙盘](#6-完整案例从零构建一个业务沙盘)
7. [内置函数参考](#7-内置函数参考)
8. [DSL 路径语法参考](#8-dsl-路径语法参考)
9. [常见问题](#9-常见问题)

---

## 1. 快速上手

### 最简流程

1. 打开浏览器访问 http://localhost:5173
2. 在左侧面板，从下拉选择器选择内置示例 `private_banking`
3. 图谱自动渲染，点击任意节点查看属性
4. 选中 **红色菱形** 的事件节点（如"星辰科技IPO"），左侧面板出现动作按钮
5. 点击动作按钮（如"模拟: IPO成功上市"），观察涟漪传导动画和右侧洞察输出

### 自定义场景流程

1. 编写 **JSON 配置文件**（定义图谱结构 + 推演规则）
2. （可选）编写 **Python 动作文件**（定义自定义业务逻辑函数）
3. 在界面上先上传 Python 文件，再上传 JSON 文件
4. 系统加载并渲染图谱，即可开始推演

---

## 2. JSON 配置文件编写规范

JSON 配置文件是系统的核心输入，定义了图谱的全部信息。文件必须包含以下 **4 个顶层字段**：

```json
{
  "metadata": { ... },
  "ontology_def": { ... },
  "graph_data": { ... },
  "action_engine": { ... }
}
```

以下逐一详解每个字段。

---

### 2.1 `metadata` — 元数据

描述这个图谱场景的基本信息。

```json
{
  "metadata": {
    "domain": "private_banking",
    "version": "1.0",
    "description": "私行高净值客户经营：张远航家族财富管理沙盘"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `domain` | string | **是** | 领域标识，如 `"private_banking"`, `"supply_chain"`, `"fraud_detection"` |
| `version` | string | 否 | 版本号 |
| `description` | string | 否 | 场景描述（会显示在前端界面上） |

---

### 2.2 `ontology_def` — 本体定义（节点类型和边类型）

定义图谱中有哪些类型的节点和边，以及它们在前端的视觉样式。

```json
{
  "ontology_def": {
    "node_types": {
      "Customer": {
        "label": "高净值客户",
        "color": "#1890FF",
        "shape": "circle"
      },
      "LifeEvent": {
        "label": "关键事件",
        "color": "#F5222D",
        "shape": "diamond"
      }
    },
    "edge_types": {
      "FACES": {
        "label": "面临事件",
        "color": "#FF7A45",
        "style": "dashed"
      },
      "CONTROLS": {
        "label": "实际控制",
        "color": "#FA8C16",
        "style": "solid"
      }
    }
  }
}
```

#### 节点类型 (`node_types`)

每个 key 是节点类型名称（如 `"Customer"`），value 是样式定义：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `label` | string | **是** | 中文显示名称 |
| `color` | string | **是** | 十六进制颜色值 |
| `shape` | string | **是** | 形状：`"circle"`, `"rect"`, `"diamond"`, `"hexagon"`, `"triangle"` |
| `icon` | string | 否 | 图标名称（Ant Design 图标） |

#### 边类型 (`edge_types`)

每个 key 是边类型名称（如 `"CONTROLS"`），value 是样式定义：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `label` | string | **是** | 中文显示名称 |
| `color` | string | **是** | 十六进制颜色值 |
| `style` | string | 否 | 线型：`"solid"`（实线）, `"dashed"`（虚线） |

> **命名约定**: 节点类型名用 PascalCase（如 `Customer`），边类型名用 UPPER_SNAKE_CASE（如 `HAS_PORTFOLIO`）。

---

### 2.3 `graph_data` — 图数据（节点和边的实例）

定义图谱中具体的节点和边。

```json
{
  "graph_data": {
    "nodes": [
      {
        "id": "CUST_ZHANG",
        "type": "Customer",
        "properties": {
          "name": "张远航",
          "age": 45,
          "aum": 200000000,
          "risk_level": "MODERATE"
        }
      },
      {
        "id": "EVT_IPO",
        "type": "LifeEvent",
        "properties": {
          "name": "星辰科技IPO",
          "subtype": "IPO",
          "status": "PREPARING"
        }
      }
    ],
    "edges": [
      {
        "source": "CUST_ZHANG",
        "target": "EVT_IPO",
        "type": "FACES",
        "properties": {}
      }
    ]
  }
}
```

#### 节点 (`nodes`)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | **是** | 节点唯一标识符（如 `"CUST_ZHANG"`） |
| `type` | string | **是** | 节点类型，必须匹配 `ontology_def.node_types` 中的 key |
| `properties` | object | **是** | 节点属性字典，可以是任意 key-value 对 |

#### 边 (`edges`)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source` | string | **是** | 起始节点 ID |
| `target` | string | **是** | 目标节点 ID |
| `type` | string | **是** | 边类型，必须匹配 `ontology_def.edge_types` 中的 key |
| `properties` | object | **是** | 边属性字典（可以是空对象 `{}`） |

> **重要**: `source` 和 `target` 的值必须是 `nodes` 数组中已定义的节点 `id`。

---

### 2.4 `action_engine` — 动作引擎（推演规则）

定义图谱上可执行的 What-If 模拟动作。**这是整个系统的核心。**

```json
{
  "action_engine": {
    "actions": [
      {
        "action_id": "simulate_ipo_success",
        "target_node_type": "LifeEvent",
        "match_properties": { "subtype": "IPO" },
        "display_name": "模拟: IPO成功上市",
        "direct_effect": {
          "property_to_update": "status",
          "new_value": "COMPLETED_SUCCESS"
        },
        "ripple_rules": [
          {
            "rule_id": "IPO_S01",
            "propagation_path": "-[TRIGGERS]-> BusinessEntity",
            "effect_on_target": {
              "action_to_trigger": "recalculate_valuation",
              "parameters": { "shock_factor": 1.5 }
            },
            "insight_template": "企业估值跃升至 ¥{target[valuation]:,.0f}",
            "insight_type": "event_trigger",
            "insight_severity": "critical"
          },
          {
            "rule_id": "IPO_S02",
            "propagation_path": "<-[FACES]- Customer",
            "condition": "source.get('subtype') == 'IPO'",
            "effect_on_target": {
              "action_to_trigger": "pb_assess_aum_impact",
              "parameters": { "event_type": "IPO_SUCCESS", "uplift_factor": 0.8 }
            },
            "insight_template": "{target[name]} AUM 增长至 ¥{target[aum]:,.0f}",
            "insight_type": "quantitative_impact",
            "insight_severity": "critical"
          }
        ]
      }
    ]
  }
}
```

#### Action 定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action_id` | string | **是** | 动作唯一标识符 |
| `target_node_type` | string | **是** | 动作适用的节点类型（只有该类型的节点会显示此动作按钮） |
| `match_properties` | object | 否 | 额外匹配条件，精确匹配节点属性 |
| `display_name` | string | **是** | 前端按钮显示文字 |
| `direct_effect` | object | 否 | 直接效果：修改目标节点的一个属性 |
| `ripple_rules` | array | **是** | 涟漪规则数组（定义影响如何沿图拓扑传导） |

#### `direct_effect` — 直接效果

| 字段 | 类型 | 说明 |
|------|------|------|
| `property_to_update` | string | 要修改的属性名 |
| `new_value` | any | 新属性值 |

#### `ripple_rules[]` — 涟漪规则（最核心的部分）

每条涟漪规则定义了影响如何从触发节点传导到相邻节点：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `rule_id` | string | **是** | 规则唯一标识符 |
| `propagation_path` | string | **是** | DSL 路径，定义传导方向和经过的边/节点类型。详见 [DSL 语法参考](#8-dsl-路径语法参考) |
| `condition` | string | 否 | Python 条件表达式，可用 `source` 和 `target` 字典。为空或不填则始终匹配 |
| `effect_on_target` | object | **是** | 对匹配节点执行的效果 |
| `insight_template` | string | 否 | 洞察文本模板，支持 Python `format_map` 语法 |
| `insight_type` | string | 否 | 洞察类型（见下表） |
| `insight_severity` | string | 否 | 洞察严重度：`"info"`, `"warning"`, `"critical"` |

#### `effect_on_target` — 效果定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `action_to_trigger` | string | 要调用的 Action 函数名称（内置或自定义） |
| `parameters` | object | 传递给函数的参数字典 |

#### 洞察类型 (`insight_type`)

| 值 | 含义 | 图标颜色 |
|------|------|----------|
| `event_trigger` | 事件触发通知 | 蓝色 |
| `quantitative_impact` | 量化影响分析 | 橙色 |
| `risk_propagation` | 风险传导预警 | 红色 |
| `network_analysis` | 网络拓扑分析 | 紫色 |
| `recommendation` | 行动建议 | 绿色 |

#### 洞察模板语法

使用 Python `format_map` 语法，可以引用节点属性：

```
"{target[name]} 的 AUM 增长至 ¥{target[aum]:,.0f}"
```

| 变量 | 说明 |
|------|------|
| `{target[属性名]}` | 目标节点（被影响的节点）的属性值 |
| `{source[属性名]}` | 源节点（触发推演的节点）的属性值 |
| `:,.0f` | 数字格式化（千分位分隔，无小数） |
| `:.1%` | 百分比格式化（保留一位小数） |
| `:.4f` | 浮点数格式化（保留四位小数） |

---

## 3. Python 动作函数编写规范

当你的推演规则中 `action_to_trigger` 引用的函数名不在内置函数列表中时，你需要编写自定义 Python 动作函数。

### 3.1 基本模板

```python
"""我的自定义业务领域 Action 函数。"""

from app.engine.action_registry import ActionContext, ActionResult, register_action


@register_action
def my_custom_function(ctx: ActionContext) -> ActionResult:
    """函数描述。

    Params:
        param1 (str): 参数1说明
        param2 (float): 参数2说明
    """
    # 1. 从 ctx.params 读取 JSON 中传入的参数
    param1 = ctx.params.get("param1", "默认值")
    param2 = ctx.params.get("param2", 0.0)

    # 2. 从 ctx.target_node 读取目标节点当前属性
    old_value = ctx.target_node.get("some_property", 0)

    # 3. 执行业务逻辑计算
    new_value = old_value * (1 + param2)

    # 4. 返回结果
    return ActionResult(
        updated_properties={
            "some_property": new_value,
            "status": "UPDATED",
        },
        old_values={
            "some_property": old_value,
        },
    )
```

### 3.2 关键规则

1. **必须使用 `@register_action` 装饰器** — 否则系统无法发现函数
2. **函数签名固定为** `(ctx: ActionContext) -> ActionResult` — 不能修改
3. **函数名即注册名** — JSON 中 `action_to_trigger` 的值必须与函数名完全一致
4. **一个 `.py` 文件可以包含多个函数** — 系统会自动扫描所有带装饰器的函数

### 3.3 ActionContext 详解

`ctx` 参数提供了执行上下文中的所有信息：

| 属性 | 类型 | 说明 |
|------|------|------|
| `ctx.target_node` | `dict` | 目标节点（被影响的节点）的属性字典 |
| `ctx.source_node` | `dict` | 源节点（触发推演的节点）的属性字典 |
| `ctx.target_id` | `str` | 目标节点 ID |
| `ctx.source_id` | `str` | 源节点 ID |
| `ctx.params` | `dict` | JSON 中 `effect_on_target.parameters` 的内容 |
| `ctx.graph` | `nx.DiGraph` | NetworkX 有向图实例（可用于高级图拓扑分析） |

### 3.4 ActionResult 详解

返回值告诉引擎如何更新节点：

| 字段 | 类型 | 说明 |
|------|------|------|
| `updated_properties` | `dict` | 要更新到目标节点上的属性键值对 |
| `old_values` | `dict` | 更新前的旧值（用于前端展示变化对比） |

### 3.5 函数复杂度分层

系统设计了三个智能层级，按需选用：

#### L1 数据层 — 简单属性操作

```python
@register_action
def my_set_status(ctx: ActionContext) -> ActionResult:
    """简单设置状态属性。"""
    new_status = ctx.params.get("status", "ACTIVE")
    old_status = ctx.target_node.get("status")
    return ActionResult(
        updated_properties={"status": new_status},
        old_values={"status": old_status},
    )
```

#### L2 信息层 — 业务计算

```python
@register_action
def assess_aum_impact(ctx: ActionContext) -> ActionResult:
    """基于事件计算 AUM 影响。"""
    uplift = ctx.params.get("uplift_factor", 0)
    old_aum = ctx.target_node.get("aum", 0)
    new_aum = old_aum * (1 + uplift)
    return ActionResult(
        updated_properties={"aum": new_aum},
        old_values={"aum": old_aum},
    )
```

#### L3 智能层 — 图拓扑分析

```python
@register_action
def analyze_network_risk(ctx: ActionContext) -> ActionResult:
    """遍历图拓扑，分析网络风险。"""
    graph = ctx.graph
    target_id = ctx.target_id

    # 遍历所有入边
    risk_count = 0
    for u, v, edata in graph.in_edges(target_id, data=True):
        if edata.get("type") == "TARGETS":
            risk_count += 1
            neighbor = graph.nodes.get(u, {})
            # 可以读取邻居节点属性做复杂分析

    return ActionResult(
        updated_properties={
            "risk_sources": risk_count,
            "risk_level": "HIGH" if risk_count >= 3 else "LOW",
        },
        old_values={"risk_level": ctx.target_node.get("risk_level", "UNKNOWN")},
    )
```

### 3.6 函数与 JSON 的对应关系

JSON 中每条涟漪规则的 `effect_on_target.action_to_trigger` 对应一个 Python 函数名，`parameters` 对应函数中 `ctx.params` 的内容：

**JSON 侧：**
```json
{
  "effect_on_target": {
    "action_to_trigger": "assess_aum_impact",
    "parameters": {
      "uplift_factor": 0.8,
      "event_type": "IPO_SUCCESS"
    }
  }
}
```

**Python 侧：**
```python
@register_action
def assess_aum_impact(ctx: ActionContext) -> ActionResult:
    uplift = ctx.params.get("uplift_factor", 0)      # → 0.8
    event_type = ctx.params.get("event_type", "")     # → "IPO_SUCCESS"
    # ...
```

---

## 4. 上传操作指南

### 4.1 方式一：上传自定义文件

#### 步骤 1：准备 Python 动作文件（如需自定义函数）

如果你的 JSON 中引用了非内置函数名，需要先准备 `.py` 文件。

#### 步骤 2：上传 Python 文件

在界面左侧文件上传面板，找到 **"Python 动作文件（可选）"** 区域：

1. 点击 **"选择 .py 文件"** 按钮
2. 选择你的 Python 文件
3. 上传成功后显示绿色标签，标签上会显示文件名

> 注意：Python 文件只是"预加载"，不会立即执行。它会在上传 JSON 时一起提交。

#### 步骤 3：上传 JSON 配置文件

在 **拖拽上传区域**，将 `.json` 文件拖入或点击选择：

1. 系统会同时提交 JSON 和之前预加载的 Python 文件
2. 后端校验 JSON 格式、注册 Python 函数、构建图谱
3. 成功后图谱自动渲染

#### 上传结果提示

- **"工作区加载成功"** — 一切正常
- **"工作区已加载，但有 N 个警告"** — JSON 中引用了未注册的函数名，请检查 Python 文件是否包含对应函数
- **黄色警告框** — 列出所有未注册的函数名及其所在规则

### 4.2 方式二：使用内置示例

从下拉菜单选择内置示例（如 `private_banking`），系统自动加载对应的 JSON 和 Python 文件。

### 4.3 只使用内置函数（无需 Python 文件）

如果你的 JSON 中所有 `action_to_trigger` 都是内置函数名，**不需要上传 Python 文件**，只上传 JSON 即可。

内置函数列表见 [第 7 节](#7-内置函数参考)。

---

## 5. 模拟推演操作

### 5.1 选中节点

点击图谱中的节点，左侧控制台显示：
- 节点属性面板（所有 `properties` 键值对）
- 可用动作按钮列表（根据节点类型过滤）

### 5.2 执行推演

点击动作按钮后：
1. 系统执行直接效果（修改目标节点属性）
2. 按涟漪规则沿图拓扑传导影响
3. 图谱上显示涟漪传导动画（高亮路径）
4. 右侧面板输出结构化洞察

### 5.3 查看洞察

右侧情报叙事流按时间顺序显示洞察条目，每条包含：
- 类型标签（事件触发 / 量化影响 / 风险传导 / 网络分析 / 建议）
- 严重度（info / warning / critical）
- 洞察文本内容

### 5.4 重置

点击重置按钮，图谱恢复到初始状态，清除所有推演历史。

---

## 6. 完整案例：从零构建一个业务沙盘

以下演示如何构建一个简单的"供应链风险传导"沙盘。

### 6.1 编写 JSON 配置文件 `supply_chain.json`

```json
{
  "metadata": {
    "domain": "supply_chain",
    "version": "1.0",
    "description": "供应链风险传导模拟沙盘"
  },
  "ontology_def": {
    "node_types": {
      "Supplier": {
        "label": "供应商",
        "color": "#52C41A",
        "shape": "circle"
      },
      "Factory": {
        "label": "工厂",
        "color": "#1890FF",
        "shape": "rect"
      },
      "RiskEvent": {
        "label": "风险事件",
        "color": "#F5222D",
        "shape": "diamond"
      }
    },
    "edge_types": {
      "SUPPLIES_TO": {
        "label": "供应",
        "color": "#52C41A",
        "style": "solid"
      },
      "FACES": {
        "label": "面临",
        "color": "#F5222D",
        "style": "dashed"
      },
      "TRIGGERS": {
        "label": "影响",
        "color": "#FF7A45",
        "style": "solid"
      }
    }
  },
  "graph_data": {
    "nodes": [
      {
        "id": "SUPPLIER_A",
        "type": "Supplier",
        "properties": {
          "name": "核心芯片供应商A",
          "capacity": 10000,
          "status": "NORMAL",
          "region": "台湾"
        }
      },
      {
        "id": "FACTORY_1",
        "type": "Factory",
        "properties": {
          "name": "华东制造基地",
          "daily_output": 5000,
          "dependency_ratio": 0.7,
          "status": "NORMAL"
        }
      },
      {
        "id": "EVT_EARTHQUAKE",
        "type": "RiskEvent",
        "properties": {
          "name": "供应商地震停产",
          "status": "POTENTIAL",
          "severity": "HIGH"
        }
      }
    ],
    "edges": [
      {
        "source": "SUPPLIER_A",
        "target": "FACTORY_1",
        "type": "SUPPLIES_TO",
        "properties": { "dependency_weight": 0.7 }
      },
      {
        "source": "EVT_EARTHQUAKE",
        "target": "SUPPLIER_A",
        "type": "TRIGGERS",
        "properties": {}
      },
      {
        "source": "FACTORY_1",
        "target": "EVT_EARTHQUAKE",
        "type": "FACES",
        "properties": {}
      }
    ]
  },
  "action_engine": {
    "actions": [
      {
        "action_id": "trigger_earthquake",
        "target_node_type": "RiskEvent",
        "display_name": "模拟: 地震导致停产",
        "direct_effect": {
          "property_to_update": "status",
          "new_value": "OCCURRED"
        },
        "ripple_rules": [
          {
            "rule_id": "EQ_01",
            "propagation_path": "-[TRIGGERS]-> Supplier",
            "effect_on_target": {
              "action_to_trigger": "sc_supplier_shutdown",
              "parameters": { "capacity_loss_ratio": 0.8 }
            },
            "insight_template": "{target[name]} 因地震停产，产能下降 80%，剩余产能 {target[capacity]}",
            "insight_type": "event_trigger",
            "insight_severity": "critical"
          },
          {
            "rule_id": "EQ_02",
            "propagation_path": "<-[FACES]- Factory",
            "effect_on_target": {
              "action_to_trigger": "sc_assess_production_impact",
              "parameters": {}
            },
            "insight_template": "{target[name]} 日产量降至 {target[daily_output]}，供应链中断风险 {target[risk_level]}",
            "insight_type": "risk_propagation",
            "insight_severity": "critical"
          }
        ]
      }
    ]
  }
}
```

### 6.2 编写 Python 动作文件 `supply_chain.py`

```python
"""供应链风险领域 Action 函数。"""

from app.engine.action_registry import ActionContext, ActionResult, register_action


@register_action
def sc_supplier_shutdown(ctx: ActionContext) -> ActionResult:
    """供应商停产，削减产能。"""
    loss_ratio = ctx.params.get("capacity_loss_ratio", 0.5)
    old_capacity = ctx.target_node.get("capacity", 0)
    new_capacity = old_capacity * (1 - loss_ratio)
    return ActionResult(
        updated_properties={
            "capacity": new_capacity,
            "status": "SHUTDOWN",
        },
        old_values={"capacity": old_capacity},
    )


@register_action
def sc_assess_production_impact(ctx: ActionContext) -> ActionResult:
    """评估工厂生产受影响程度。"""
    graph = ctx.graph
    target_id = ctx.target_id
    dependency = ctx.target_node.get("dependency_ratio", 0.5)
    old_output = ctx.target_node.get("daily_output", 0)

    # 计算受影响产量
    new_output = old_output * (1 - dependency)
    risk_level = "CRITICAL" if dependency > 0.6 else "MODERATE"

    return ActionResult(
        updated_properties={
            "daily_output": new_output,
            "risk_level": risk_level,
            "status": "DISRUPTED",
        },
        old_values={
            "daily_output": old_output,
            "status": ctx.target_node.get("status"),
        },
    )
```

### 6.3 上传操作

1. 打开浏览器访问 http://localhost:5173
2. 在 Python 上传区域点击"选择 .py 文件"，选择 `supply_chain.py`
3. 将 `supply_chain.json` 拖入上传区域
4. 系统加载成功，图谱渲染
5. 点击红色菱形的"供应商地震停产"节点
6. 点击"模拟: 地震导致停产"按钮
7. 观察涟漪传导和洞察输出

---

## 7. 内置函数参考

以下函数无需上传 Python 文件即可直接在 JSON 中使用：

### `set_property`

**层级**: L1 数据层 — 设置节点属性

| 参数 | 类型 | 说明 |
|------|------|------|
| `property` | string | 属性名 |
| `value` | any | 新值 |

```json
{
  "action_to_trigger": "set_property",
  "parameters": { "property": "status", "value": "ACTIVE" }
}
```

### `adjust_numeric`

**层级**: L1 数据层 — 数值属性乘以系数

| 参数 | 类型 | 说明 |
|------|------|------|
| `property` | string | 数值属性名 |
| `factor` | float | 乘数（0.8 = 降低20%，1.2 = 增长20%） |

```json
{
  "action_to_trigger": "adjust_numeric",
  "parameters": { "property": "valuation", "factor": 0.6 }
}
```

### `update_risk_status`

**层级**: L1 数据层 — 更新风险状态

| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string | 新风险状态（如 `"HIGH_RISK"`, `"LOW_RISK"`, `"ELEVATED"`） |

```json
{
  "action_to_trigger": "update_risk_status",
  "parameters": { "status": "HIGH_RISK" }
}
```

### `recalculate_valuation`

**层级**: L2 信息层 — 基于冲击因子重算估值

| 参数 | 类型 | 说明 |
|------|------|------|
| `shock_factor` | float | 估值变化比例（-0.3 = 下跌30%，0.5 = 上涨50%） |

```json
{
  "action_to_trigger": "recalculate_valuation",
  "parameters": { "shock_factor": 1.5 }
}
```

### `compute_margin_gap`

**层级**: L2 信息层 — 计算保证金缺口

| 参数 | 类型 | 说明 |
|------|------|------|
| `stock_change` | float | 股价变化比例（-0.4 = 下跌40%） |

> 需要目标节点有 `loan_amount` 和 `collateral_ratio` 属性。

### `graph_weighted_exposure`

**层级**: L3 智能层 — 沿图拓扑计算加权风险敞口

| 参数 | 类型 | 说明 |
|------|------|------|
| `direction` | string | `"in"`, `"out"`, `"both"` |
| `edge_type` | string | 过滤的边类型 |
| `value_property` | string | 邻居节点的值属性名（默认 `"valuation"`） |
| `weight_property` | string | 边的权重属性名（默认 `"weight"`） |
| `aggregation` | string | 聚合方式：`"sum"`, `"max"`, `"count"` |

---

## 8. DSL 路径语法参考

涟漪规则中的 `propagation_path` 使用类 Cypher 语法，定义影响传导的方向、边类型和目标节点类型。

### 语法格式

```
方向标记[边类型]方向标记 节点类型
```

### 两种方向

| 方向 | 语法 | 含义 | 示例 |
|------|------|------|------|
| **出方向** | `-[EDGE_TYPE]-> NodeType` | 沿出边方向传导 | `-[TRIGGERS]-> BusinessEntity` |
| **入方向** | `<-[EDGE_TYPE]- NodeType` | 沿入边方向传导 | `<-[FACES]- Customer` |

### 示例解读

| 路径 | 含义 |
|------|------|
| `-[TRIGGERS]-> BusinessEntity` | 找到当前节点沿 `TRIGGERS` 边连接的所有 `BusinessEntity` 类型节点 |
| `<-[FACES]- Customer` | 找到沿 `FACES` 边反向指向当前节点的所有 `Customer` 类型节点 |
| `-[SUPPLIES_TO]-> Factory` | 找到当前节点沿 `SUPPLIES_TO` 边连接的所有 `Factory` 类型节点 |
| `<-[TARGETS]- Competitor` | 找到沿 `TARGETS` 边反向指向当前节点的所有 `Competitor` 类型节点 |

### 关键理解

传导起点是**触发 Action 的节点**（如事件节点），路径描述的是从这个节点出发如何找到需要被影响的邻居节点。

例如：用户点击事件节点 `EVT_IPO` 的"模拟IPO成功"按钮：
- `<-[FACES]- Customer` → 找到所有通过 `FACES` 边连接到 `EVT_IPO` 的 `Customer` 节点
- `-[TRIGGERS]-> BusinessEntity` → 找到 `EVT_IPO` 通过 `TRIGGERS` 边连接的 `BusinessEntity` 节点

---

## 9. 常见问题

### Q: 上传 JSON 后报 422 错误

**原因**: JSON 缺少必填字段。

**解决**: 确保 JSON 包含完整的 4 个顶层字段：`metadata`, `ontology_def`, `graph_data`, `action_engine`。其中 `graph_data` 必须包含 `nodes` 和 `edges` 数组。

### Q: 上传后出现"未注册函数"警告

**原因**: JSON 中 `action_to_trigger` 引用了既不在内置函数中也不在上传的 Python 文件中的函数名。

**解决**:
1. 检查函数名拼写是否正确（大小写敏感）
2. 确认 Python 文件中的函数使用了 `@register_action` 装饰器
3. 确认先上传了 Python 文件再上传 JSON

### Q: 推演时没有涟漪效果

**原因**: 涟漪规则的传导路径没有匹配到任何邻居节点。

**排查**:
1. 检查 `propagation_path` 中的边类型是否与 `edges` 中定义的 `type` 一致
2. 检查方向是否正确（入方向 vs 出方向）
3. 检查路径中的节点类型是否与实际节点的 `type` 一致
4. 如果有 `condition`，检查条件表达式是否正确

### Q: 可以不写 Python 文件吗？

**可以。** 如果你的所有 `action_to_trigger` 都使用内置函数（`set_property`, `adjust_numeric`, `update_risk_status`, `recalculate_valuation`, `compute_margin_gap`, `graph_weighted_exposure`），无需上传 Python 文件。

### Q: 节点属性可以是任意类型吗？

**是的。** `properties` 是一个自由的 key-value 字典，支持 string, number, boolean, null 等 JSON 基础类型。你的 Action 函数可以读取和写入任意属性。

### Q: 一个动作可以触发多条涟漪规则吗？

**可以。** `ripple_rules` 是一个数组，可以包含多条规则，它们会按顺序依次执行。每条规则可以影响不同方向、不同类型的邻居节点。

### Q: 自定义函数可以覆盖内置函数吗？

**可以。** 如果你的 Python 文件中定义了与内置函数同名的函数（如自定义版本的 `recalculate_valuation`），你的版本会覆盖内置版本。系统会在加载时提示已注册的函数列表及其来源。
