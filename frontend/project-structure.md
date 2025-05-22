# 指纹系统前端项目结构设计

## 项目技术栈
- React 18
- TypeScript
- Vite (构建工具)
- Ant Design (UI组件库)
- React Router (路由管理)
- Zustand (状态管理)
- Axios (HTTP请求)
- React Query (数据获取和缓存)
- ESLint + Prettier (代码规范)

## 目录结构
```
src/
├── assets/             # 静态资源文件
├── components/         # 通用组件
│   ├── Layout/         # 布局组件
│   ├── Settings/       # 设置相关组件
│   └── common/         # 其他通用组件
├── features/           # 功能模块
│   ├── fingerprint/    # 指纹管理模块
│   ├── door/           # 门控系统模块
│   ├── monitoring/     # 系统监控模块
│   └── logs/           # 日志管理模块
├── hooks/              # 自定义钩子
├── services/           # API服务
│   ├── api.ts          # API基础配置
│   ├── fingerprint.ts  # 指纹管理API
│   ├── door.ts         # 门控系统API
│   ├── monitoring.ts   # 系统监控API
│   └── logs.ts         # 日志管理API
├── store/              # 全局状态管理
│   ├── index.ts        # 状态存储入口
│   └── settings.ts     # 设置状态管理
├── types/              # 类型定义
├── utils/              # 工具函数
├── App.tsx             # 应用入口组件
├── main.tsx            # 应用入口文件
└── vite-env.d.ts       # Vite类型声明
```

## 页面结构
1. 主页面 (Dashboard)
   - 系统状态概览
   - 快速操作区域

2. 指纹管理页面
   - 指纹列表
   - 添加指纹 (SSE实时反馈)
   - 删除指纹

3. 门控系统页面
   - 开门/锁门控制
   - 门状态显示

4. 系统监控页面
   - 监控状态显示
   - 启动/停止监控控制

5. 日志管理页面
   - 日志文件列表
   - 日志内容查看

6. 设置页面
   - BaseURL配置
   - Token配置
   - 系统设置

## 全局状态管理
使用Zustand管理全局状态，主要包括：

1. 设置状态
   - baseUrl: 系统API基础URL
   - token: 认证令牌
   - 主题设置

2. 系统状态
   - 门状态
   - 监控状态
   - 连接状态

## 组件设计

### 布局组件
- AppLayout: 应用主布局，包含侧边栏、顶部导航和内容区
- Sidebar: 侧边导航栏
- Header: 顶部导航栏，包含设置入口
- Footer: 页脚信息

### 设置组件
- SettingsDrawer: 设置抽屉组件
- BaseUrlInput: 基础URL输入组件
- TokenInput: 令牌输入组件
- ThemeSwitch: 主题切换组件

### 指纹管理组件
- FingerprintList: 指纹列表组件
- FingerprintEnrollment: 指纹录入组件 (SSE)
- DeleteConfirmation: 删除确认组件

### 门控系统组件
- DoorControl: 门控制组件
- DoorStatus: 门状态显示组件

### 系统监控组件
- MonitoringControl: 监控控制组件
- MonitoringStatus: 监控状态显示组件

### 日志管理组件
- LogFileList: 日志文件列表组件
- LogViewer: 日志内容查看组件

## 响应式设计
- 使用Ant Design的栅格系统实现响应式布局
- 针对移动设备优化交互体验
- 支持暗黑模式和浅色模式切换

## API请求处理
- 使用Axios进行HTTP请求
- 全局配置请求拦截器，自动添加认证头
- 使用React Query管理数据获取、缓存和状态

## 错误处理
- 全局错误边界捕获React组件错误
- API请求错误统一处理
- 友好的错误提示UI

## 安全考虑
- Token存储在localStorage，提供清除选项
- 敏感操作需要二次确认
- 自动检测Token有效性
