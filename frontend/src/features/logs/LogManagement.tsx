import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Typography, Select, Spin, message } from 'antd';
import { FileTextOutlined, ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import createAPI from '@/services/api';

const { Title, Paragraph } = Typography;
const { Option } = Select;

const LogManagement: React.FC = () => {
  const [logFiles, setLogFiles] = useState<string[]>([]);
  const [selectedLog, setSelectedLog] = useState<string | null>(null);
  const [logContent, setLogContent] = useState<string>('');
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingContent, setLoadingContent] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const api = createAPI();

  const fetchLogFiles = async () => {
    setLoadingFiles(true);
    try {
      const response = await api.get('/logs');
      setLogFiles(response.data.logs || []);
      
      // 如果有日志文件，默认选择第一个
      if (response.data.logs && response.data.logs.length > 0) {
        setSelectedLog(response.data.logs[0]);
        fetchLogContent(response.data.logs[0]);
      }
    } catch (error) {
      messageApi.error('获取日志文件列表失败，请检查网络连接和API设置');
      console.error('获取日志文件列表失败:', error);
    } finally {
      setLoadingFiles(false);
    }
  };

  const fetchLogContent = async (filename: string) => {
    setLoadingContent(true);
    try {
      const response = await api.get(`/logs/${filename}`, {
        responseType: 'text',
        transformResponse: [(data) => data], // 防止自动JSON解析
      });
      setLogContent(response.data);
    } catch (error) {
      messageApi.error('获取日志内容失败，请重试');
      console.error('获取日志内容失败:', error);
      setLogContent('');
    } finally {
      setLoadingContent(false);
    }
  };

  useEffect(() => {
    fetchLogFiles();
  }, []);

  const handleLogSelect = (value: string) => {
    setSelectedLog(value);
    fetchLogContent(value);
  };

  const handleDownload = () => {
    if (!selectedLog || !logContent) {
      messageApi.warning('没有可下载的日志内容');
      return;
    }

    // 创建Blob对象
    const blob = new Blob([logContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    // 创建下载链接
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedLog;
    document.body.appendChild(a);
    a.click();
    
    // 清理
    URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    messageApi.success('日志文件下载成功');
  };

  // 将日志内容按行分割，用于表格显示
  const logLines = logContent ? logContent.split('\n').map((line, index) => ({
    key: index,
    line: index + 1,
    content: line,
  })) : [];

  const columns = [
    {
      title: '行号',
      dataIndex: 'line',
      key: 'line',
      width: 80,
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
  ];

  return (
    <>
      {contextHolder}
      <Card 
        title={<Title level={4}>日志管理</Title>}
        extra={
          <Space>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={fetchLogFiles}
              loading={loadingFiles}
            >
              刷新
            </Button>
            <Button 
              type="primary" 
              icon={<DownloadOutlined />}
              onClick={handleDownload}
              disabled={!selectedLog || !logContent}
            >
              下载日志
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Paragraph>选择要查看的日志文件：</Paragraph>
            <Select
              style={{ width: 300 }}
              placeholder="选择日志文件"
              onChange={handleLogSelect}
              value={selectedLog}
              loading={loadingFiles}
              disabled={loadingFiles || logFiles.length === 0}
            >
              {logFiles.map(file => (
                <Option key={file} value={file}>
                  <Space>
                    <FileTextOutlined />
                    {file}
                  </Space>
                </Option>
              ))}
            </Select>
          </div>
          
          <Spin spinning={loadingContent}>
            <Card 
              title={selectedLog ? `日志内容: ${selectedLog}` : '日志内容'} 
              style={{ marginTop: 16 }}
              bodyStyle={{ padding: 0 }}
            >
              {logContent ? (
                <Table
                  columns={columns}
                  dataSource={logLines}
                  pagination={{ 
                    showSizeChanger: true, 
                    pageSizeOptions: ['10', '20', '50', '100', '200'],
                    defaultPageSize: 50,
                    showTotal: (total, range) => `${range[0]}-${range[1]} 共 ${total} 项`
                  }}
                  size="small"
                  scroll={{ y: 400 }}
                />
              ) : (
                <div style={{ padding: 24, textAlign: 'center' }}>
                  {logFiles.length > 0 ? '请选择日志文件查看内容' : '没有可用的日志文件'}
                </div>
              )}
            </Card>
          </Spin>
        </Space>
      </Card>
    </>
  );
};

export default LogManagement;
