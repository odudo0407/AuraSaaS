<template>
  <div class="min-h-full bg-[#f5f4f0] p-6">
    <section class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-sm font-bold text-primary">{{ copy.kicker }}</p>
        <h1 class="mt-2 text-3xl font-bold text-ink">{{ greeting }}, {{ auth.user?.username || 'operator' }}</h1>
        <p class="mt-2 max-w-760px text-sm leading-6 text-muted">
          {{ copy.subtitle }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <StoreSelector @change="onStoreChange" />
        <router-link
          to="/app/ai"
          class="flex h-10 items-center rounded-lg bg-ink px-4 text-sm font-bold text-white no-underline transition hover:bg-body"
        >
          {{ copy.askAgent }}
        </router-link>
      </div>
    </section>

    <section class="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <article v-for="stat in statCards" :key="stat.label" class="rounded-lg border border-hairline bg-white p-5">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold uppercase text-muted">{{ stat.label }}</span>
          <span class="rounded-md bg-[#f5f4f0] px-2 py-1 text-xs text-muted">{{ stat.unit }}</span>
        </div>
        <div class="mt-4 text-3xl font-bold text-ink">{{ stat.value }}</div>
        <div class="mt-3 flex items-center gap-2 text-xs">
          <span
            class="rounded-full px-2 py-1 font-bold"
            :class="stat.growth >= 0 ? 'bg-[#e8f7ef] text-[#237b4b]' : 'bg-primary/10 text-primary'"
          >
            {{ stat.growth >= 0 ? '+' : '-' }}{{ Math.abs(stat.growth) }}%
          </span>
          <span class="text-muted">{{ copy.monthOverMonth }}</span>
        </div>
      </article>
    </section>

    <section class="mb-6 grid gap-4 xl:grid-cols-[1.45fr_0.9fr]">
      <article class="rounded-lg border border-hairline bg-white p-5">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-bold text-ink">{{ copy.revenueTrend }}</h2>
            <p class="mt-1 text-xs text-muted">{{ copy.revenueTrendDesc }}</p>
          </div>
          <div class="flex rounded-lg border border-hairline bg-[#f5f4f0] p-1">
            <button
              v-for="range in ranges"
              :key="range.label"
              @click="setRange(range)"
              class="h-8 rounded-md px-3 text-xs font-bold transition"
              :class="activeRange === range.label ? 'bg-ink text-white' : 'text-muted hover:text-ink'"
            >
              {{ range.label }}
            </button>
          </div>
        </div>
        <div ref="chartRef" class="h-280px w-full"></div>
      </article>

      <article class="rounded-lg border border-hairline bg-[#10151f] p-5 text-white">
        <div class="mb-5 flex items-start justify-between">
          <div>
            <h2 class="text-base font-bold">{{ copy.agentReadiness }}</h2>
            <p class="mt-1 text-xs leading-5 text-white/55">{{ copy.agentReadinessDesc }}</p>
          </div>
          <span class="rounded-full bg-[#37d67a]/15 px-3 py-1 text-xs font-bold text-[#37d67a]">{{ copy.online }}</span>
        </div>
        <div class="space-y-3">
          <div v-for="item in readiness" :key="item.label" class="rounded-lg border border-white/10 bg-white/5 p-3">
            <div class="flex items-center justify-between gap-3">
              <span class="text-sm font-bold">{{ item.label }}</span>
              <span class="text-xs text-white/55">{{ item.value }}</span>
            </div>
            <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div class="h-full rounded-full bg-[#37d67a]" :style="{ width: `${item.score}%` }"></div>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="mb-6 rounded-lg border border-hairline bg-white p-5">
      <div class="mb-4 flex items-center justify-between">
        <div>
          <h2 class="text-base font-bold text-ink">{{ copy.recentRuns }}</h2>
          <p class="mt-1 text-xs text-muted">{{ copy.recentRunsDesc }}</p>
        </div>
        <router-link to="/app/ai" class="text-xs font-bold text-primary no-underline">{{ copy.openAnalysis }}</router-link>
      </div>
      <div v-if="recentTraces.length === 0" class="rounded-lg border border-dashed border-hairline p-4 text-sm text-muted">
        {{ copy.noRuns }}
      </div>
      <div v-else class="grid gap-3 md:grid-cols-3">
        <router-link
          v-for="trace in recentTraces"
          :key="trace.trace_id"
          to="/app/ai"
          class="rounded-lg border border-hairline bg-[#fbfaf8] p-4 text-ink no-underline transition hover:border-ink"
        >
          <div class="truncate text-sm font-bold">{{ trace.user_query }}</div>
          <div class="mt-3 flex items-center justify-between text-xs text-muted">
            <span>{{ trace.status }}</span>
            <span>{{ trace.step_count }} {{ copy.steps }}</span>
          </div>
        </router-link>
      </div>
    </section>

    <section class="grid gap-4 xl:grid-cols-[1fr_1fr_0.8fr]">
      <article class="rounded-lg border border-hairline bg-white p-5">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-base font-bold text-ink">{{ copy.priorityTasks }}</h2>
          <span class="rounded-full bg-primary/10 px-2 py-1 text-xs font-bold text-primary">{{ pendingTasks.length }}</span>
        </div>
        <div v-if="pendingTasks.length === 0" class="rounded-lg border border-dashed border-hairline p-6 text-sm text-muted">
          {{ copy.noTasks }}
        </div>
        <button
          v-for="task in pendingTasks"
          :key="task.id || task.title"
          @click="onTaskClick(task)"
          class="mb-3 w-full rounded-lg border border-hairline bg-[#fbfaf8] p-4 text-left transition hover:border-ink"
        >
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-sm font-bold text-ink">{{ task.title }}</div>
              <div class="mt-1 text-xs text-muted">{{ task.time || task.description || copy.needsReview }}</div>
            </div>
            <span
              class="rounded-full px-2 py-1 text-xs font-bold"
              :class="task.urgency === 'high' ? 'bg-primary/10 text-primary' : 'bg-[#edf2ff] text-[#364fc7]'"
            >
              {{ task.tag || task.urgency || 'task' }}
            </span>
          </div>
        </button>
      </article>

      <article class="rounded-lg border border-hairline bg-white p-5">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-base font-bold text-ink">{{ copy.topSkus }}</h2>
          <router-link to="/app/products" class="text-xs font-bold text-primary no-underline">{{ copy.viewAll }}</router-link>
        </div>
        <div v-if="topSkus.length === 0" class="rounded-lg border border-dashed border-hairline p-6 text-sm text-muted">
          {{ copy.noSku }}
        </div>
        <div
          v-for="(sku, index) in topSkus"
          :key="sku.name"
          class="flex items-center justify-between gap-4 border-b border-hairline-soft py-3 last:border-b-0"
        >
          <div class="flex items-center gap-3">
            <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-[#f5f4f0] text-xs font-bold">{{ index + 1 }}</span>
            <div>
              <div class="text-sm font-bold text-ink">{{ sku.name }}</div>
              <div class="text-xs text-muted">{{ sku.category }}</div>
            </div>
          </div>
          <div class="text-right">
            <div class="text-sm font-bold text-ink">{{ sku.sales }} {{ copy.sold }}</div>
            <div class="text-xs text-muted">{{ sku.revenue }}</div>
          </div>
        </div>
      </article>

      <article class="rounded-lg border border-hairline bg-white p-5">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-base font-bold text-ink">{{ copy.campaigns }}</h2>
          <router-link to="/app/marketing" class="text-xs font-bold text-primary no-underline">{{ copy.manage }}</router-link>
        </div>
        <div v-for="campaign in campaigns" :key="campaign.name" class="mb-3 rounded-lg border border-hairline bg-[#fbfaf8] p-4 last:mb-0">
          <div class="flex items-center justify-between gap-3">
            <div class="text-sm font-bold text-ink">{{ campaign.name }}</div>
            <span class="rounded-full bg-white px-2 py-1 text-xs font-bold text-muted">{{ campaign.channel }}</span>
          </div>
          <div class="mt-3 flex items-center justify-between text-xs">
            <span class="font-bold" :class="campaign.status === 'active' ? 'text-[#237b4b]' : 'text-muted'">{{ campaign.status }}</span>
            <span class="text-muted">{{ campaign.conversion }} {{ copy.conversion }}</span>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { useAuthStore } from '../stores/auth'
import { request } from '../utils/request'
import StoreSelector from '../components/StoreSelector.vue'
import { useLanguage } from '../utils/language'

const auth = useAuthStore()
const router = useRouter()
const { language } = useLanguage()
const chartRef = ref(null)
let chartInstance = null

const currentStoreId = ref(null)
const overviewData = ref(null)
const trendsData = ref(null)
const topSkusData = ref([])
const pendingTasks = ref([])
const recentTraces = ref([])
const activeRange = ref('30d')
const ranges = [
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
]

const copy = computed(() => translations[language.value])

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return copy.value.goodMorning
  if (hour < 18) return copy.value.goodAfternoon
  return copy.value.goodEvening
})

const readiness = computed(() => copy.value.readiness)

const translations = {
  zh: {
    kicker: '运营指挥中心',
    subtitle: '监控门店健康、识别风险，并把高价值问题交给 AI 分析工作流。',
    askAgent: '询问智能体',
    goodMorning: '早上好',
    goodAfternoon: '下午好',
    goodEvening: '晚上好',
    monthOverMonth: '较上月',
    revenueTrend: '营收趋势',
    revenueTrendDesc: '按所选门店和时间窗口展示营收信号。',
    agentReadiness: '智能体状态',
    agentReadinessDesc: '面向经营智能体的可观测性检查。',
    online: '在线',
    priorityTasks: '优先任务',
    noTasks: '暂无待处理任务，工作台状态良好。',
    needsReview: '需要运营人员确认',
    topSkus: '热销 SKU',
    viewAll: '查看全部',
    noSku: 'SKU 数据加载中或暂不可用。',
    sold: '已售',
    campaigns: '营销活动',
    recentRuns: '最近 AI 决策',
    recentRunsDesc: '查看最近保存的智能体运行和可回放 trace。',
    openAnalysis: '打开 AI 分析',
    noRuns: '暂无智能体运行记录。',
    steps: '步',
    manage: '管理',
    conversion: '转化',
    currency: '¥',
    locale: 'zh-CN',
    statLabels: ['营收', '订单', '客单价', '净利润'],
    statUnits: ['销售', '数量', 'AOV', '利润'],
    fallbackCampaigns: [
      { name: '会员日恢复计划', channel: '短信', status: '进行中', conversion: '3.2%' },
      { name: '雨天外卖组合', channel: '外卖平台', status: '进行中', conversion: '4.1%' },
      { name: '高毛利套餐', channel: '小程序', status: '草稿', conversion: '-' },
    ],
    readiness: [
      { label: 'SSE 流式输出', value: '就绪', score: 96 },
      { label: 'RAG 知识库', value: '已索引', score: 88 },
      { label: '审批工作流', value: '受控', score: 82 },
      { label: 'Trace 回放', value: '已保存', score: 76 },
    ],
  },
  en: {
    kicker: 'Operations command center',
    subtitle: 'Monitor store health, spot risks, and send high-impact questions to the AI analysis workflow.',
    askAgent: 'Ask the agent',
    goodMorning: 'Good morning',
    goodAfternoon: 'Good afternoon',
    goodEvening: 'Good evening',
    monthOverMonth: 'month over month',
    revenueTrend: 'Revenue trend',
    revenueTrendDesc: 'Store-filtered revenue signal for the selected time window.',
    agentReadiness: 'Agent readiness',
    agentReadinessDesc: 'Operational checks inspired by agent observability platforms.',
    online: 'online',
    priorityTasks: 'Priority tasks',
    noTasks: 'No pending tasks. The workspace is clear.',
    needsReview: 'Needs operator review',
    topSkus: 'Top SKUs',
    viewAll: 'View all',
    noSku: 'SKU data is loading or not available.',
    sold: 'sold',
    campaigns: 'Campaigns',
    recentRuns: 'Recent agent runs',
    recentRunsDesc: 'Review recent saved agent runs and replayable traces.',
    openAnalysis: 'Open AI analysis',
    noRuns: 'No saved agent runs yet.',
    steps: 'steps',
    manage: 'Manage',
    conversion: 'conversion',
    currency: '$',
    locale: 'en-US',
    statLabels: ['Revenue', 'Orders', 'Avg ticket', 'Net profit'],
    statUnits: ['sales', 'volume', 'AOV', 'margin'],
    fallbackCampaigns: [
      { name: 'Member day recovery', channel: 'SMS', status: 'active', conversion: '3.2%' },
      { name: 'Rainy-day delivery kit', channel: 'Delivery', status: 'active', conversion: '4.1%' },
      { name: 'High-margin bundle', channel: 'Mini app', status: 'draft', conversion: '-' },
    ],
    readiness: [
      { label: 'SSE streaming', value: 'ready', score: 96 },
      { label: 'RAG playbooks', value: 'indexed', score: 88 },
      { label: 'Approval workflow', value: 'guarded', score: 82 },
      { label: 'Trace replay', value: 'stored', score: 76 },
    ],
  },
}

function formatMoney(value) {
  if (value == null) return '-'
  return `${copy.value.currency}${Number(value).toLocaleString(copy.value.locale, { maximumFractionDigits: 0 })}`
}

function formatNumber(value) {
  if (value == null) return '-'
  return Number(value).toLocaleString(copy.value.locale)
}

const statCards = computed(() => {
  const kpis = overviewData.value?.kpis || {}
  const growth = overviewData.value?.mom_growth || {}
  return [
    { label: copy.value.statLabels[0], value: formatMoney(kpis.revenue), growth: growth.revenue_pct || 0, unit: copy.value.statUnits[0] },
    { label: copy.value.statLabels[1], value: formatNumber(kpis.order_count), growth: growth.orders_pct || 0, unit: copy.value.statUnits[1] },
    { label: copy.value.statLabels[2], value: formatMoney(kpis.avg_ticket), growth: 0, unit: copy.value.statUnits[2] },
    { label: copy.value.statLabels[3], value: formatMoney(kpis.net_profit), growth: 0, unit: copy.value.statUnits[3] },
  ]
})

const topSkus = computed(() => (topSkusData.value || []).map((sku) => ({
  name: sku.sku_name,
  category: sku.category,
  sales: sku.total_sales,
  revenue: formatMoney(sku.total_revenue),
})))

const campaigns = ref([])

function onStoreChange(storeId) {
  currentStoreId.value = storeId
  fetchAllData()
}

function setRange(range) {
  activeRange.value = range.label
  fetchTrends(range.days)
}

async function fetchAllData() {
  await Promise.all([fetchOverview(), fetchTrends(activeDays.value), fetchTopSkus(), fetchCampaigns(), fetchAlerts(), fetchRecentTraces()])
}

const activeDays = computed(() => ranges.find((range) => range.label === activeRange.value)?.days || 30)

async function fetchOverview() {
  try {
    const qs = currentStoreId.value ? `?store_id=${currentStoreId.value}` : ''
    const res = await request(`/api/dashboard/overview${qs}`)
    overviewData.value = res.data
  } catch {
    overviewData.value = null
  }
}

async function fetchTrends(days = 30) {
  try {
    const params = [`days=${days}`]
    if (currentStoreId.value) params.push(`store_id=${currentStoreId.value}`)
    const res = await request(`/api/dashboard/trends?${params.join('&')}`)
    trendsData.value = res.data
  } catch {
    trendsData.value = null
  }
  updateChart()
}

async function fetchTopSkus() {
  try {
    const params = ['limit=5', 'days=7']
    if (currentStoreId.value) params.push(`store_id=${currentStoreId.value}`)
    const res = await request(`/api/dashboard/top-skus?${params.join('&')}`)
    topSkusData.value = res.data || []
  } catch {
    topSkusData.value = []
  }
}

async function fetchAlerts() {
  try {
    const qs = currentStoreId.value ? `&store_id=${currentStoreId.value}` : ''
    const res = await request(`/api/tasks?status=pending&limit=5${qs}`)
    pendingTasks.value = res.data || []
  } catch {
    pendingTasks.value = []
  }
}

async function fetchRecentTraces() {
  try {
    const res = await request('/api/agent/traces?limit=3')
    recentTraces.value = res.data || []
  } catch {
    recentTraces.value = []
  }
}

async function fetchCampaigns() {
  try {
    const qs = currentStoreId.value ? `?store_id=${currentStoreId.value}` : ''
    const res = await request(`/api/dashboard/campaigns${qs}`)
    const data = res.data || []
    if (data.length) {
      campaigns.value = data.map((campaign) => ({
        name: campaign.name,
        channel: campaign.channel,
        status: campaign.status,
        conversion: campaign.conversion_rate ? `${(campaign.conversion_rate * 100).toFixed(1)}%` : '-',
      }))
    }
  } catch {
    campaigns.value = copy.value.fallbackCampaigns
  }
  if (!campaigns.value.length) campaigns.value = copy.value.fallbackCampaigns
}

function onTaskClick(task) {
  if (task.link_to) router.push(task.link_to)
}

function renderChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateChart()
  new ResizeObserver(() => chartInstance?.resize()).observe(chartRef.value)
}

function updateChart() {
  if (!chartInstance) return
  const dates = trendsData.value?.dates || Array.from({ length: activeDays.value }, (_, index) => `D${index + 1}`)
  const revenue = trendsData.value?.revenue || dates.map((_, index) => 18000 + Math.sin(index / 2) * 2800 + index * 170)
  chartInstance.setOption({
    backgroundColor: 'transparent',
    color: ['#ff385c'],
    grid: { top: 18, right: 18, bottom: 28, left: 56 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#111827',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 12 },
      valueFormatter: (value) => formatMoney(value),
    },
    xAxis: {
      type: 'category',
      data: dates.map((date) => String(date).slice(-5)),
      axisLine: { lineStyle: { color: '#dddddd' } },
      axisTick: { show: false },
      axisLabel: { color: '#929292', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#ebebeb' } },
      axisLabel: { color: '#929292', fontSize: 11, formatter: (value) => `${copy.value.currency}${Math.round(value / 1000)}k` },
    },
    series: [
      {
        type: 'line',
        data: revenue,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255,56,92,0.18)' },
            { offset: 1, color: 'rgba(255,56,92,0)' },
          ]),
        },
      },
    ],
  })
}

onMounted(() => {
  renderChart()
  fetchAllData()
})
</script>
