'use client'

import { Layout } from 'antd'
import { usePathname } from 'next/navigation'
import AppSidebar from './AppSidebar'

export default function AppLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname()

    // 登入、注冊等頁面不需要侧边栏
    const noSidebarRoutes = ['/login', '/register', '/forgot-password']
    const isNoSidebarRoute = noSidebarRoutes.includes(pathname)

    if (isNoSidebarRoute) {
        return <>{children}</>
    }

    return (
        <Layout hasSider className="h-screen overflow-hidden bg-slate-50/50">
            <AppSidebar />
            <Layout className="flex flex-col flex-1 h-full min-w-0 overflow-hidden bg-transparent relative">
                {children}
            </Layout>
        </Layout>
    )
}
