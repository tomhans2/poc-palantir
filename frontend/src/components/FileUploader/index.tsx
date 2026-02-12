import { useState, useEffect, useCallback } from 'react';
import { Upload, Select, Button, message, Divider, Space } from 'antd';
import { InboxOutlined, CloudUploadOutlined } from '@ant-design/icons';
import { loadWorkspace, getSamples } from '../../services/api';
import { useWorkspace } from '../../hooks/useWorkspace';
import type { SampleInfo } from '../../types';
import type { UploadFile } from 'antd/es/upload/interface';

const { Dragger } = Upload;

export function FileUploader({ onSuccess }: { onSuccess?: () => void } = {}) {
  const { dispatch } = useWorkspace();
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSample, setSelectedSample] = useState<string | undefined>(
    undefined,
  );

  useEffect(() => {
    getSamples()
      .then(setSamples)
      .catch(() => {
        /* backend may not be running */
      });
  }, []);

  const handleLoad = useCallback(
    async (fileOrSample: File | string) => {
      setLoading(true);
      try {
        const resp = await loadWorkspace(fileOrSample);
        dispatch({
          type: 'LOAD_WORKSPACE',
          payload: {
            metadata: resp.metadata,
            ontologyDef: resp.ontology_def,
            graphData: resp.graph_data,
            actions: resp.actions,
          },
        });
        message.success('工作区加载成功');
        onSuccess?.();
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : '加载失败，请检查 JSON 格式';
        message.error(msg);
      } finally {
        setLoading(false);
      }
    },
    [dispatch],
  );

  const handleFileUpload = useCallback(
    (file: UploadFile) => {
      if (file.originFileObj) {
        handleLoad(file.originFileObj);
      }
      return false;
    },
    [handleLoad],
  );

  const handleSampleChange = useCallback(
    (value: string) => {
      setSelectedSample(value);
      handleLoad(value);
    },
    [handleLoad],
  );

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Dragger
        accept=".json"
        showUploadList={false}
        beforeUpload={() => false}
        onChange={({ file }) => handleFileUpload(file)}
        disabled={loading}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">拖拽 JSON 文件到此处上传</p>
        <p className="ant-upload-hint">支持自定义知识图谱 JSON 文件</p>
      </Dragger>

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
