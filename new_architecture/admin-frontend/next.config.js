/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  
  // 环境变量
  env: {
    API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8000',
  },
  
  // 图片配置
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  
  // 重写配置（用于开发代理）
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_BASE_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
  
  // 编译配置
  compiler: {
    // 移除 console.log 在生产环境
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },
  
  // 输出配置
  output: 'standalone',
};

module.exports = nextConfig;