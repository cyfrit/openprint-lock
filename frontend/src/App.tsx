import React from 'react';
import { App as AntApp } from 'antd';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import useSettingsStore from '@/store/settings';

import AppLayout from '@/components/Layout/AppLayout';
import Dashboard from '@/features/dashboard/Dashboard';
import FingerprintList from '@/features/fingerprint/FingerprintList';
import DoorControl from '@/features/door/DoorControl';
import MonitoringControl from '@/features/monitoring/MonitoringControl';
import LogManagement from '@/features/logs/LogManagement';

import './index.css';

// 创建 React Query 客户端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const App: React.FC = () => {
  const { isDarkMode } = useSettingsStore();
  
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDarkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="fingerprint" element={<FingerprintList />} />
              <Route path="door" element={<DoorControl />} />
              <Route path="monitoring" element={<MonitoringControl />} />
              <Route path="logs" element={<LogManagement />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
};

export default function Root() {
  return (
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>
  );
}
