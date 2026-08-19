import { useCallback, useEffect, useRef, useState } from 'react'
import { Card, Col, Row, Spin, Statistic, Typography } from 'antd'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { getDashboardOverview, DashboardOverviewData } from '../services/api'

const { Title, Text } = Typography

/** 大屏设计基准 1920×1080 */
const SCREEN_STYLE: React.CSSProperties = {
  width: '100%',
  minHeight: 'calc(100vh - 48px)',
  background: 'linear-gradient(135deg, #0f172a 0%, #134e4a 50%, #0f766e 100%)',
  padding: 24,
  boxSizing: 'border-box',
  borderRadius: 12,
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardOverviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const timerRef = useRef<ReturnType<typeof setInterval>>()

  const fetchData = useCallback(async () => {
    try {
      const overview = await getDashboardOverview()
      setData(overview)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchData()
    timerRef.current = setInterval(() => void fetchData(), 30000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [fetchData])

  const hotBarOption: EChartsOption = {
    backgroundColor: 'transparent',
    title: {
      text: '热门问答 TOP5',
      left: 'center',
      textStyle: { color: '#ecfdf5', fontSize: 18 },
    },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, bottom: 60, top: 50 },
    xAxis: {
      type: 'category',
      data: data?.hotQA.map((q) => q.question) ?? [],
      axisLabel: {
        color: '#99f6e4',
        interval: 0,
        rotate: 20,
        formatter: (v: string) => (v.length > 12 ? `${v.slice(0, 12)}…` : v),
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#99f6e4' },
      splitLine: { lineStyle: { color: 'rgba(153,246,228,0.15)' } },
    },
    series: [
      {
        type: 'bar',
        data: data?.hotQA.map((q) => q.count) ?? [],
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#2dd4bf' },
              { offset: 1, color: '#0d9488' },
            ],
          },
          borderRadius: [6, 6, 0, 0],
        },
        barMaxWidth: 48,
      },
    ],
  }

  const satisfactionLineOption: EChartsOption = {
    backgroundColor: 'transparent',
    title: {
      text: '近7日满意度趋势',
      left: 'center',
      textStyle: { color: '#ecfdf5', fontSize: 18 },
    },
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 30, bottom: 40, top: 50 },
    xAxis: {
      type: 'category',
      data: data?.satisfactionTrend.map((d) => d.date.slice(5)) ?? [],
      axisLabel: { color: '#99f6e4' },
    },
    yAxis: {
      type: 'value',
      min: 3,
      max: 5,
      axisLabel: { color: '#99f6e4' },
      splitLine: { lineStyle: { color: 'rgba(153,246,228,0.15)' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: data?.satisfactionTrend.map((d) => d.avgSatisfaction) ?? [],
        lineStyle: { color: '#fbbf24', width: 3 },
        itemStyle: { color: '#fbbf24' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(251,191,36,0.35)' },
              { offset: 1, color: 'rgba(251,191,36,0)' },
            ],
          },
        },
      },
    ],
  }

  return (
    <div style={SCREEN_STYLE}>
      <div style={{ maxWidth: 1920, margin: '0 auto' }}>
        <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
          <Col>
            <Title level={2} style={{ color: '#ecfdf5', margin: 0 }}>
              景区导览 · 数据大屏
            </Title>
            <Text style={{ color: '#99f6e4' }}>1920×1080 运营数据概览 · 30 秒自动刷新</Text>
          </Col>
        </Row>

        <Spin spinning={loading}>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={8}>
              <Card
                bordered={false}
                style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 12 }}
              >
                <Statistic
                  title={<span style={{ color: '#99f6e4' }}>今日服务人次</span>}
                  value={data?.sessionCount ?? 0}
                  suffix="次"
                  valueStyle={{ color: '#2dd4bf', fontSize: 36 }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card
                bordered={false}
                style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 12 }}
              >
                <Statistic
                  title={<span style={{ color: '#99f6e4' }}>今日问答次数</span>}
                  value={data?.messageCount ?? 0}
                  suffix="条"
                  valueStyle={{ color: '#34d399', fontSize: 36 }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card
                bordered={false}
                style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 12 }}
              >
                <Statistic
                  title={<span style={{ color: '#99f6e4' }}>近7日平均满意度</span>}
                  value={data?.avgSatisfaction ?? 0}
                  precision={2}
                  suffix="/ 5"
                  valueStyle={{ color: '#fbbf24', fontSize: 36 }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card
                bordered={false}
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  borderRadius: 12,
                  height: 420,
                }}
                bodyStyle={{ height: '100%', padding: 12 }}
              >
                <ReactECharts
                  option={hotBarOption}
                  style={{ height: 380, width: '100%' }}
                  notMerge
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card
                bordered={false}
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  borderRadius: 12,
                  height: 420,
                }}
                bodyStyle={{ height: '100%', padding: 12 }}
              >
                <ReactECharts
                  option={satisfactionLineOption}
                  style={{ height: 380, width: '100%' }}
                  notMerge
                />
              </Card>
            </Col>
          </Row>
        </Spin>
      </div>
    </div>
  )
}
