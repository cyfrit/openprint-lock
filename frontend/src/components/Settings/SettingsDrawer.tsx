import React from 'react';
import { Drawer, Button, Space } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import SettingsForm from './SettingsForm';

interface SettingsDrawerProps {
  // 可以添加额外的props
}

const SettingsDrawer: React.FC<SettingsDrawerProps> = () => {
  const [open, setOpen] = React.useState(false);

  const showDrawer = () => {
    setOpen(true);
  };

  const onClose = () => {
    setOpen(false);
  };

  return (
    <>
      <Button 
        type="text" 
        icon={<SettingOutlined />} 
        onClick={showDrawer}
        size="large"
      >
        系统设置
      </Button>
      <Drawer
        title="指纹系统设置"
        placement="right"
        onClose={onClose}
        open={open}
        width={400}
        styles={{
          body: {
            paddingBottom: 80,
          },
        }}
        footer={
          <Space>
            <Button onClick={onClose}>关闭</Button>
          </Space>
        }
      >
        <SettingsForm />
      </Drawer>
    </>
  );
};

export default SettingsDrawer;
