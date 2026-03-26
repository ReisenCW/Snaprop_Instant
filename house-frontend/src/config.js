// 生产环境使用相对路径（通过 Nginx 反向代理）
// 开发环境使用本地地址
const isProduction = import.meta.env.PROD || import.meta.env.MODE === 'production';

export const API_BASE_URL = isProduction ? '' : 'http://127.0.0.1:5000';
export const WS_BASE_URL = isProduction ? '' : 'ws://127.0.0.1:5000';
