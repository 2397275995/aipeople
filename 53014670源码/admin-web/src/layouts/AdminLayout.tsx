import { Layout, Menu, Typography } from 'antd'
import {
  BookOutlined,
  DashboardOutlined,
  SmileOutlined,
} from '@ant-design/icons'
import { Link, Outlet, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout

export default function AdminLayout() {
  const location = useLocation()
  const selected = location.pathname.includes('/admin/knowledge')
    ? 'knowledge'
    : location.pathname.includes('/admin/sentiment')
      ? 'sentiment'
      : 'dashboard'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={0} theme="light">
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Typography.Text strong style={{ color: '#0d9488' }}>
            景区导览管理
          </Typography.Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selected]}
          items={[
            {
              key: 'dashboard',
              icon: <DashboardOutlined />,
              label: <Link to="/admin">数据大屏</Link>,
            },
            {
              key: 'knowledge',
              icon: <BookOutlined />,
              label: <Link to="/admin/knowledge">知识库管理</Link>,
            },
            {
              key: 'sentiment',
              icon: <SmileOutlined />,
              label: <Link to="/admin/sentiment">感受度分析</Link>,
            },
          ]}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Typography.Title level={4} style={{ margin: '16px 0', color: '#134e4a' }}>
            管理后台
          </Typography.Title>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
