import { useCallback, useEffect, useState } from 'react'
import { Card, Col, Row, Spin, Statistic, Typography } from 'antd'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import 'echarts-wordcloud'
import { getSentimentTrend, SentimentTrendData } from '../services/api'

const { Title, Text } = Typography

export default function SentimentAnalysis() {
  const [data, setData] = useState<SentimentTrendData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getSentimentTrend(7)
      setData(result)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  const pct = (v: number) => `${(v * 100).toFixed(1)}%`

  const stackedAreaOption: EChartsOption = {
    title: {
      text: '近7日情感比例趋势',
      left: 'center',
      textStyle: { fontSize: 16, color: '#134e4a' },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const items = params as { seriesName: string; value: number; axisValue: string }[]
        if (!items?.length) return ''
        const lines = items.map((p) => `${p.seriesName}: ${p.value}%`)
        return `${items[0].axisValue}<br/>${lines.join('<br/>')}`
      },
    },
    legend: {
      data: ['正面', '中性', '负面'],
      bottom: 0,
    },
    grid: { left: 50, right: 30, bottom: 50, top: 50 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data?.trend.map((d) => d.date.slice(5)) ?? [],
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%' },
    },
    color: ['#34d399', '#94a3b8', '#f87171'],
    series: [
      {
        name: '正面',
        type: 'line',
        stack: 'sentiment',
        smooth: true,
        areaStyle: { opacity: 0.75 },
        emphasis: { focus: 'series' },
        data: data?.trend.map((d) => +(d.positive * 100).toFixed(1)) ?? [],
      },
      {
        name: '中性',
        type: 'line',
        stack: 'sentiment',
        smooth: true,
        areaStyle: { opacity: 0.75 },
        emphasis: { focus: 'series' },
        data: data?.trend.map((d) => +(d.neutral * 100).toFixed(1)) ?? [],
      },
      {
        name: '负面',
        type: 'line',
        stack: 'sentiment',
        smooth: true,
        areaStyle: { opacity: 0.75 },
        emphasis: { focus: 'series' },
        data: data?.trend.map((d) => +(d.negative * 100).toFixed(1)) ?? [],
      },
    ],
  }

  const wordCloudOption: EChartsOption = {
    title: {
      text: '热点话题词云',
      left: 'center',
      textStyle: { fontSize: 16, color: '#134e4a' },
    },
    tooltip: {
      show: true,
      formatter: (p: { name?: string; value?: number }) =>
        `${p.name ?? ''}: 权重 ${p.value ?? 0}`,
    },
    series: [
      {
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        width: '95%',
        height: '85%',
        sizeRange: [14, 52],
        rotationRange: [-30, 30],
        gridSize: 8,
        drawOutOfBound: false,
        textStyle: {
          color: () => {
            const palette = ['#0d9488', '#14b8a6', '#2dd4bf', '#059669', '#047857', '#134e4a']
            return palette[Math.floor(Math.random() * palette.length)]
          },
        },
        emphasis: {
          textStyle: { shadowBlur: 8, shadowColor: 'rgba(13,148,136,0.4)' },
        },
        data:
          data?.hotTopics.map((t) => ({
            name: t.word,
            value: t.weight,
          })) ?? [],
      },
    ],
  }

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
        <Col>
          <Title level={3} style={{ margin: 0, color: '#134e4a' }}>
            感受度分析
          </Title>
          <Text type="secondary">基于会话日志的用户情感趋势与热点话题</Text>
        </Col>
      </Row>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={6}>
            <Card bordered={false}>
              <Statistic
                title="分析消息总数"
                value={data?.summary.totalMessages ?? 0}
                suffix="条"
                valueStyle={{ color: '#0d9488' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card bordered={false}>
              <Statistic
                title="正面占比"
                value={pct(data?.summary.positiveRate ?? 0)}
                valueStyle={{ color: '#34d399' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card bordered={false}>
              <Statistic
                title="中性占比"
                value={pct(data?.summary.neutralRate ?? 0)}
                valueStyle={{ color: '#64748b' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card bordered={false}>
              <Statistic
                title="负面占比"
                value={pct(data?.summary.negativeRate ?? 0)}
                valueStyle={{ color: '#f87171' }}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card bordered={false} style={{ height: 460 }} bodyStyle={{ height: '100%' }}>
              <ReactECharts
                option={stackedAreaOption}
                style={{ height: 420, width: '100%' }}
                notMerge
              />
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card bordered={false} style={{ height: 460 }} bodyStyle={{ height: '100%' }}>
              <ReactECharts
                option={wordCloudOption}
                style={{ height: 420, width: '100%' }}
                notMerge
              />
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  )
}
