import React, { useState, useEffect, useRef } from 'react';
import { Table, Button, Space, Typography, Card, Popconfirm, message, Empty, Modal, Form, Input, Spin } from 'antd';
import { PlusOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import createAPI from '@/services/api';
import useSettingsStore from '@/store/settings';

const { Title } = Typography;

interface FingerprintData {
  id: string;
  name: string;
}

const FingerprintList: React.FC = () => {
  const [fingerprints, setFingerprints] = useState<FingerprintData[]>([]);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const [isAddModalVisible, setIsAddModalVisible] = useState(false);
  const [sseLog, setSseLog] = useState<string[]>([]);
  const [isRegistering, setIsRegistering] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const sseLogContainerRef = useRef<HTMLDivElement>(null); // Added ref for SSE log container
  const [form] = Form.useForm();

  const api = createAPI();

  const fetchFingerprints = async () => {
    setLoading(true);
    try {
      const response = await api.get('/fingerprints');
      const data = response.data;
      
      // 转换对象格式为数组格式，方便表格显示
      const fingerprintArray = Object.entries(data).map(([id, name]) => ({
        id,
        name: name as string,
      }));
      
      setFingerprints(fingerprintArray);
    } catch (error) {
      messageApi.error('获取指纹列表失败，请检查网络连接和API设置');
      console.error('获取指纹列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFingerprints();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  // Added eslint-disable-line for exhaustive-deps as fetchFingerprints is stable if api is stable.
  // If api can change, it should be a dependency. For now, assuming it's stable.

  // useEffect to scroll SSE log to bottom
  useEffect(() => {
    if (sseLogContainerRef.current) {
      sseLogContainerRef.current.scrollTop = sseLogContainerRef.current.scrollHeight;
    }
  }, [sseLog]);

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/fingerprints/${id}`);
      messageApi.success('指纹删除成功');
      fetchFingerprints(); // 重新加载列表
    } catch (error) {
      messageApi.error('指纹删除失败，请重试');
      console.error('指纹删除失败:', error);
    }
  };

  const showAddModal = () => {
    form.resetFields();
    setSseLog([]);
    setIsRegistering(false);
    if (abortControllerRef.current) {
      abortControllerRef.current.abort(); // Abort any previous request
      abortControllerRef.current = null;
    }
    setIsAddModalVisible(true);
  };

  const handleModalCloseOrCancel = () => {
    if (isRegistering && abortControllerRef.current && !abortControllerRef.current.signal.aborted) {
      abortControllerRef.current.abort();
    }
    setIsAddModalVisible(false);
    setSseLog([]);
    setIsRegistering(false); // Ensure registration state is reset
    form.resetFields();
  };

  const handleAddFingerprint = async (values: { name: string }) => {
    setIsRegistering(true);
    setSseLog([`Starting registration for "${values.name}"...`]);
    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;
    const { baseUrl, token } = useSettingsStore.getState();

    try {
      const response = await fetch(`${baseUrl}/fingerprints`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ name: values.name }),
        signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to parse error response from server.' }));
        const errorMessage = `Error ${response.status}: ${errorData.message || 'Registration failed to start.'}`;
        messageApi.error(errorMessage);
        setSseLog(prev => [...prev, errorMessage]);
        setIsRegistering(false);
        return;
      }

      if (!response.body) {
        const noBodyMessage = 'No response body from server for SSE.';
        messageApi.error(noBodyMessage);
        setSseLog(prev => [...prev, noBodyMessage]);
        setIsRegistering(false);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          setSseLog(prev => [...prev, 'Registration stream ended.']);
          if (isRegistering) { // If still registering, means it ended unexpectedly
            messageApi.warning('Registration process ended without a clear status.');
            setIsRegistering(false);
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last partial line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonData = line.substring('data: '.length);
            try {
              const eventData = JSON.parse(jsonData);
              setSseLog(prev => [...prev, eventData.message || JSON.stringify(eventData)]);

              if (eventData.status === 'success') {
                messageApi.success(eventData.message || 'Fingerprint registered successfully!');
                setIsRegistering(false);
                fetchFingerprints();
                reader.cancel(); // Close the stream
                // Auto-close modal after a short delay
                setTimeout(() => {
                  setIsAddModalVisible(false); 
                  form.resetFields();
                  setSseLog([]); // Clear logs after closing
                }, 1500); // 1.5 seconds delay
                return; 
              } else if (eventData.status === 'error') {
                messageApi.error(eventData.message || 'An error occurred during registration.');
                setIsRegistering(false);
                // Keep modal open to show error log
                // reader.cancel(); // Optionally close stream on first error
                // return; 
              } else if (eventData.status === 'cancelled') {
                messageApi.info(eventData.message || 'Registration was cancelled.');
                setIsRegistering(false);
                reader.cancel();
                return;
              }
              // For 'progress' status, log is already updated.
            } catch (e: any) {
              console.error('Error parsing SSE JSON:', e, jsonData);
              setSseLog(prev => [...prev, `Error parsing SSE event: ${e.message}`]);
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        const abortMessage = 'Fingerprint registration cancelled by user.';
        messageApi.info(abortMessage);
        setSseLog(prev => [...prev, abortMessage]);
      } else {
        const networkErrorMessage = `Connection error: ${error.message}`;
        messageApi.error(networkErrorMessage);
        console.error('Fingerprint registration failed:', error);
        setSseLog(prev => [...prev, networkErrorMessage]);
      }
    } finally {
      setIsRegistering(false);
      if (abortControllerRef.current && abortControllerRef.current.signal === signal) { // Check if it's the same controller
          abortControllerRef.current = null;
      }
    }
  };


  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
    },
    {
      title: '用户名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: FingerprintData) => (
        <Popconfirm
          title="删除指纹"
          description={`确定要删除用户 "${record.name}" 的指纹吗？`}
          onConfirm={() => handleDelete(record.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button 
            danger 
            icon={<DeleteOutlined />} 
            size="small"
          >
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      {contextHolder}
      <Card
        title={<Title level={4}>指纹管理</Title>}
        extra={
          <Space>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={fetchFingerprints}
              loading={loading}
            >
              刷新
            </Button>
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={showAddModal}
            >
              添加指纹
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={fingerprints}
          rowKey="id"
          loading={loading}
          pagination={false}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="暂无指纹数据"
              />
            ),
          }}
        />
      </Card>

      <Modal
        title="添加新指纹"
        visible={isAddModalVisible}
        onCancel={handleModalCloseOrCancel}
        maskClosable={!isRegistering}
        closable={!isRegistering}
        footer={
          isRegistering
            ? [
                <Button key="cancelOp" onClick={() => {
                  if (abortControllerRef.current) {
                    abortControllerRef.current.abort();
                  }
                }}>
                  取消注册
                </Button>,
              ]
            : [
                <Button key="close" onClick={handleModalCloseOrCancel}>
                  取消
                </Button>,
                <Button key="submit" type="primary" onClick={() => form.submit()}>
                  注册
                </Button>,
              ]
        }
      >
        <Form form={form} layout="vertical" onFinish={handleAddFingerprint}>
          <Form.Item
            name="name"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名!' }]}
          >
            <Input placeholder="请输入用户名" disabled={isRegistering} />
          </Form.Item>
          {(sseLog.length > 0 || isRegistering) && (
            <div>
              <Title level={5}>注册状态:</Title>
              <div 
                ref={sseLogContainerRef} // Attach ref here
                style={{ 
                  maxHeight: '200px', 
                  overflowY: 'auto', 
                  border: '1px solid #d9d9d9', 
                  padding: '8px', 
                  marginBottom: '10px', 
                  background: '#f5f5f5',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                {sseLog.map((log, index) => (
                  <div key={index}>{log}</div>
                ))}
                {isRegistering && 
                 !sseLog.some(s => s.toLowerCase().includes("error") || 
                                   s.toLowerCase().includes("cancelled") ||
                                   s.toLowerCase().includes("aborted") ||
                                   s.toLowerCase().includes("stream ended") ||
                                   s.toLowerCase().includes("success") // Also check for success to stop spinner
                                   ) && 
                 <Space><Spin size="small" /> 处理中</Space>}
              </div>
            </div>
          )}
        </Form>
      </Modal>
    </>
  );
};

export default FingerprintList;
