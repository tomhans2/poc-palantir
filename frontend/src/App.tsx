import { useWorkspace } from './hooks/useWorkspace'
import './App.css'

function App() {
  const { state } = useWorkspace()

  return (
    <div>
      <h1>动态图谱洞察沙盘</h1>
      <p>
        {state.metadata
          ? state.metadata.description
          : '请上传 JSON 知识图谱文件或选择内置示例'}
      </p>
    </div>
  )
}

export default App
