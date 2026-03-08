import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import { ConfigProvider, App } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { Providers } from '@/components/providers'
import AppLayout from '@/components/layout/AppLayout'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SmartCourseEngine - 智能课程管理系统',
  description: '基于AI的智能课程知识库管理系统',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <AntdRegistry>
          <ConfigProvider
            locale={zhCN}
            theme={{
              token: {
                colorPrimary: '#6366f1', // Indigo-500
                colorInfo: '#6366f1',
                colorSuccess: '#10b981', // Emerald-500
                colorWarning: '#f59e0b', // Amber-500
                colorError: '#ef4444', // Red-500
                borderRadius: 12,
                colorLink: '#6366f1',
                fontFamily: 'inherit',
              },
              components: {
                Layout: {
                  headerBg: 'rgba(255, 255, 255, 0.8)',
                  headerPadding: '0 24px',
                },
                Menu: {
                  itemBorderRadius: 10,
                  itemMarginBlock: 6,
                  itemMarginInline: 8,
                  itemSelectedBg: 'rgba(99, 102, 241, 0.1)',
                  itemSelectedColor: '#6366f1',
                },
                Button: {
                  borderRadius: 10,
                  controlHeight: 38,
                  fontWeight: 500,
                },
                Card: {
                  borderRadiusLG: 16,
                  boxShadowTertiary: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
                },
                Table: {
                  borderRadius: 16,
                },
                Input: {
                  borderRadius: 10,
                  controlHeight: 38,
                },
                Select: {
                  borderRadius: 10,
                  controlHeight: 38,
                }
              },
            }}
          >
            <App>
              <Providers>
                <AppLayout>
                  <div className="page-transition flex-1 flex flex-col min-w-0 h-full min-h-0">
                    {children}
                  </div>
                </AppLayout>
              </Providers>
            </App>
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  )
}