import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert,
  Card,
  Form,
  Input,
  message,
  Progress,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd'
import { InboxOutlined, ReloadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import {
  getKbDocumentStatus,
  KbDocumentItem,
  listKbDocuments,
  uploadKbDocument,
} from '../services/api'

const { Dragger } = Upload
const { Title, Paragraph } = Typography

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '排队中' },
  parsing: { color: 'processing', label: '解析中' },
  chunking: { color: 'processing', label: '分块中' },
  indexing: { color: 'processing', label: '向量化' },
  ready: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
}

const ACCEPT = '.pdf,.txt,.md,.docx'

export default function KnowledgeManage() {
  const [documents, setDocuments] = useState<KbDocumentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [category, setCategory] = useState('other')
  const pollTimers = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map())

  const fetchList = useCallback(async () => {
    setLoading(true)
    try {
      const list = await listKbDocuments(30)
      setDocuments(list)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载文档列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchList()
    return () => {
      pollTimers.current.forEach((t) => clearInterval(t))
      pollTimers.current.clear()
    }
  }, [fetchList])

  const startPolling = (docId: string) => {
    if (pollTimers.current.has(docId)) return

    const timer = setInterval(async () => {
      try {
        const status = await getKbDocumentStatus(docId)
        setDocuments((prev) =>
          prev.map((d) =>
            d.docId === docId
              ? {
                  ...d,
                  status: status.status,
                  progress: status.progress,
                  chunkCount: status.chunkCount,
                  errorMessage: status.errorMessage,
                }
              : d,
          ),
        )
        if (status.status === 'ready' || status.status === 'failed') {
          clearInterval(timer)
          pollTimers.current.delete(docId)
          if (status.status === 'ready') {
            message.success(`文档 ${docId} 入库完成，共 ${status.chunkCount} 个分块`)
          } else {
            message.error(status.errorMessage || '文档处理失败')
          }
          void fetchList()
        }
      } catch {
        /* 轮询静默失败 */
      }
    }, 2000)

    pollTimers.current.set(docId, timer)
  }

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    accept: ACCEPT,
    showUploadList: false,
    beforeUpload: (file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
      if (!['pdf', 'txt', 'md', 'docx'].includes(ext)) {
        message.error('仅支持 PDF / TXT / MD / DOCX')
        return Upload.LIST_IGNORE
      }
      return true
    },
    customRequest: async ({ file, onSuccess, onError }) => {
      const uploadFile = file as File
      setUploading(true)
      try {
        const result = await uploadKbDocument(uploadFile, category, 'lingshan_scenic')
        message.success(`${uploadFile.name} 已提交处理`)
        startPolling(result.docId)
        await fetchList()
        onSuccess?.(result)
      } catch (e) {
        message.error(e instanceof Error ? e.message : '上传失败')
        onError?.(e as Error)
      } finally {
        setUploading(false)
      }
    },
  }

  const columns = [
    {
      title: '文档名称',
      dataIndex: 'filename',
      key: 'filename',
      render: (text: string, row: KbDocumentItem) => (
        <Space direction="vertical" size={0}>
          <span>{text}</span>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {row.docId}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const cfg = STATUS_MAP[status] ?? { color: 'default', label: status }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 160,
      render: (progress: number, row: KbDocumentItem) => (
        <Progress
          percent={progress}
          size="small"
          status={row.status === 'failed' ? 'exception' : row.status === 'ready' ? 'success' : 'active'}
        />
      ),
    },
    {
      title: '分块数',
      dataIndex: 'chunkCount',
      key: 'chunkCount',
      width: 80,
    },
    {
      title: '上传时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      render: (v: string) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '错误',
      dataIndex: 'errorMessage',
      key: 'errorMessage',
      ellipsis: true,
      render: (v: string | null) =>
        v ? <Typography.Text type="danger">{v}</Typography.Text> : '-',
    },
  ]

  return (
    <div>
      <Title level={3} style={{ marginTop: 0, color: '#115e59' }}>
        知识库管理
      </Title>
      <Paragraph type="secondary">
        上传景区讲解资料，系统将自动解析、分块并写入 Chroma 向量库，供 AI 数字人问答检索。
      </Paragraph>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="认证说明"
        description="默认使用硬编码 Token（scenic-admin-token-2026），也可通过 POST /api/v1/admin/auth/login 获取 JWT。"
      />

      <Card title="上传文档" style={{ marginBottom: 24 }}>
        <Form layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item label="文档分类">
            <Select
              value={category}
              onChange={setCategory}
              style={{ width: 160 }}
              options={[
                { value: 'history', label: '历史文化' },
                { value: 'culture', label: '人文艺术' },
                { value: 'faq', label: '常见问题' },
                { value: 'guide', label: '游览指南' },
                { value: 'other', label: '其他' },
              ]}
            />
          </Form.Item>
        </Form>

        <Dragger {...uploadProps} disabled={uploading}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ color: '#14b8a6', fontSize: 48 }} />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">支持 PDF、TXT、Markdown、Word（.docx），单文件最大 20MB</p>
        </Dragger>
      </Card>

      <Card
        title="最近上传"
        extra={
          <a onClick={() => void fetchList()}>
            <ReloadOutlined /> 刷新
          </a>
        }
      >
        <Table
          rowKey="docId"
          columns={columns}
          dataSource={documents}
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  )
}
