<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-semibold text-ink mb-1">财务中心</h2>
        <p class="text-muted text-sm">收入支出一目了然，智能成本分析</p>
      </div>
      <div class="flex gap-2 items-center">
        <StoreSelector @change="onStoreChange" />
        <select class="bg-canvas border border-hairline rounded-lg px-3 py-2 text-sm text-ink outline-none">
          <option>2026年5月</option><option>2026年4月</option><option>2026年3月</option>
        </select>
        <button @click="exportReport"
          class="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-active transition-colors">
          导出财报
        </button>
      </div>
    </div>

    <!-- P&L Summary -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-muted text-xs font-medium mb-1">总营收</div>
        <div class="text-ink font-bold mb-1" style="font-size: 24px">¥{{ financeData ? financeData.total_revenue?.toLocaleString() : '328,450' }}</div>
        <span class="text-xs font-medium" :class="(financeData?.revenue_growth || 12.5) >= 0 ? 'text-primary' : 'text-muted'">
          {{ (financeData?.revenue_growth || 12.5) >= 0 ? '↑' : '↓' }} {{ Math.abs(financeData?.revenue_growth || 12.5) }}% 较上月
        </span>
      </div>
      <div class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-muted text-xs font-medium mb-1">总支出</div>
        <div class="text-ink font-bold mb-1" style="font-size: 24px">¥{{ financeData ? financeData.total_expense?.toLocaleString() : '283,220' }}</div>
        <span class="text-xs text-muted font-medium">—</span>
      </div>
      <div class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-muted text-xs font-medium mb-1">净利润</div>
        <div class="text-primary font-bold mb-1" style="font-size: 24px">¥{{ financeData ? financeData.net_profit?.toLocaleString() : '45,230' }}</div>
        <span class="text-xs font-medium" :class="(financeData?.profit_growth || 15.7) >= 0 ? 'text-primary' : 'text-muted'">
          {{ (financeData?.profit_growth || 15.7) >= 0 ? '↑' : '↓' }} {{ Math.abs(financeData?.profit_growth || 15.7) }}% 较上月
        </span>
      </div>
    </div>

    <!-- Cost breakdown + Trend -->
    <div class="grid grid-cols-2 gap-6 mb-6">
      <div class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-sm font-semibold text-ink mb-4">成本结构分析</div>
        <div v-for="(cost, i) in displayCostBreakdown" :key="i"
          class="flex items-center justify-between py-3"
          :class="i < displayCostBreakdown.length - 1 ? 'border-b border-hairline-soft' : ''">
          <div class="flex items-center gap-3">
            <span class="w-8 h-8 rounded-lg bg-surface-soft flex items-center justify-center text-sm">{{ cost.icon }}</span>
            <div>
              <div class="text-sm font-medium text-ink">{{ cost.name }}</div>
              <div class="text-xs text-muted-soft">{{ cost.desc }}</div>
            </div>
          </div>
          <div class="text-right">
            <div class="text-sm font-semibold text-ink">¥{{ cost.amount }}</div>
            <div class="text-xs text-muted-soft">{{ cost.pct }}%</div>
          </div>
        </div>
      </div>

      <div class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-sm font-semibold text-ink mb-4">月度利润趋势</div>
        <div ref="profitChart" class="w-full h-64"></div>
      </div>
    </div>

    <!-- Transaction records -->
    <div class="bg-canvas border border-hairline rounded-xl p-5">
      <div class="flex justify-between items-center mb-4">
        <span class="text-sm font-semibold text-ink">近期交易记录</span>
        <span @click="router.push('/app/reports')" class="text-primary text-xs font-medium cursor-pointer">查看全部 →</span>
      </div>
      <table class="w-full">
        <thead><tr class="border-b border-hairline-soft">
          <th v-for="h in ['时间','类型','描述','金额','状态']" :key="h"
            class="text-left text-muted text-xs font-medium py-2.5 px-2">{{ h }}</th>
        </tr></thead>
        <tbody>
          <tr v-for="tx in displayTransactions" :key="tx.id" class="border-b border-hairline-soft/50">
            <td class="py-3 px-2 text-sm text-muted">{{ tx.time }}</td>
            <td class="py-3 px-2"><span class="text-xs px-2 py-0.5 rounded-full" :class="tx.type === '收入' ? 'bg-primary/8 text-primary' : 'bg-surface-soft text-muted'">{{ tx.type }}</span></td>
            <td class="py-3 px-2 text-sm text-ink">{{ tx.desc }}</td>
            <td class="py-3 px-2 text-sm font-medium" :class="tx.amount > 0 ? 'text-primary' : 'text-ink'">{{ tx.amount > 0 ? '+' : '' }}¥{{ Math.abs(tx.amount).toLocaleString() }}</td>
            <td class="py-3 px-2"><span class="text-xs px-2 py-0.5 rounded-full bg-primary/8 text-primary font-medium">已完成</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="exportMsg" class="fixed bottom-8 left-1/2 -translate-x-1/2 bg-ink text-white px-6 py-3 rounded-xl text-sm font-medium shadow-lg z-50">
      {{ exportMsg }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { request } from '../utils/request'
import StoreSelector from '../components/StoreSelector.vue'

const router = useRouter()
const profitChart = ref(null)
let profitChartInstance = null
const exportMsg = ref('')
const financeData = ref(null)
const transactions = ref([])
const currentStoreId = ref(null)

function onStoreChange(storeId) {
  currentStoreId.value = storeId
  fetchFinance()
  fetchTransactions()
  renderChart()
}

async function fetchFinance() {
  try {
    const qs = currentStoreId.value ? `?store_id=${currentStoreId.value}` : ''
    const res = await request(`/api/finance/overview${qs}`)
    financeData.value = res.data
  } catch { /* API failed, keep existing data */ }
}

async function fetchTransactions() {
  try {
    const qs = currentStoreId.value ? `?store_id=${currentStoreId.value}` : ''
    const res = await request(`/api/finance/transactions${qs}`)
    const data = (res.data || []).map((t, i) => ({ id: i + 1, ...t }))
    transactions.value = data.length > 0 ? data : []
  } catch { /* API failed, keep existing data */ }
}

async function exportReport() {
  try {
    const res = await fetch('/api/dashboard/export?format=csv&days=30')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `finance_${new Date().toISOString().slice(0,10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    exportMsg.value = '导出成功'
  } catch (e) {
    exportMsg.value = '导出失败: ' + e.message
  }
  setTimeout(() => { exportMsg.value = '' }, 3000)
}

const costIcons = { '食材采购': '🥘', '人工成本': '👥', '房租水电': '🏠', '平台抽佣': '🛵', '其他支出': '🔧', '营销推广': '📢' }
const costDescs = { '食材采购': '原材料及半成品', '人工成本': '员工薪资社保', '房租水电': '门店租金及水电', '平台抽佣': '外卖平台服务费', '其他支出': '设备维护及杂项', '营销推广': '广告投放及活动' }

const costBreakdown = [
  { icon: '🥘', name: '食材采购', desc: '原材料及半成品', amount: '112,400', pct: 40 },
  { icon: '👥', name: '人工成本', desc: '员工薪资社保', amount: '75,600', pct: 27 },
  { icon: '🏠', name: '房租水电', desc: '门店租金及水电', amount: '42,300', pct: 15 },
  { icon: '🛵', name: '平台抽佣', desc: '外卖平台服务费', amount: '28,500', pct: 10 },
  { icon: '📢', name: '营销推广', desc: '广告投放及活动', amount: '12,800', pct: 4.5 },
  { icon: '🔧', name: '其他支出', desc: '设备维护及杂项', amount: '11,620', pct: 3.5 },
]

const displayCostBreakdown = computed(() => {
  if (financeData.value?.cost_breakdown) {
    return financeData.value.cost_breakdown.map(c => ({
      icon: costIcons[c.name] || '📦',
      name: c.name,
      desc: costDescs[c.name] || '',
      amount: c.amount?.toLocaleString() || '0',
      pct: c.pct || 0,
    }))
  }
  return costBreakdown
})


const displayTransactions = computed(() => {
  return transactions.value.length > 0 ? transactions.value : transactions_default
})

const transactions_default = [
  { id: 1, time: '05-31 14:23', type: '收入', desc: '朝阳大悦城店 - 外卖结算', amount: 2340 },
  { id: 2, time: '05-31 12:15', type: '收入', desc: '三里屯店 - 堂食收入', amount: 5680 },
  { id: 3, time: '05-31 10:30', type: '支出', desc: '食材供应商 - 每周采购', amount: -18500 },
  { id: 4, time: '05-30 18:45', type: '收入', desc: '西单店 - 团购订单', amount: 3200 },
  { id: 5, time: '05-30 16:00', type: '支出', desc: '美团平台 - 月度结算', amount: -12800 },
  { id: 6, time: '05-30 09:00', type: '支出', desc: '员工工资 - 5月上半月', amount: -37800 },
]

async function renderChart() {
  if (!profitChart.value) return
  if (!profitChartInstance) {
    profitChartInstance = echarts.init(profitChart.value)
    new ResizeObserver(() => profitChartInstance?.resize()).observe(profitChart.value)
  }
  try {
    const params = ['days=90']
    if (currentStoreId.value) params.push(`store_id=${currentStoreId.value}`)
    const res = await request(`/api/dashboard/trends?${params.join('&')}`)
    const dates = res.data?.dates || []
    const revenue = res.data?.revenue || []
    const profit = res.data?.net_profit || []
    // Group by month
    const monthMap = {}
    dates.forEach((d, i) => {
      const m = d.slice(0, 7)
      if (!monthMap[m]) monthMap[m] = { revenue: 0, profit: 0 }
      monthMap[m].revenue += revenue[i] || 0
      monthMap[m].profit += profit[i] || 0
    })
    const months = Object.keys(monthMap).slice(-5)
    const revData = months.map(m => Math.round(monthMap[m].revenue))
    const profitData = months.map(m => Math.round(monthMap[m].profit))
    const labels = months.map(m => m.slice(5) + '月')

    profitChartInstance.setOption({
      backgroundColor: 'transparent',
      grid: { top: 10, right: 10, bottom: 24, left: 50 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: labels, axisLine:{lineStyle:{color:'#ddd'}}, axisTick:{show:false}, axisLabel:{color:'#929292',fontSize:11} },
      yAxis: { type:'value', splitLine:{lineStyle:{color:'#ebebeb'}}, axisLabel:{color:'#929292',fontSize:11,formatter:v=>`¥${(v/10000).toFixed(0)}万`} },
      series: [
        { name:'营收', type:'bar', data:revData, barWidth:20, itemStyle:{color:'#ffd1da'} },
        { name:'利润', type:'bar', data:profitData, barWidth:20, itemStyle:{color:'#ff385c'} },
      ]
    })
  } catch {
    profitChartInstance.setOption({
      backgroundColor: 'transparent',
      grid: { top: 10, right: 10, bottom: 24, left: 50 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['1月','2月','3月','4月','5月'], axisLine:{lineStyle:{color:'#ddd'}}, axisTick:{show:false}, axisLabel:{color:'#929292',fontSize:11} },
      yAxis: { type:'value', splitLine:{lineStyle:{color:'#ebebeb'}}, axisLabel:{color:'#929292',fontSize:11,formatter:v=>`¥${(v/10000).toFixed(0)}万`} },
      series: [
        { name:'营收', type:'bar', data:[280000,295000,310000,328000,328450], barWidth:20, itemStyle:{color:'#ffd1da'} },
        { name:'利润', type:'bar', data:[32000,35000,38000,42000,45230], barWidth:20, itemStyle:{color:'#ff385c'} },
      ]
    })
  }
}

onMounted(() => {
  fetchFinance()
  fetchTransactions()
  renderChart()
})
</script>
