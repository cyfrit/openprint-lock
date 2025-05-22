import React from 'react';
import { Form, Input, Button, Card, Switch, Space, Typography, theme } from 'antd';
import { SaveOutlined, UndoOutlined, LinkOutlined, KeyOutlined } from '@ant-design/icons';
import useSettingsStore from '@/store/settings';

const { Title, Text } = Typography;

const SettingsForm: React.FC = () => {
  const { token: themeToken } = theme.useToken();
  const { baseUrl, token, isDarkMode, setBaseUrl, setToken, toggleDarkMode, reset } = useSettingsStore();
  
  const [form] = Form.useForm();
  
  React.useEffect(() => {
    // 当store中的值变化时，更新表单
    form.setFieldsValue({
      baseUrl,
      token,
    });
  }, [baseUrl, token, form]);
  
  const handleSave = (values: { baseUrl: string; token: string }) => {
    setBaseUrl(values.baseUrl);
    setToken(values.token);
  };
  
  const handleReset = () => {
    reset();
    form.setFieldsValue({
      baseUrl: 'http://localhost:80',
      token: 'fingerprint_system_token_2025_secure',
    });
  };
  
  return (
    <Card 
      title={
        <Space>
          <Title level={4} style={{ margin: 0 }}>系统设置</Title>
        </Space>
      }
      style={{ 
        maxWidth: 600, 
        margin: '0 auto',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
        borderRadius: themeToken.borderRadiusLG,
      }}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ baseUrl, token }}
        onFinish={handleSave}
      >
        <Form.Item
          name="baseUrl"
          label="基础URL"
          rules={[
            { required: true, message: '请输入基础URL' },
            { type: 'url', message: '请输入有效的URL格式' }
          ]}
          tooltip="指纹系统API的基础URL，格式为: http://<ESP32_IP_ADDRESS>:<API_PORT>"
        >
          <Input 
            prefix={<LinkOutlined />} 
            placeholder="http://192.168.1.100:80" 
          />
        </Form.Item>
        
        <Form.Item
          name="token"
          label="认证令牌"
          rules={[{ required: true, message: '请输入认证令牌' }]}
          tooltip="用于API认证的Bearer Token"
        >
          <Input.Password 
            prefix={<KeyOutlined />} 
            placeholder="输入认证令牌" 
          />
        </Form.Item>
        
        <Form.Item label="界面主题">
          <Space>
            <Switch 
              checked={isDarkMode} 
              onChange={toggleDarkMode} 
              checkedChildren="暗色" 
              unCheckedChildren="亮色" 
            />
            <Text type="secondary">
              {isDarkMode ? '暗色模式' : '亮色模式'}
            </Text>
          </Space>
        </Form.Item>
        
        <Form.Item>
          <Space>
            <Button 
              type="primary" 
              htmlType="submit" 
              icon={<SaveOutlined />}
            >
              保存设置
            </Button>
            <Button 
              onClick={handleReset} 
              icon={<UndoOutlined />}
            >
              恢复默认
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default SettingsForm;
