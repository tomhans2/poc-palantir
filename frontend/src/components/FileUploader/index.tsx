import { useState, useEffect, useCallback, useRef } from 'react';
import {
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
  CloudUploadOutlined,
  PythonOutlined,
  FileTextOutlined,
  DeleteOutlined,
  FileAddOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { loadWorkspace, getSamples } from '../../services/api';
import { useWorkspace } from '../../hooks/useWorkspace';
import type { SampleInfo } from '../../types';

const { Text } = Typography;

export function FileUploader({ onSuccess }: { onSuccess?: () => void } = {}) {
  const { dispatch } = useWorkspace();
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSample, setSelectedSample] = useState<string | undefined>(
    undefined,
  );
  const [jsonFile, setJsonFile] = useState<File | null>(null);
  const [pythonFile, setPythonFile] = useState<File | null>(null);
  const [lastWarnings, setLastWarnings] = useState<string[]>([]);

  const jsonInputRef = useRef<HTMLInputElement>(null);
  const pyInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getSamples()
      .then(setSamples)
      .catch(() => {
        /* backend may not be running */
      });
  }, []);

  // ---- Core load function ----
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

        if (resp.warnings && resp.warnings.length > 0) {
          setLastWarnings(resp.warnings);
          message.warning(
            `工作区已加载，但有 ${resp.warnings.length} 个警告`,
          );
        } else {
          message.success('工作区加载成功');
        }

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

        // Clear file selections after successful load
        setJsonFile(null);
        setPythonFile(null);
        onSuccess?.();
      } catch (err: unknown) {
        console.error('[FileUploader] Load failed:', err);
        let msg = '加载失败，请检查文件格式';
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as {
            response?: { data?: { detail?: string | unknown[] } };
          };
          const detail = axiosErr.response?.data?.detail;
          if (typeof detail === 'string') {
            msg = detail;
          } else if (Array.isArray(detail)) {
            msg = (detail as { msg?: string; loc?: string[] }[])
              .map((d) => {
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

  // ---- Native file input handlers (bypassing Antd Upload) ----
  const handleJsonFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setJsonFile(file);
        setSelectedSample(undefined); // Clear sample selection
      }
      // Reset input so the same file can be re-selected
      e.target.value = '';
    },
    [],
  );

  const handlePythonFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setPythonFile(file);
        message.info(`Python 动作文件 "${file.name}" 已选择`);
      }
      e.target.value = '';
    },
    [],
  );

  // ---- Upload button click ----
  const handleUploadClick = useCallback(() => {
    if (jsonFile) {
      handleLoad(jsonFile, pythonFile || undefined);
    }
  }, [jsonFile, pythonFile, handleLoad]);

  // ---- Sample selection ----
  const handleSampleChange = useCallback(
    (value: string) => {
      setSelectedSample(value);
      setJsonFile(null); // Clear file selection when using sample
      setPythonFile(null);
      handleLoad(value);
    },
    [handleLoad],
  );

  // ---- Remove file handlers ----
  const handleRemoveJson = useCallback(() => {
    setJsonFile(null);
  }, []);

  const handleRemovePython = useCallback(() => {
    setPythonFile(null);
  }, []);

  // ---- Drop zone handler ----
  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      const files = Array.from(e.dataTransfer.files);
      for (const file of files) {
        if (file.name.endsWith('.json')) {
          setJsonFile(file);
          setSelectedSample(undefined);
        } else if (file.name.endsWith('.py')) {
          setPythonFile(file);
          message.info(`Python 动作文件 "${file.name}" 已选择`);
        }
      }
    },
    [],
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* Hidden native file inputs */}
      <input
        ref={jsonInputRef}
        type="file"
        accept=".json"
        style={{ display: 'none' }}
        onChange={handleJsonFileChange}
      />
      <input
        ref={pyInputRef}
        type="file"
        accept=".py"
        style={{ display: 'none' }}
        onChange={handlePythonFileChange}
      />

      {/* Drop zone + file selection area */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        style={{
          border: '2px dashed #d9d9d9',
          borderRadius: 8,
          padding: '20px 16px',
          textAlign: 'center',
          background: jsonFile ? '#f0f5ff' : '#fafafa',
          cursor: 'pointer',
          transition: 'all 0.3s',
        }}
        onClick={() => !jsonFile && jsonInputRef.current?.click()}
      >
        {jsonFile ? (
          <Space direction="vertical" size="small">
            <Tag
              icon={<FileTextOutlined />}
              color="blue"
              closable
              onClose={handleRemoveJson}
              style={{ fontSize: 14, padding: '4px 12px' }}
            >
              {jsonFile.name}{' '}
              <Text type="secondary" style={{ fontSize: 12 }}>
                ({(jsonFile.size / 1024).toFixed(1)} KB)
              </Text>
            </Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              JSON 配置文件已选择，点击下方按钮加载
            </Text>
          </Space>
        ) : (
          <>
            <p style={{ marginBottom: 8 }}>
              <FileAddOutlined style={{ fontSize: 32, color: '#1890ff' }} />
            </p>
            <p style={{ margin: 0, fontWeight: 500 }}>
              点击选择或拖拽 JSON 配置文件
            </p>
            <p
              style={{
                margin: '4px 0 0 0',
                fontSize: 12,
                color: '#999',
              }}
            >
              支持 .json 和 .py 文件拖拽（自动识别类型）
            </p>
          </>
        )}
      </div>

      {/* Python file section */}
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
            上传包含 @register_action 装饰器函数的 .py 文件
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
                onClick={handleRemovePython}
              >
                移除
              </Button>
            </Space>
          ) : (
            <Button
              size="small"
              icon={<CloudUploadOutlined />}
              onClick={() => pyInputRef.current?.click()}
              disabled={loading}
            >
              选择 .py 文件
            </Button>
          )}
        </Space>
      </div>

      {/* Upload/Load button */}
      {jsonFile && (
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleUploadClick}
          loading={loading}
          block
          size="large"
        >
          {loading ? '加载中...' : '上传并加载图谱'}
        </Button>
      )}

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

      <Alert
        type="info"
        showIcon
        style={{ fontSize: 12 }}
        message="使用说明"
        description="上传的文件直接加载到当前会话，不会出现在内置示例下拉框中。下拉框仅显示服务器预置的示例场景。"
      />
    </Space>
  );
}
