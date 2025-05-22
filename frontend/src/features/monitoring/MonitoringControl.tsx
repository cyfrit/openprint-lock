import React, { useState, useEffect } from 'react';
import { Card, Button, Space, Typography, Row, Col, Statistic, Badge, Switch, message } from 'antd';
import { EyeOutlined, EyeInvisibleOutlined, SyncOutlined } from '@ant-design/icons';
import createAPI from '@/services/api';

const { Title, Paragraph } = Typography;

const MonitoringControl: React.FC = () => {
  const [monitoringStatus, setMonitoringStatus] = useState<'enabled_and_active' | 'enabled_but_paused' | 'disabled' | 'unknown'>('unknown');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const api = createAPI();

  const fetchMonitoringStatus = async () => {
    setLoading(true);
    try {
      const response = await api.get('/monitoring/status');
      setMonitoringStatus(response.data.status);
    } catch (error) {
      messageApi.error('获取监控状态失败，请检查网络连接和API设置');
      console.error('获取监控状态失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartMonitoring = async () => {
    setActionLoading(true);
    try {
      await api.post('/monitoring/start');
      messageApi.success('指纹监控已启动');
      setMonitoringStatus('enabled_and_active');
    } catch (error) {
      messageApi.error('启动监控失败，请重试');
      console.error('启动监控失败:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStopMonitoring = async () => {
    setActionLoading(true);
    try {
      await api.post('/monitoring/stop');
      messageApi.success('指纹监控已停止');
      setMonitoringStatus('disabled');
    } catch (error) {
      messageApi.error('停止监控失败，请重试');
      console.error('停止监控失败:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleMonitoring = (checked: boolean) => {
    if (checked) {
      handleStartMonitoring();
    } else {
      handleStopMonitoring();
    }
  };

  useEffect(() => {
    fetchMonitoringStatus();
  }, []);

  const getStatusBadge = () => {
    if (monitoringStatus === 'enabled_and_active') {
      return <Badge status="processing" text="监控中" />;
    } else if (monitoringStatus === 'enabled_but_paused') {
      return <Badge status="warning" text="已暂停" />;
    } else if (monitoringStatus === 'disabled') {
      return <Badge status="error" text="已停止" />;
    } else {
      return <Badge status="default" text="未知状态" />;
    }
  };

  const isActive = monitoringStatus === 'enabled_and_active';

  return (
    <>
      {contextHolder}
      <Card title={<Title level={4}>系统监控控制</Title>}>
        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Card>
              <Statistic
                title="当前监控状态"
                value={
                  monitoringStatus === 'enabled_and_active'
                    ? '监控中'
                    : monitoringStatus === 'enabled_but_paused'
                    ? '已暂停'
                    : monitoringStatus === 'disabled'
                    ? '已停止'
                    : '未知状态'
                }
                valueStyle={{
                  color:
                    monitoringStatus === 'enabled_and_active'
                      ? '#52c41a'
                      : monitoringStatus === 'enabled_but_paused'
                      ? '#faad14'
                      : monitoringStatus === 'disabled'
                      ? '#ff4d4f'
                      : '#d9d9d9',
                }}
                prefix={
                  monitoringStatus === 'enabled_and_active' ? (
                    <EyeOutlined />
                  ) : monitoringStatus === 'unknown' ? (
                    <SyncOutlined spin />
                  ) : (
                    <EyeInvisibleOutlined />
                  )
                }
              />
              <div style={{ marginTop: 16 }}>
                <Space>
                  <Button
                    type="primary"
                    icon={<SyncOutlined />}
                    onClick={fetchMonitoringStatus}
                    loading={loading}
                  >
                    刷新状态
                  </Button>
                  {getStatusBadge()}
                </Space>
              </div>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="监控操作">
              <Paragraph>
                通过以下控制开关启动或停止指纹监控系统。启动监控后，系统将持续检测指纹输入。
              </Paragraph>
              <div style={{ marginTop: 24, display: 'flex', alignItems: 'center' }}>
                <Switch
                  checked={isActive}
                  onChange={handleToggleMonitoring}
                  loading={actionLoading || loading}
                  checkedChildren="监控中"
                  unCheckedChildren="已停止"
                  style={{ marginRight: 16 }}
                />
                <span>
                  {isActive ? '系统正在监控指纹输入' : '指纹监控已停止'}
                </span>
              </div>
            </Card>
          </Col>
        </Row>
      </Card>
    </>
  );
};

export default MonitoringControl;
