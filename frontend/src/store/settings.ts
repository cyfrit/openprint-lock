import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { SettingsState } from '@/types/settings';

// 创建设置状态存储
const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      baseUrl: 'http://localhost:80', // 默认基础URL
      token: '', // 默认令牌
      isDarkMode: false, // 默认浅色模式
      
      // 设置基础URL
      setBaseUrl: (url: string) => set({ baseUrl: url }),
      
      // 设置认证令牌
      setToken: (token: string) => set({ token: token }),
      
      // 切换暗黑/浅色模式
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
      
      // 重置所有设置为默认值
      reset: () => set({
        baseUrl: 'http://localhost:80',
        token: '',
        isDarkMode: false,
      }),
    }),
    {
      name: 'fingerprint-system-settings', // localStorage的键名
    }
  )
);

export default useSettingsStore;
