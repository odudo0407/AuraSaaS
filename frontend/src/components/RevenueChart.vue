<template>
  <div ref="chartRef" class="w-full h-200px"></div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({ data: Object })
const chartRef = ref(null)
let chart = null

function renderChart() {
  if (!chartRef.value || !props.data?.dates?.length) return
  if (!chart) chart = echarts.init(chartRef.value, null, { renderer: 'canvas' })

  chart.setOption({
    backgroundColor: 'transparent',
    grid: { top: 20, right: 20, bottom: 30, left: 60 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#dddddd',
      textStyle: { color: '#222222', fontSize: 13 },
      formatter: (params) => {
        const p = params[0]
        return `<div style="font-size:12px;color:#6a6a6a">${p.name}</div>
                <div style="font-size:18px;color:#ff385c;font-weight:700">¥${p.value.toLocaleString()}</div>`
      },
    },
    xAxis: {
      type: 'category',
      data: props.data.dates.map(d => d.slice(5)),
      axisLine: { lineStyle: { color: '#dddddd' } },
      axisTick: { show: false },
      axisLabel: { color: '#929292', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#ebebeb' } },
      axisLabel: {
        color: '#929292',
        fontSize: 12,
        formatter: (v) => `¥${(v / 1000).toFixed(0)}k`,
      },
    },
    series: [{
      type: 'line',
      data: props.data.revenue,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#ff385c', width: 2.5 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(255,56,92,0.12)' },
          { offset: 1, color: 'rgba(255,56,92,0)' },
        ]),
      },
    }],
  })
}

watch(() => props.data, renderChart, { deep: true })
onMounted(renderChart)
onUnmounted(() => chart?.dispose())

let resizeObserver
onMounted(() => {
  resizeObserver = new ResizeObserver(() => chart?.resize())
  if (chartRef.value) resizeObserver.observe(chartRef.value)
})
onUnmounted(() => resizeObserver?.disconnect())
</script>
