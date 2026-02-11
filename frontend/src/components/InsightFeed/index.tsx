import { Card, Tag, Empty, Timeline } from 'antd';
import {
  ThunderboltOutlined,
  LinkOutlined,
  CalculatorOutlined,
  ApartmentOutlined,
  BulbOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useWorkspace } from '../../hooks/useWorkspace';
import type { InsightItem, InsightType, InsightSeverity } from '../../types';

// ---- Config maps ----

const insightTypeConfig: Record<
  InsightType,
  { icon: React.ReactNode; color: string; label: string }
> = {
  event_trigger: {
    icon: <ThunderboltOutlined />,
    color: '#1677ff',
    label: '事件触发',
  },
  risk_propagation: {
    icon: <LinkOutlined />,
    color: '#fa8c16',
    label: '风险传导',
  },
  quantitative_impact: {
    icon: <CalculatorOutlined />,
    color: '#722ed1',
    label: '量化影响',
  },
  network_analysis: {
    icon: <ApartmentOutlined />,
    color: '#f5222d',
    label: '网络分析',
  },
  recommendation: {
    icon: <BulbOutlined />,
    color: '#52c41a',
    label: '建议',
  },
};

const severityTagColor: Record<InsightSeverity, string> = {
  info: 'blue',
  warning: 'orange',
  critical: 'red',
};

const severityLabel: Record<InsightSeverity, string> = {
  info: '信息',
  warning: '警告',
  critical: '严重',
};

// ---- Component ----

export function InsightFeed() {
  const { state, dispatch } = useWorkspace();
  const { simulationHistory } = state;

  // Reverse chronological order (newest first)
  const reversedHistory = [...simulationHistory].reverse();

  const handleInsightClick = (insight: InsightItem) => {
    if (insight.target_node) {
      // Find the node to get its type
      const node = state.graphData?.nodes.find(
        (n) => n.id === insight.target_node,
      );
      if (node) {
        dispatch({
          type: 'SELECT_NODE',
          payload: { nodeId: node.id, nodeType: node.type },
        });
      }
    }
  };

  if (reversedHistory.length === 0) {
    return (
      <div className="panel-placeholder">
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="执行模拟后，智能洞察将在此显示"
        />
      </div>
    );
  }

  return (
    <div style={{ padding: 12 }}>
      {reversedHistory.map((entry, histIdx) => {
        const ts = new Date(entry.timestamp);
        const timeStr = ts.toLocaleTimeString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        });

        return (
          <Card
            key={`sim-${histIdx}`}
            size="small"
            title={
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 13,
                }}
              >
                <ThunderboltOutlined style={{ color: '#fa8c16' }} />
                <span style={{ fontWeight: 600 }}>{entry.displayName}</span>
              </div>
            }
            extra={
              <span style={{ fontSize: 11, color: '#999' }}>
                <ClockCircleOutlined style={{ marginRight: 4 }} />
                {timeStr}
              </span>
            }
            style={{ marginBottom: 12 }}
            styles={{
              header: { padding: '4px 12px', minHeight: 36 },
              body: { padding: '8px 12px' },
            }}
          >
            <Timeline
              items={entry.insights.map((insight, insIdx) => {
                const typeConf =
                  insightTypeConfig[insight.type] ?? insightTypeConfig.event_trigger;
                const isCritical = insight.severity === 'critical';

                return {
                  key: `${histIdx}-${insIdx}`,
                  dot: (
                    <span style={{ color: typeConf.color, fontSize: 14 }}>
                      {typeConf.icon}
                    </span>
                  ),
                  children: (
                    <div
                      onClick={() => handleInsightClick(insight)}
                      style={{
                        cursor: insight.target_node ? 'pointer' : 'default',
                        padding: '6px 8px',
                        borderRadius: 6,
                        border: isCritical
                          ? '1px solid #ff4d4f'
                          : '1px solid #f0f0f0',
                        background: isCritical ? '#fff1f0' : '#fafafa',
                        transition: 'box-shadow 0.2s',
                        ...(isCritical
                          ? { animation: 'insightPulse 2s ease-in-out infinite' }
                          : {}),
                      }}
                      onMouseEnter={(e) => {
                        if (insight.target_node) {
                          (e.currentTarget as HTMLDivElement).style.boxShadow =
                            '0 1px 4px rgba(0,0,0,0.12)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLDivElement).style.boxShadow =
                          'none';
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                          marginBottom: 4,
                        }}
                      >
                        <Tag
                          color={typeConf.color}
                          style={{
                            fontSize: 11,
                            lineHeight: '18px',
                            padding: '0 4px',
                            marginRight: 0,
                          }}
                        >
                          {typeConf.label}
                        </Tag>
                        <Tag
                          color={severityTagColor[insight.severity]}
                          style={{
                            fontSize: 11,
                            lineHeight: '18px',
                            padding: '0 4px',
                            marginRight: 0,
                          }}
                        >
                          {severityLabel[insight.severity]}
                        </Tag>
                      </div>
                      <div style={{ fontSize: 12, color: '#333', lineHeight: 1.5 }}>
                        {insight.text}
                      </div>
                      {insight.target_node && (
                        <div
                          style={{
                            fontSize: 11,
                            color: '#999',
                            marginTop: 2,
                          }}
                        >
                          目标: {insight.target_node}
                        </div>
                      )}
                    </div>
                  ),
                };
              })}
            />
          </Card>
        );
      })}
    </div>
  );
}
