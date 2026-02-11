import { useCallback, useState } from 'react';
import { Layout, Button, Drawer, message } from 'antd';
import {
  ReloadOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useWorkspace } from '../../hooks/useWorkspace';
import { resetWorkspace } from '../../services/api';
import { FileUploader } from '../FileUploader';
import { ControlPanel } from '../ControlPanel';
import { GraphCanvas } from '../GraphCanvas';
import { InsightFeed } from '../InsightFeed';

const { Header, Sider, Content } = Layout;

export function AppLayout() {
  const { state, dispatch } = useWorkspace();
  const [uploaderOpen, setUploaderOpen] = useState(false);
  const [resetting, setResetting] = useState(false);

  const handleReset = useCallback(async () => {
    setResetting(true);
    try {
      await resetWorkspace();
      dispatch({ type: 'RESET' });
      message.success('已重置工作区');
    } catch {
      message.error('重置失败');
    } finally {
      setResetting(false);
    }
  }, [dispatch]);

  const headerTitle = state.metadata?.description ?? '动态图谱洞察沙盘';

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <span className="app-header-title">{headerTitle}</span>

        <div className="app-header-actions">
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploaderOpen(true)}
            size="small"
          >
            加载数据
          </Button>

          {state.metadata && (
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              loading={resetting}
              size="small"
            >
              重置
            </Button>
          )}
        </div>
      </Header>

      <Layout>
        <Sider width={280} className="left-sider">
          <ControlPanel />
        </Sider>

        <Content className="main-content">
          <GraphCanvas />
        </Content>

        <Sider width={320} className="right-sider">
          <InsightFeed />
        </Sider>
      </Layout>

      <Drawer
        title="加载知识图谱"
        open={uploaderOpen}
        onClose={() => setUploaderOpen(false)}
        width={400}
        destroyOnClose
      >
        <FileUploader />
      </Drawer>
    </Layout>
  );
}
