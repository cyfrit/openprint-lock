import React from 'react';
import { Card, Row, Col, Statistic, Button, Space, Alert, Typography } from 'antd';
import { 
  ScanOutlined, 
  KeyOutlined, 
  EyeOutlined, 
  FileTextOutlined,
  LockOutlined,
  UnlockOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph } = Typography;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  
  return (
    <div>
      <Title level={2}>指纹门禁系统控制面板</Title>
      <Paragraph>欢迎使用指纹门禁系统。通过此控制面板，您可以管理指纹、控制门锁、监控系统状态以及查看日志。</Paragraph>
      
      <Alert 
        message="请确保已正确设置系统基础URL和认证令牌" 
        description="点击右上角的系统设置按钮可以配置连接参数。" 
        type="info" 
        showIcon 
        style={{ marginBottom: 24 }}
      />
      
      <Row gutter={[24, 24]}>
        <Col xs={24} sm={12} lg={6}>
          <Card 
            hoverable 
            onClick={() => navigate('/fingerprint')}
            style={{ height: '100%' }}
          >
            <Statistic 
              title="指纹管理" 
              value="管理用户指纹" 
              valueStyle={{ fontSize: '16px' }}
              prefix={<ScanOutlined style={{ fontSize: 36, color: '#1677ff' }} />} 
            />
            <div style={{ marginTop: 16 }}>
              <Button type="primary" onClick={(e) => {
                e.stopPropagation();
                navigate('/fingerprint');
              }}>
                进入管理
              </Button>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card 
            hoverable 
            onClick={() => navigate('/door')}
            style={{ height: '100%' }}
          >
            <Statistic 
              title="门控系统" 
              value="控制门锁状态" 
              valueStyle={{ fontSize: '16px' }}
              prefix={<KeyOutlined style={{ fontSize: 36, color: '#52c41a' }} />} 
            />
            <div style={{ marginTop: 16 }}>
              <Space>
                <Button 
                  type="primary" 
                  icon={<UnlockOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    // 这里可以添加开门的API调用
                  }}
                >
                  开门
                </Button>
                <Button 
                  danger 
                  icon={<LockOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    // 这里可以添加锁门的API调用
                  }}
                >
                  锁门
                </Button>
              </Space>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card 
            hoverable 
            onClick={() => navigate('/monitoring')}
            style={{ height: '100%' }}
          >
            <Statistic 
              title="系统监控" 
              value="监控系统状态" 
              valueStyle={{ fontSize: '16px' }}
              prefix={<EyeOutlined style={{ fontSize: 36, color: '#722ed1' }} />} 
            />
            <div style={{ marginTop: 16 }}>
              <Button type="primary" onClick={(e) => {
                e.stopPropagation();
                navigate('/monitoring');
              }}>
                查看状态
              </Button>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card 
            hoverable 
            onClick={() => navigate('/logs')}
            style={{ height: '100%' }}
          >
            <Statistic 
              title="日志管理" 
              value="查看系统日志" 
              valueStyle={{ fontSize: '16px' }}
              prefix={<FileTextOutlined style={{ fontSize: 36, color: '#fa8c16' }} />} 
            />
            <div style={{ marginTop: 16 }}>
              <Button type="primary" onClick={(e) => {
                e.stopPropagation();
                navigate('/logs');
              }}>
                查看日志
              </Button>
            </div>
          </Card>
        </Col>
      </Row>
      
      <div style={{ marginTop: 48 }}>
        <Title level={4}>系统信息</Title>
        <Paragraph>
          本系统提供指纹识别、门禁控制和日志记录功能。
          通过RESTful API接口，可以实现远程管理和控制。
        </Paragraph>
        <Paragraph>
          如需帮助，请参考API文档或联系系统管理员。
        </Paragraph>
      </div>
    </div>
  );
};

export default Dashboard;
