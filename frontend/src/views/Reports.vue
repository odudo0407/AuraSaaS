<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-semibold text-ink mb-1">数据报表</h2>
        <p class="text-muted text-sm">多维度数据分析，洞察经营趋势</p>
      </div>
      <div class="flex gap-2 items-center">
        <StoreSelector @change="onStoreChange" />
        <select class="bg-canvas border border-hairline rounded-lg px-3 py-2 text-sm text-ink outline-none">
          <option>最近7天</option><option>最近30天</option><option>最近90天</option>
        </select>
        <button @click="exportExcel"
          class="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-active transition-colors">
          导出 Excel
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-6 border-b border-hairline mb-6">
      <span v-for="tab in tabs" :key="tab.key"
        class="pb-3 text-sm font-medium cursor-pointer transition-colors"
        :class="activeTab === tab.key ? 'text-ink border-b-2 border-ink' : 'text-muted hover:text-ink'"
        @click="activeTab = tab.key">
        {{ tab.label }}
      </span>
    </div>

    <!-- Revenue Analysis -->
    <div v-if="activeTab === 'revenue'" class="grid grid-cols-2 gap-6">
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
    <div v-if="activeTab === 'sku'" class="bg-canvas border border-hairline rounded-xl p-5">
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
    <div v-if="activeTab === 'channel'" class="grid grid-cols-3 gap-6">
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
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { request as apiRequest } from '../utils/request'
import StoreSelector from '../components/StoreSelector.vue'

const activeTab = ref('revenue')
const exportMsg = ref('')
const currentStoreId = ref(null)

async function exportExcel() {
  try {
    const res = await fetch('/api/dashboard/export?format=xlsx&days=30')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${new Date().toISOString().slice(0,10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    exportMsg.value = '导出成功'
  } catch (e) {
    exportMsg.value = '导出失败: ' + e.message
  }
  setTimeout(() => { exportMsg.value = '' }, 3000)
}
const revenueChart = ref(null)
const categoryChart = ref(null)

const tabs = [
  { key: 'revenue', label: '营收分析' },
  { key: 'sku', label: '商品分析' },
  { key: 'channel', label: '渠道分析' },
]

const weekDays = ['周一','周二','周三','周四','周五','周六','周日']
const hours = Array.from({ length: 17 }, (_, i) => i + 6)
const heatmapData = ref({})

async function fetchHeatmap() {
  try {
    const qs = currentStoreId.value ? `?store_id=${currentStoreId.value}` : ''
    const res = await apiRequest(`/api/dashboard/heatmap${qs}`)
    const data = res.data || []
    if (data.length > 0) {
      const map = {}
      let maxOrders = 1
      data.forEach(d => {
        const key = `${d.day_of_week}-${d.hour}`
        map[key] = d.orders
        if (d.orders > maxOrders) maxOrders = d.orders
      })
      heatmapData.value = { map, max: maxOrders }
    }
  } catch { /* keep default random values */ }
}

function getHeatValue(d, h) {
  const { map, max } = heatmapData.value
  if (!map || Object.keys(map).length === 0) {
    const base = (d >= 5 ? 0.6 : 0.3) + (h >= 6 && h <= 9 ? 0.3 : h >= 11 && h <= 13 ? 0.4 : h >= 17 && h <= 20 ? 0.35 : 0.1)
    return Math.min(1, base + Math.random() * 0.2)
  }
  const val = map[`${d}-${h}`] || 0
  return val / max
}
function getHeatColor(d, h) {
  const v = getHeatValue(d, h)
  return v > 0.7 ? '#ff385c' : v > 0.5 ? '#ff6b81' : v > 0.3 ? '#ffa0ad' : '#ffd1da'
}

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

let revenueChartInstance = null
let categoryChartInstance = null

async function renderCharts() {
  await nextTick()
  // Revenue trend chart
  if (revenueChart.value) {
    if (!revenueChartInstance) {
      revenueChartInstance = echarts.init(revenueChart.value)
      new ResizeObserver(() => revenueChartInstance?.resize()).observe(revenueChart.value)
    }
    try {
      const params = ['days=30']
      if (currentStoreId.value) params.push(`store_id=${currentStoreId.value}`)
      const res = await apiRequest(`/api/dashboard/trends?${params.join('&')}`)
      const dates = (res.data?.dates || []).map(d => d.slice(5))
      const revenue = res.data?.revenue || []
      revenueChartInstance.setOption({
        backgroundColor: 'transparent', grid: { top: 10, right: 10, bottom: 24, left: 50 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: dates.length ? dates : Array.from({length:30},(_,i)=>`${i+1}`), axisLine:{lineStyle:{color:'#ddd'}}, axisTick:{show:false}, axisLabel:{color:'#929292',fontSize:11} },
        yAxis: { type:'value', splitLine:{lineStyle:{color:'#ebebeb'}}, axisLabel:{color:'#929292',fontSize:11,formatter:v=>`¥${(v/1000).toFixed(0)}k`} },
        series: [{ type:'line', data:revenue, smooth:true, symbol:'none', lineStyle:{color:'#ff385c',width:2}, areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(255,56,92,0.1)'},{offset:1,color:'rgba(255,56,92,0)'}])} }]
      })
    } catch {
      revenueChartInstance.setOption({
        backgroundColor: 'transparent', grid: { top: 10, right: 10, bottom: 24, left: 50 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: Array.from({length:30},(_,i)=>`${i+1}`), axisLine:{lineStyle:{color:'#ddd'}}, axisTick:{show:false}, axisLabel:{color:'#929292',fontSize:11} },
        yAxis: { type:'value', splitLine:{lineStyle:{color:'#ebebeb'}}, axisLabel:{color:'#929292',fontSize:11,formatter:v=>`¥${(v/1000).toFixed(0)}k`} },
        series: [{ type:'line', data:[28000,31000,29500,33000,35000,32000,36000,34000,38000,37000,35500,39000,41000,38500,40000,42000,39500,37000,35000,38000,40000,41500,43000,42000,44000,41000,39000,42500,44500,43000], smooth:true, symbol:'none', lineStyle:{color:'#ff385c',width:2}, areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(255,56,92,0.1)'},{offset:1,color:'rgba(255,56,92,0)'}])} }]
      })
    }
  }

  // Category pie chart — from SKU data
  if (categoryChart.value) {
    if (!categoryChartInstance) {
      categoryChartInstance = echarts.init(categoryChart.value)
      new ResizeObserver(() => categoryChartInstance?.resize()).observe(categoryChart.value)
    }
    try {
      const params = ['limit=20']
      if (currentStoreId.value) params.push(`store_id=${currentStoreId.value}`)
      const res = await apiRequest(`/api/dashboard/top-skus?${params.join('&')}`)
      const skuData = res.data || []
      const catMap = {}
      skuData.forEach(s => {
        catMap[s.category] = (catMap[s.category] || 0) + s.total_sales
      })
      const colors = ['#ff385c', '#ff6b81', '#ffa0ad', '#ffd1da', '#ebebeb', '#c1c1c1']
      const pieData = Object.entries(catMap).map(([name, value], i) => ({
        value, name, itemStyle: { color: colors[i % colors.length] }
      }))
      categoryChartInstance.setOption({
        backgroundColor: 'transparent', tooltip: { trigger: 'item' },
        series: [{ type: 'pie', radius: ['45%','75%'], center: ['50%','50%'], label: { show: true, color: '#6a6a6a', fontSize: 12 },
          data: pieData.length ? pieData : [{ value: 1, name: '暂无数据', itemStyle: { color: '#ebebeb' } }]
        }]
      })
    } catch {
      categoryChartInstance.setOption({
        backgroundColor: 'transparent', tooltip: { trigger: 'item' },
        series: [{ type: 'pie', radius: ['45%','75%'], center: ['50%','50%'], label: { show: true, color: '#6a6a6a', fontSize: 12 },
          data: [
            { value: 45, name: '热菜', itemStyle: { color: '#ff385c' } },
            { value: 25, name: '饮品', itemStyle: { color: '#ff6b81' } },
            { value: 15, name: '甜品', itemStyle: { color: '#ffa0ad' } },
            { value: 10, name: '主食', itemStyle: { color: '#ffd1da' } },
            { value: 5, name: '凉菜', itemStyle: { color: '#ebebeb' } },
          ]
        }]
      })
    }
  }
}

function onStoreChange(storeId) {
  currentStoreId.value = storeId
  fetchHeatmap()
  renderCharts()
}

onMounted(() => {
  fetchHeatmap()
  renderCharts()
})
</script>
