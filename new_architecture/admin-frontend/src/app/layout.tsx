import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { Providers } from '@/components/providers'

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
                colorPrimary: '#3b82f6',
                borderRadius: 6,
                colorLink: '#3b82f6',
              },
              components: {
                Layout: {
                  headerBg: '#ffffff',
                  headerPadding: '0 24px',
                },
                Menu: {
                  itemBorderRadius: 6,
                  itemMarginBlock: 4,
                  itemMarginInline: 4,
                },
                Button: {
                  borderRadius: 6,
                },
                Card: {
                  borderRadiusLG: 8,
                },
                Table: {
                  borderRadius: 8,
                },
              },
            }}
          >
            <Providers>
              {children}
            </Providers>
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  )
}