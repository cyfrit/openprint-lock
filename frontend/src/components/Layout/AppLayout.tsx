import React from 'react';
import { Layout, Menu, theme, ConfigProvider } from 'antd';
import { 
  HomeOutlined, 
  ScanOutlined, 
  KeyOutlined, 
  EyeOutlined, 
  FileTextOutlined 
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import SettingsDrawer from '@/components/Settings/SettingsDrawer';
import useSettingsStore from '@/store/settings';

const { Header, Sider, Content } = Layout;

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = React.useState(false);
  const { isDarkMode } = useSettingsStore();
  
  const { token: themeToken } = theme.useToken();
  
  // 根据当前路径确定选中的菜单项
  const selectedKey = React.useMemo(() => {
    const path = location.pathname;
    if (path.includes('/fingerprint')) return '2';
    if (path.includes('/door')) return '3';
    if (path.includes('/monitoring')) return '4';
    if (path.includes('/logs')) return '5';
    return '1'; // 默认选中首页
  }, [location.pathname]);
  
  // 菜单项点击处理
  const handleMenuClick = (key: string) => {
    switch (key) {
      case '1':
        navigate('/');
        break;
      case '2':
        navigate('/fingerprint');
        break;
      case '3':
        navigate('/door');
        break;
      case '4':
        navigate('/monitoring');
        break;
      case '5':
        navigate('/logs');
        break;
      default:
        navigate('/');
    }
  };
  
  return (
    <ConfigProvider
      theme={{
        algorithm: isDarkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <Sider 
          collapsible 
          collapsed={collapsed} 
          onCollapse={setCollapsed}
          style={{
            overflow: 'auto',
            height: '100vh',
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            zIndex: 1000,
          }}
        >
          <div style={{ 
            height: 64, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            padding: '16px',
            color: themeToken.colorPrimary,
            fontSize: collapsed ? '18px' : '20px',
            fontWeight: 'bold',
            overflow: 'hidden',
          }}>
            {collapsed ? '指纹' : '指纹门禁系统'}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[selectedKey]}
            items={[
              {
                key: '1',
                icon: <HomeOutlined />,
                label: '首页',
                onClick: () => handleMenuClick('1'),
              },
              {
                key: '2',
                icon: <ScanOutlined />,
                label: '指纹管理',
                onClick: () => handleMenuClick('2'),
              },
              {
                key: '3',
                icon: <KeyOutlined />,
                label: '门控系统',
                onClick: () => handleMenuClick('3'),
              },
              {
                key: '4',
                icon: <EyeOutlined />,
                label: '系统监控',
                onClick: () => handleMenuClick('4'),
              },
              {
                key: '5',
                icon: <FileTextOutlined />,
                label: '日志管理',
                onClick: () => handleMenuClick('5'),
              },
            ]}
          />
        </Sider>
        <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'all 0.2s' }}>
          <Header style={{ 
            padding: '0 16px', 
            background: themeToken.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            boxShadow: '0 1px 4px rgba(0, 0, 0, 0.05)',
            position: 'sticky',
            top: 0,
            zIndex: 999,
          }}>
            <SettingsDrawer />
          </Header>
          <Content style={{ 
            margin: '24px 16px', 
            padding: 24, 
            background: themeToken.colorBgContainer,
            borderRadius: themeToken.borderRadiusLG,
            minHeight: 280,
            overflow: 'initial',
          }}>
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

export default AppLayout;
