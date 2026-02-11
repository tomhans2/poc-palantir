# 前端 - 动态图谱洞察沙盘 (React + AntV G6)

## 安装与启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

启动后访问: http://localhost:5173

> 注意：前端需要后端服务运行在 `http://localhost:8000`，Vite 开发服务器会自动将 `/api` 请求代理到后端。

## 环境配置

### Vite 配置 (vite.config.ts)

| 配置项 | 值 | 说明 |
|--------|------|------|
| 开发端口 | `5173` | Vite 开发服务器端口 |
| API 代理 | `/api → http://localhost:8000` | 自动转发 API 请求到后端 |

如需修改后端地址，编辑 `vite.config.ts` 中的 `server.proxy` 配置。

## 构建

```bash
# TypeScript 类型检查 + 生产构建
npm run build

# 预览生产构建
npm run preview
```

## 技术栈

- **React 19** + TypeScript 5.9
- **Vite 7** (开发服务器 + 构建工具)
- **Ant Design 6** (UI 组件库)
- **@ant-design/icons** (图标库)
- **AntV G6 5.x** (图谱渲染引擎)
- **Axios** (HTTP 客户端)

## 目录结构

```
frontend/src/
├── types/index.ts             # TypeScript 接口 (对齐后端 Pydantic 模型)
├── services/api.ts            # API 调用封装 (loadWorkspace, simulate, reset, etc.)
├── hooks/
│   ├── useWorkspace.ts        # 全局状态管理 (Context + useReducer)
│   └── useSimulation.ts       # 推演逻辑封装
└── components/
    ├── WorkspaceProvider.tsx   # Context Provider 组件
    ├── Layout/AppLayout.tsx    # 三栏布局壳 (Header + Sider + Content + Sider)
    ├── FileUploader/           # JSON 文件上传 + 内置示例选择
    ├── GraphCanvas/            # AntV G6 图谱画布 (涟漪动画)
    ├── ControlPanel/           # 左侧控制台 (属性面板 + 动作按钮 + 图例)
    └── InsightFeed/            # 右侧情报叙事流 (结构化洞察)
```
