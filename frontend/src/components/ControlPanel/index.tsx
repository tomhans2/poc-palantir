import { Descriptions, Button, Divider, Space, Tag, Empty } from 'antd';
import {
  ThunderboltOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useWorkspace } from '../../hooks/useWorkspace';
import { useSimulation } from '../../hooks/useSimulation';

export function ControlPanel() {
  const { state } = useWorkspace();
  const { onSimulate, isSimulating } = useSimulation();

  const {
    selectedNodeId,
    selectedNodeType,
    graphData,
    actions,
    ontologyDef,
  } = state;

  // Find the selected node data
  const selectedNode = selectedNodeId
    ? graphData?.nodes.find((n) => n.id === selectedNodeId)
    : null;

  // Filter actions that target the selected node type
  const availableActions = selectedNodeType
    ? actions.filter((a) => a.target_node_type === selectedNodeType)
    : [];

  return (
    <div style={{ padding: 12 }}>
      {/* Node Properties Card */}
      <div style={{ marginBottom: 16 }}>
        <div
          style={{
            fontWeight: 600,
            fontSize: 14,
            marginBottom: 8,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <InfoCircleOutlined />
          节点详情
        </div>

        {selectedNode ? (
          <>
            <Tag color="blue" style={{ marginBottom: 8 }}>
              {selectedNode.type}
            </Tag>
            <Tag style={{ marginBottom: 8 }}>{selectedNode.id}</Tag>
            <Descriptions
              column={1}
              size="small"
              bordered
              style={{ marginTop: 4 }}
            >
              {Object.entries(selectedNode.properties).map(([key, value]) => (
                <Descriptions.Item key={key} label={key}>
                  {String(value ?? '')}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </>
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="请点击节点查看详情"
            style={{ margin: '24px 0' }}
          />
        )}
      </div>

      {/* Action Buttons */}
      {availableActions.length > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                fontWeight: 600,
                fontSize: 14,
                marginBottom: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <ThunderboltOutlined />
              可用操作
            </div>
            <Space direction="vertical" style={{ width: '100%' }}>
              {availableActions.map((action) => (
                <Button
                  key={action.action_id}
                  type="primary"
                  block
                  loading={isSimulating}
                  disabled={isSimulating}
                  onClick={() => onSimulate(action.action_id)}
                >
                  {action.display_name}
                </Button>
              ))}
            </Space>
          </div>
        </>
      )}

      {/* Legend */}
      {ontologyDef && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div>
            <div
              style={{
                fontWeight: 600,
                fontSize: 14,
                marginBottom: 8,
              }}
            >
              图例
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {Object.entries(ontologyDef.node_types).map(
                ([typeKey, typeDef]) => (
                  <div
                    key={typeKey}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                  >
                    <span
                      style={{
                        display: 'inline-block',
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        backgroundColor: typeDef.color,
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontSize: 13, color: '#333' }}>
                      {typeDef.label}
                    </span>
                  </div>
                ),
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
