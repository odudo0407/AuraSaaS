<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-semibold text-ink mb-1">数据报表</h2>
        <p class="text-muted text-sm">多维度数据分析，洞察经营趋势</p>
      </div>
      <div class="flex gap-2 items-center">
        <StoreSelector @change="onStoreChange" />
        <select v-model="timeRange" @change="onTimeRangeChange" class="bg-canvas border border-hairline rounded-lg px-3 py-2 text-sm text-ink outline-none">
          <option v-for="opt in timeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <button @click="exportExcel"
          class="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-active transition-colors">
          导出 Excel
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-3 mb-6">
      <div v-for="tab in tabs" :key="tab.key"
        class="flex items-center justify-center px-5 py-2 rounded-lg border cursor-pointer transition-colors text-sm font-medium"
        :class="activeTab === tab.key ? 'border-ink text-ink' : 'border-hairline text-muted hover:text-ink hover:border-ink'"
        @click="activeTab = tab.key">
        {{ tab.label }}
      </div>
    </div>

    <!-- Revenue Analysis -->
    <div v-show="activeTab === 'revenue'" class="grid grid-cols-2 gap-6">
      <div class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-sm font-semibold text-ink mb-4">日营收趋势</div>
        <div ref="revenueChart" class="w-full h-56"></div>
      </div>
      <div class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-sm font-semibold text-ink mb-4">品类营收占比</div>
        <div ref="categoryChart" class="w-full h-56"></div>
      </div>
      <div class="bg-canvas border border-hairline rounded-xl p-5 col-span-2">
        <div class="text-sm font-semibold text-ink mb-4">时段热力分析</div>
        <div class="grid grid-cols-7 gap-1">
          <div v-for="(day, di) in weekDays" :key="di" class="text-center">
            <div class="text-xs text-muted mb-2">{{ day }}</div>
            <div v-for="(hour, hi) in hours" :key="hi"
              class="h-5 rounded-sm mb-0.5"
              :style="{ background: getHeatColor(di, hi), opacity: 0.3 + getHeatValue(di, hi) * 0.7 }">
            </div>
          </div>
        </div>
        <div class="flex justify-between mt-2">
          <span class="text-xs text-muted-soft">06:00</span>
          <span class="text-xs text-muted-soft">12:00</span>
          <span class="text-xs text-muted-soft">18:00</span>
          <span class="text-xs text-muted-soft">22:00</span>
        </div>
      </div>
    </div>

    <!-- SKU Analysis -->
    <div v-show="activeTab === 'sku'" class="bg-canvas border border-hairline rounded-xl p-5">
      <div class="text-sm font-semibold text-ink mb-4">SKU 表现分析</div>
      <table class="w-full">
        <thead><tr class="border-b border-hairline-soft">
          <th v-for="h in ['商品名称','品类','日均销量','营收','毛利率','趋势','状态']" :key="h"
            class="text-left text-muted text-xs font-medium py-2.5 px-2">{{ h }}</th>
        </tr></thead>
        <tbody>
          <tr v-for="sku in skuData" :key="sku.name" class="border-b border-hairline-soft/50">
            <td class="py-3 px-2 text-sm font-medium text-ink">{{ sku.name }}</td>
            <td class="py-3 px-2"><span class="text-xs px-2 py-0.5 rounded-full bg-surface-soft text-muted">{{ sku.category }}</span></td>
            <td class="py-3 px-2 text-sm text-body">{{ sku.avgSales }}</td>
            <td class="py-3 px-2 text-sm text-body">¥{{ sku.revenue }}</td>
            <td class="py-3 px-2 text-sm font-medium" :class="sku.margin >= 60 ? 'text-ink' : sku.margin >= 40 ? 'text-muted' : 'text-error-text'">{{ sku.margin }}%</td>
            <td class="py-3 px-2"><span class="text-sm" :class="sku.trend > 0 ? 'text-primary' : 'text-muted'">{{ sku.trend > 0 ? '↑' : '↓' }}{{ Math.abs(sku.trend) }}%</span></td>
            <td class="py-3 px-2"><span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="sku.status === 'good' ? 'bg-primary/8 text-primary' : 'bg-error-text/8 text-error-text'">{{ sku.status === 'good' ? '正常' : '预警' }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Channel Analysis -->
    <div v-show="activeTab === 'channel'" class="grid grid-cols-3 gap-6">
      <div v-for="ch in channels" :key="ch.name"
        class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="flex items-center gap-3 mb-4">
          <span class="w-10 h-10 rounded-xl bg-surface-soft flex items-center justify-center text-lg">{{ ch.icon }}</span>
          <div>
            <div class="text-sm font-semibold text-ink">{{ ch.name }}</div>
            <div class="text-xs text-muted-soft">{{ ch.desc }}</div>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div><div class="text-lg font-bold text-ink">{{ ch.orders }}</div><div class="text-xs text-muted-soft">订单数</div></div>
          <div><div class="text-lg font-bold text-ink">¥{{ ch.revenue }}</div><div class="text-xs text-muted-soft">营收</div></div>
        </div>
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted-soft">占比</span>
          <div class="flex-1 mx-3 h-1.5 bg-surface-soft rounded-full overflow-hidden">
            <div class="h-full bg-primary rounded-full" :style="{ width: ch.pct + '%' }"></div>
          </div>
          <span class="text-ink font-medium">{{ ch.pct }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { request as apiRequest } from '../utils/request'
import StoreSelector from '../components/StoreSelector.vue'

const activeTab = ref('revenue')
const currentStoreId = ref(null)
const timeRange = ref(30)
const timeOptions = [
  { value: 7, label: '最近7天' },
  { value: 30, label: '最近30天' },
  { value: 90, label: '最近90天' },
]

async function exportExcel() {
  try {
    const res = await fetch('/api/dashboard/export?format=xlsx&days=30')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'report_' + new Date().toISOString().slice(0, 10) + '.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch { /* ignore */ }
}

const revenueChart = ref(null)
const categoryChart = ref(null)

const tabs = [
  { key: 'revenue', label: '营收分析' },
  { key: 'sku', label: '商品分析' },
  { key: 'channel', label: '渠道分析' },
]

// --- Heatmap ---
const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const hours = Array.from({ length: 17 }, (_, i) => i + 6)

function buildFallbackHeatmap() {
  const map = {}
  for (let d = 0; d < 7; d++) {
    const dowBase = d >= 5 ? 0.6 : 0.3
    for (let h = 6; h <= 22; h++) {
      const hourBase = h >= 6 && h <= 9 ? 0.3 : h >= 11 && h <= 13 ? 0.45 : h >= 17 && h <= 20 ? 0.38 : 0.12
      const seed = ((d * 31 + h * 17) % 100) / 100
      map[d + '-' + h] = (dowBase + hourBase + seed * 0.15) * 100
    }
  }
  return { map, max: 100 }
}

const heatmapData = ref(buildFallbackHeatmap())

async function fetchHeatmap() {
  try {
    const params = ['days=' + timeRange.value]
    if (currentStoreId.value) params.push('store_id=' + currentStoreId.value)
    const res = await apiRequest('/api/dashboard/traffic-heatmap?' + params.join('&'))
    const data = res.data || []
    if (data.length > 0) {
      const map = {}
      let maxOrders = 1
      data.forEach(function (d) {
        var key = d.day_of_week + '-' + d.hour
        map[key] = (map[key] || 0) + d.orders
        if (map[key] > maxOrders) maxOrders = map[key]
      })
      heatmapData.value = { map: map, max: maxOrders }
      return
    }
  } catch { /* use fallback */ }
  heatmapData.value = buildFallbackHeatmap()
}

function getHeatValue(d, h) {
  var m = heatmapData.value
  var val = m.map[d + '-' + h]
  return val != null && m.max > 0 ? val / m.max : 0.3
}
function getHeatColor(d, h) {
  var v = getHeatValue(d, h)
  return v > 0.7 ? '#ff385c' : v > 0.5 ? '#ff6b81' : v > 0.3 ? '#ffa0ad' : '#ffd1da'
}

// --- SKU table (static fallback) ---
const skuData = [
  { name: '招牌烤鸭', category: '热菜', avgSales: 35, revenue: '31,360', margin: 64.8, trend: 5.2, status: 'good' },
  { name: '冰美式', category: '饮品', avgSales: 48, revenue: '5,292', margin: 78.6, trend: -60, status: 'warning' },
  { name: '麻辣香锅', category: '热菜', avgSales: 52, revenue: '15,488', margin: 65.9, trend: 3.1, status: 'good' },
  { name: '杨枝甘露', category: '饮品', avgSales: 80, revenue: '4,970', margin: 71.4, trend: -8.5, status: 'good' },
  { name: '蛋黄酥', category: '甜品', avgSales: 70, revenue: '2,304', margin: 72.2, trend: 12.3, status: 'good' },
  { name: '生椰拿铁', category: '饮品', avgSales: 57, revenue: '3,648', margin: 75.0, trend: -40, status: 'warning' },
  { name: '酸菜鱼', category: '热菜', avgSales: 45, revenue: '12,600', margin: 64.1, trend: 2.8, status: 'good' },
  { name: '小笼包', category: '主食', avgSales: 65, revenue: '5,070', margin: 73.1, trend: 1.5, status: 'good' },
]

const channels = [
  { name: '堂食', icon: '🍽', desc: '到店消费', orders: '8,234', revenue: '245,600', pct: 52 },
  { name: '外卖平台', icon: '🛵', desc: '美团/饿了么', orders: '3,456', revenue: '128,400', pct: 27 },
  { name: '小程序自营', icon: '📱', desc: '私域流量', orders: '1,157', revenue: '54,450', pct: 12 },
  { name: '企业团购', icon: '🏢', desc: 'B端客户', orders: '234', revenue: '32,100', pct: 7 },
  { name: '其他', icon: '📦', desc: '其他渠道', orders: '123', revenue: '8,900', pct: 2 },
]

// --- ECharts ---
let revenueChartInstance = null
let categoryChartInstance = null

function initChart(refEl, existing) {
  if (existing && !existing.isDisposed()) existing.dispose()
  if (!refEl) return null
  var inst = echarts.init(refEl)
  new ResizeObserver(function () {
    if (inst && !inst.isDisposed()) inst.resize()
  }).observe(refEl)
  return inst
}

async function renderCharts() {
  await nextTick()

  revenueChartInstance = initChart(revenueChart.value, revenueChartInstance)
  if (revenueChartInstance) {
    try {
      var params = ['days=' + timeRange.value]
      if (currentStoreId.value) params.push('store_id=' + currentStoreId.value)
      var res = await apiRequest('/api/dashboard/trends?' + params.join('&'))
      var dates = (res.data?.dates || []).map(function (d) { return d.slice(5) })
      var revenue = res.data?.revenue || []
      revenueChartInstance.setOption({
        grid: { top: 10, right: 10, bottom: 24, left: 50 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: dates.length ? dates : Array.from({ length: timeRange.value }, function (_, i) { return String(i + 1) }), axisLabel: { color: '#929292', fontSize: 11 } },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: '#ebebeb' } }, axisLabel: { color: '#929292', fontSize: 11, formatter: function (v) { return '¥' + (v / 1000).toFixed(0) + 'k' } } },
        series: [{ type: 'line', data: revenue.length ? revenue : Array.from({ length: timeRange.value }, function (_, i) { return 18000 + Math.sin(i / 2) * 2800 + i * 170 }), smooth: true, symbol: 'none', lineStyle: { color: '#ff385c', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(255,56,92,0.1)' }, { offset: 1, color: 'rgba(255,56,92,0)' }]) } }]
      }, { notMerge: true })
    } catch {
      revenueChartInstance.setOption({
        grid: { top: 10, right: 10, bottom: 24, left: 50 }, tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: Array.from({ length: timeRange.value }, function (_, i) { return String(i + 1) }), axisLabel: { color: '#929292', fontSize: 11 } },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: '#ebebeb' } }, axisLabel: { color: '#929292', fontSize: 11, formatter: function (v) { return '¥' + (v / 1000).toFixed(0) + 'k' } } },
        series: [{ type: 'line', data: Array.from({ length: timeRange.value }, function (_, i) { return 28000 + i * 500 + Math.sin(i / 3) * 2000 }), smooth: true, symbol: 'none', lineStyle: { color: '#ff385c', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(255,56,92,0.1)' }, { offset: 1, color: 'rgba(255,56,92,0)' }]) } }]
      }, { notMerge: true })
    }
  }

  categoryChartInstance = initChart(categoryChart.value, categoryChartInstance)
  if (categoryChartInstance) {
    try {
      var skuParams = ['limit=20']
      if (currentStoreId.value) skuParams.push('store_id=' + currentStoreId.value)
      var skuRes = await apiRequest('/api/dashboard/top-skus?' + skuParams.join('&'))
      var skuRows = skuRes.data || []
      var catMap = {}
      skuRows.forEach(function (s) { catMap[s.category] = (catMap[s.category] || 0) + s.total_sales })
      var colors = ['#ff385c', '#ff6b81', '#ffa0ad', '#ffd1da', '#ebebeb', '#c1c1c1']
      var pieData = Object.entries(catMap).map(function (entry, i) { return { value: entry[1], name: entry[0], itemStyle: { color: colors[i % colors.length] } } })
      categoryChartInstance.setOption({
        tooltip: { trigger: 'item' },
        series: [{ type: 'pie', radius: ['45%', '75%'], center: ['50%', '50%'], label: { show: true, color: '#6a6a6a', fontSize: 12 },
          data: pieData.length ? pieData : [{ value: 1, name: '暂无数据', itemStyle: { color: '#ebebeb' } }]
        }]
      }, { notMerge: true })
    } catch {
      categoryChartInstance.setOption({
        tooltip: { trigger: 'item' },
        series: [{ type: 'pie', radius: ['45%', '75%'], center: ['50%', '50%'], label: { show: true, color: '#6a6a6a', fontSize: 12 },
          data: [
            { value: 45, name: '热菜', itemStyle: { color: '#ff385c' } },
            { value: 25, name: '饮品', itemStyle: { color: '#ff6b81' } },
            { value: 15, name: '甜品', itemStyle: { color: '#ffa0ad' } },
            { value: 10, name: '主食', itemStyle: { color: '#ffd1da' } },
            { value: 5, name: '凉菜', itemStyle: { color: '#ebebeb' } },
          ]
        }]
      }, { notMerge: true })
    }
  }
}

watch(activeTab, async function (tab) {
  if (tab === 'revenue') {
    await nextTick()
    if (revenueChartInstance && !revenueChartInstance.isDisposed()) revenueChartInstance.resize()
    if (categoryChartInstance && !categoryChartInstance.isDisposed()) categoryChartInstance.resize()
  }
})

function onStoreChange(storeId) {
  currentStoreId.value = storeId
  fetchHeatmap()
  renderCharts()
}

function onTimeRangeChange() {
  fetchHeatmap()
  renderCharts()
}

onMounted(function () {
  renderCharts()
  fetchHeatmap()
})

onUnmounted(function () {
  if (revenueChartInstance && !revenueChartInstance.isDisposed()) revenueChartInstance.dispose()
  if (categoryChartInstance && !categoryChartInstance.isDisposed()) categoryChartInstance.dispose()
  revenueChartInstance = null
  categoryChartInstance = null
})
</script>
