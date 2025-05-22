import React, { useState } from 'react';
import { Card, Button, Space, Typography, Row, Col, Statistic, Badge, Spin, message } from 'antd';
import { LockOutlined, UnlockOutlined, SyncOutlined } from '@ant-design/icons';
import createAPI from '@/services/api';

const { Title, Paragraph } = Typography;

const DoorControl: React.FC = () => {
  const [doorStatus, setDoorStatus] = useState<'locked' | 'unlocked' | 'unknown'>('unknown');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const api = createAPI();

  const fetchDoorStatus = async () => {
    setLoading(true);
    try {
      const response = await api.get('/servo/status');
      setDoorStatus(response.data.status);
    } catch (error) {
      messageApi.error('获取门状态失败，请检查网络连接和API设置');
      console.error('获取门状态失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLock = async () => {
    setActionLoading(true);
    try {
      await api.post('/servo/lock');
      messageApi.success('门已锁定');
      setDoorStatus('locked');
    } catch (error) {
      messageApi.error('锁门操作失败，请重试');
      console.error('锁门操作失败:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnlock = async () => {
    setActionLoading(true);
    try {
      await api.post('/servo/unlock');
      messageApi.success('门已解锁');
      setDoorStatus('unlocked');
    } catch (error) {
      messageApi.error('解锁操作失败，请重试');
      console.error('解锁操作失败:', error);
    } finally {
      setActionLoading(false);
    }
  };

  React.useEffect(() => {
    fetchDoorStatus();
  }, []);

  const getStatusBadge = () => {
    if (doorStatus === 'locked') {
      return <Badge status="error" text="已锁定" />;
    } else if (doorStatus === 'unlocked') {
      return <Badge status="success" text="已解锁" />;
    } else {
      return <Badge status="default" text="未知状态" />;
    }
  };

  return (
    <>
      {contextHolder}
      <Card title={<Title level={4}>门控系统</Title>}>
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Card>
              <Spin spinning={loading}>
                <Statistic
                  title="当前门状态"
                  value={doorStatus === 'locked' ? '已锁定' : doorStatus === 'unlocked' ? '已解锁' : '未知状态'}
                  valueStyle={{
                    color: doorStatus === 'locked' ? '#ff4d4f' : doorStatus === 'unlocked' ? '#52c41a' : '#d9d9d9',
                  }}
                  prefix={
                    doorStatus === 'locked' ? (
                      <LockOutlined />
                    ) : doorStatus === 'unlocked' ? (
                      <UnlockOutlined />
                    ) : (
                      <SyncOutlined spin />
                    )
                  }
                />
                <div style={{ marginTop: 16 }}>
                  <Space>
                    <Button
                      type="primary"
                      icon={<SyncOutlined />}
                      onClick={fetchDoorStatus}
                      loading={loading}
                    >
                      刷新状态
                    </Button>
                    {getStatusBadge()}
                  </Space>
                </div>
              </Spin>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="门控操作">
              <Paragraph>
                通过以下按钮控制门锁的开关状态。请确保系统已正确连接到门锁硬件。
              </Paragraph>
              <Space size="large" style={{ marginTop: 16 }}>
                <Button
                  type="primary"
                  icon={<UnlockOutlined />}
                  onClick={handleUnlock}
                  loading={actionLoading}
                  size="large"
                  style={{ minWidth: 120 }}
                >
                  解锁门
                </Button>
                <Button
                  danger
                  icon={<LockOutlined />}
                  onClick={handleLock}
                  loading={actionLoading}
                  size="large"
                  style={{ minWidth: 120 }}
                >
                  锁定门
                </Button>
              </Space>
            </Card>
          </Col>
        </Row>
      </Card>
    </>
  );
};

export default DoorControl;
