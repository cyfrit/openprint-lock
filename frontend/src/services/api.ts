import axios from 'axios';
import useSettingsStore from '@/store/settings';

// 创建axios实例
const createAPI = () => {
  const { baseUrl, token } = useSettingsStore.getState();
  
  const api = axios.create({
    baseURL: baseUrl,
    timeout: 10000,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  });
  
  // 请求拦截器 - 动态获取最新的baseUrl和token
  api.interceptors.request.use(
    (config) => {
      const { baseUrl, token } = useSettingsStore.getState();
      config.baseURL = baseUrl;
      config.headers.Authorization = `Bearer ${token}`;
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
  
  // 响应拦截器
  api.interceptors.response.use(
    (response) => {
      return response;
    },
    (error) => {
      // 处理错误响应
      if (error.response) {
        // 服务器返回错误状态码
        const { status } = error.response;
        
        switch (status) {
          case 401:
            console.error('认证失败，请检查Token设置');
            break;
          case 404:
            console.error('请求的资源不存在');
            break;
          case 500:
            console.error('服务器内部错误');
            break;
          default:
            console.error(`请求错误: ${status}`);
        }
      } else if (error.request) {
        // 请求发送但没有收到响应
        console.error('无法连接到服务器，请检查BaseURL设置或网络连接');
      } else {
        // 请求配置出错
        console.error('请求配置错误:', error.message);
      }
      
      return Promise.reject(error);
    }
  );
  
  return api;
};

export default createAPI;
