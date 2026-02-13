import { useState, useEffect, useCallback } from 'react';
import {
  Upload,
  Select,
  Button,
  message,
  Divider,
  Space,
  Typography,
  Tag,
  Alert,
} from 'antd';
import {
  InboxOutlined,
  CloudUploadOutlined,
  PythonOutlined,
  FileTextOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { loadWorkspace, getSamples } from '../../services/api';
import { useWorkspace } from '../../hooks/useWorkspace';
import type { SampleInfo } from '../../types';
import type { UploadFile } from 'antd/es/upload/interface';

const { Dragger } = Upload;
const { Text } = Typography;

export function FileUploader({ onSuccess }: { onSuccess?: () => void } = {}) {
  const { dispatch } = useWorkspace();
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSample, setSelectedSample] = useState<string | undefined>(
    undefined,
  );
  const [pythonFile, setPythonFile] = useState<File | null>(null);
  const [lastWarnings, setLastWarnings] = useState<string[]>([]);

  useEffect(() => {
    getSamples()
      .then(setSamples)
      .catch(() => {
        /* backend may not be running */
      });
  }, []);

  const handleLoad = useCallback(
    async (fileOrSample: File | string, actionFile?: File) => {
      setLoading(true);
      setLastWarnings([]);
      try {
        const resp = await loadWorkspace(fileOrSample, actionFile);
        dispatch({
          type: 'LOAD_WORKSPACE',
          payload: {
            metadata: resp.metadata,
            ontologyDef: resp.ontology_def,
            graphData: resp.graph_data,
            actions: resp.actions,
            warnings: resp.warnings || [],
            registeredFunctions: resp.registered_functions || [],
          },
        });
        // Show warnings if any
        if (resp.warnings && resp.warnings.length > 0) {
          setLastWarnings(resp.warnings);
          message.warning(
            `工作区已加载，但有 ${resp.warnings.length} 个警告`,
          );
        } else {
          message.success('工作区加载成功');
        }
        // Show registered functions info
        if (resp.registered_functions && resp.registered_functions.length > 0) {
          const customCount = resp.registered_functions.filter(
            (f) => f.source === 'custom',
          ).length;
          if (customCount > 0) {
            message.info(
              `已注册 ${resp.registered_functions.length} 个动作函数（${customCount} 个来自自定义 Python 文件）`,
            );
          }
        }
        onSuccess?.();
      } catch (err: unknown) {
        let msg = '加载失败，请检查文件格式';
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as {
            response?: { data?: { detail?: string | unknown[] } };
          };
          const detail = axiosErr.response?.data?.detail;
          if (typeof detail === 'string') {
            msg = detail;
          } else if (Array.isArray(detail)) {
            msg = detail
              .map((d: { msg?: string; loc?: string[] }) => {
                const loc = d.loc?.join('.') || '';
                return `${loc}: ${d.msg || ''}`;
              })
              .join('\n');
          }
        } else if (err instanceof Error) {
          msg = err.message;
        }
        message.error(msg);
      } finally {
        setLoading(false);
      }
    },
    [dispatch, onSuccess],
  );

  const handleJsonUpload = useCallback(
    (file: UploadFile) => {
      if (file.originFileObj) {
        handleLoad(file.originFileObj, pythonFile || undefined);
      }
      return false;
    },
    [handleLoad, pythonFile],
  );

  const handlePythonUpload = useCallback(
    (file: UploadFile) => {
      if (file.originFileObj) {
        setPythonFile(file.originFileObj);
        message.info(
          `Python 动作文件 "${file.name}" 已准备就绪，上传 JSON 时将一并提交`,
        );
      }
      return false;
    },
    [],
  );

  const handleRemovePythonFile = useCallback(() => {
    setPythonFile(null);
    message.info('已移除 Python 动作文件');
  }, []);

  const handleSampleChange = useCallback(
    (value: string) => {
      setSelectedSample(value);
      setPythonFile(null); // Clear Python file when using sample
      handleLoad(value);
    },
    [handleLoad],
  );

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* JSON File Upload */}
      <Dragger
        accept=".json"
        showUploadList={false}
        beforeUpload={() => false}
        onChange={({ file }) => handleJsonUpload(file)}
        disabled={loading}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">拖拽 JSON 配置文件到此处上传</p>
        <p className="ant-upload-hint">支持自定义知识图谱 JSON 配置文件</p>
      </Dragger>

      {/* Python Action File Upload */}
      <div
        style={{
          border: '1px dashed #d9d9d9',
          borderRadius: 8,
          padding: '12px 16px',
          background: pythonFile ? '#f6ffed' : '#fafafa',
          transition: 'all 0.3s',
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <Space>
            <PythonOutlined style={{ fontSize: 16, color: '#3572A5' }} />
            <Text strong style={{ fontSize: 13 }}>
              Python 动作文件（可选）
            </Text>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            上传包含 @register_action 装饰器函数的 .py
            文件，为图谱配置自定义动作逻辑
          </Text>
          {pythonFile ? (
            <Space>
              <Tag icon={<FileTextOutlined />} color="green">
                {pythonFile.name}
              </Tag>
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={handleRemovePythonFile}
              >
                移除
              </Button>
            </Space>
          ) : (
            <Upload
              accept=".py"
              showUploadList={false}
              beforeUpload={() => false}
              onChange={({ file }) => handlePythonUpload(file)}
              disabled={loading}
            >
              <Button size="small" icon={<CloudUploadOutlined />}>
                选择 .py 文件
              </Button>
            </Upload>
          )}
        </Space>
      </div>

      {/* Warnings display */}
      {lastWarnings.length > 0 && (
        <Alert
          type="warning"
          showIcon
          closable
          message={`${lastWarnings.length} 个未注册函数警告`}
          description={
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {lastWarnings.map((w, i) => (
                <li key={i} style={{ fontSize: 12 }}>
                  {w}
                </li>
              ))}
            </ul>
          }
        />
      )}

      <Divider plain style={{ margin: '4px 0' }}>
        或选择内置示例
      </Divider>

      <Select
        className="sample-selector"
        placeholder="选择内置示例场景"
        value={selectedSample}
        onChange={handleSampleChange}
        loading={loading}
        allowClear
        options={samples.map((s) => ({
          label: s.description || s.name,
          value: s.name,
        }))}
      />

      {loading && (
        <Button type="primary" loading block icon={<CloudUploadOutlined />}>
          加载中...
        </Button>
      )}
    </Space>
  );
}
