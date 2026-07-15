<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-semibold text-ink mb-1">营销中心</h2>
        <p class="text-muted text-sm">管理营销活动，生成多渠道文案，一键投放</p>
      </div>
      <div class="flex gap-2 items-center">
        <StoreSelector @change="onStoreChange" />
        <button @click="router.push('/app/reports')"
          class="bg-surface-soft text-ink px-4 py-2 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
          📊 数据概览
        </button>
        <button @click="toggleBatchMode"
          class="bg-surface-soft text-ink px-4 py-2 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
          {{ isBatchMode ? '退出批量删除' : '批量删除' }}
        </button>
        <button @click="showCreateCampaign = true"
          class="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-active transition-colors">
          + 创建活动
        </button>
      </div>
    </div>

    <div v-if="activeTab === 'campaigns' && isBatchMode" class="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-hairline bg-canvas p-3">
      <label class="flex items-center gap-2 text-sm font-medium text-ink">
        <input type="checkbox" class="h-4 w-4 accent-primary" :checked="allSelected" @change="toggleAll" />
        全选
      </label>
      <span class="text-sm text-muted">已选择 {{ selectedCount }} 项</span>
      <button @click="showBatchDeleteConfirm = true" :disabled="selectedCount === 0"
        class="rounded-lg bg-error-text px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50">
        确认删除
      </button>
      <button @click="exitBatchMode" class="rounded-lg bg-surface-soft px-4 py-2 text-sm font-medium text-ink hover:bg-hairline">
        取消
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <div v-for="s in stats" :key="s.label" class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-muted text-xs font-medium mb-1">{{ s.label }}</div>
        <div class="text-ink font-bold" style="font-size: 22px">{{ s.value }}</div>
      </div>
    </div>
    <p v-if="statsError" class="mb-4 text-sm text-error-text">{{ statsError }}</p>

    <!-- Tabs -->
    <div class="flex gap-6 border-b border-hairline mb-6">
      <span v-for="tab in tabs" :key="tab.key"
        class="pb-3 text-sm font-medium cursor-pointer transition-colors"
        :class="activeTab === tab.key ? 'text-ink border-b-2 border-ink' : 'text-muted hover:text-ink'"
        @click="activeTab = tab.key">{{ tab.label }}</span>
    </div>

    <!-- Campaign list -->
    <div v-if="activeTab === 'campaigns'" class="space-y-4">
      <div v-for="c in campaigns" :key="c.id"
        class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-start gap-3">
            <input v-if="isBatchMode" type="checkbox" class="mt-0.5 h-4 w-4 shrink-0 accent-primary" :checked="isSelected(c.id)" @change="toggleItem(c.id)" />
            <div>
            <div class="text-sm font-semibold text-ink mb-1">{{ c.name }}</div>
            <div class="flex gap-2 items-center">
              <span class="text-xs px-2 py-0.5 rounded-full bg-surface-soft text-muted">{{ c.channel }}</span>
              <span class="text-xs px-2 py-0.5 rounded-full font-semibold"
                :class="c.status === 'active' ? 'bg-primary/10 text-primary' : c.status === 'completed' ? 'bg-ink/6 text-ink' : 'bg-muted/8 text-muted'">
                {{ { active: '进行中', completed: '已完成', draft: '草稿' }[c.status] }}
              </span>
              <span class="text-xs text-muted-soft">{{ c.period }}</span>
            </div>
            </div>
          </div>
          <div v-if="!isBatchMode" class="flex gap-2">
            <button @click="editCampaign(c)" class="bg-surface-soft text-ink px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer hover:bg-hairline transition-colors">编辑</button>
            <button @click="viewCampaignData(c)" class="bg-primary/8 text-primary px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer hover:bg-primary/15 transition-colors">查看数据</button>
          </div>
        </div>
        <div v-if="c.content" class="mb-3 rounded-lg border border-primary/15 bg-primary/5 p-3 text-sm leading-6 text-body">
          {{ c.content }}
        </div>
        <div class="grid grid-cols-4 gap-4 mb-3">
          <div><div class="text-base font-bold text-ink">{{ c.reach }}</div><div class="text-xs text-muted-soft">触达人数</div></div>
          <div><div class="text-base font-bold text-ink">{{ c.clicks }}</div><div class="text-xs text-muted-soft">点击次数</div></div>
          <div><div class="text-base font-bold text-ink">{{ c.conversion }}</div><div class="text-xs text-muted-soft">转化率</div></div>
          <div><div class="text-base font-bold text-ink">¥{{ c.revenue }}</div><div class="text-xs text-muted-soft">带来营收</div></div>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted-soft w-12">进度</span>
          <div class="flex-1 h-1.5 bg-surface-soft rounded-full overflow-hidden">
            <div class="h-full bg-primary rounded-full" :style="{ width: c.progress + '%' }"></div>
          </div>
          <span class="text-xs text-ink font-medium">{{ c.progress }}%</span>
        </div>
      </div>
    </div>

    <!-- Copy templates -->
    <div v-if="activeTab === 'copy'" class="grid grid-cols-2 gap-4">
      <div v-for="t in copyTemplates" :key="t.name"
        class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="flex items-center gap-3 mb-3">
          <span class="w-10 h-10 rounded-xl bg-surface-soft flex items-center justify-center text-xl">{{ t.icon }}</span>
          <div>
            <div class="text-sm font-semibold text-ink">{{ t.name }}</div>
            <div class="text-xs text-muted-soft">{{ t.desc }}</div>
          </div>
        </div>
        <div class="bg-surface-soft rounded-lg p-3 mb-3 text-sm text-body leading-relaxed">{{ t.preview }}</div>
        <div class="flex gap-2">
          <button @click="copyTemplate(t.preview)" class="flex-1 bg-primary text-white px-3 py-2 rounded-lg text-xs font-medium cursor-pointer hover:bg-primary-active transition-colors">使用模板</button>
          <button @click="aiGenerate(t.preview)" class="flex-1 bg-surface-soft text-ink px-3 py-2 rounded-lg text-xs font-medium cursor-pointer hover:bg-hairline transition-colors">AI 生成</button>
        </div>
      </div>
    </div>

    <!-- Channel settings -->
    <div v-if="activeTab === 'channels'" class="grid grid-cols-3 gap-4">
      <div v-for="ch in channelSettings" :key="ch.name"
        class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="flex items-center gap-3 mb-4">
          <span class="w-12 h-12 rounded-xl bg-surface-soft flex items-center justify-center text-2xl">{{ ch.icon }}</span>
          <div>
            <div class="text-sm font-semibold text-ink">{{ ch.name }}</div>
            <div class="text-xs text-muted-soft">{{ ch.desc }}</div>
          </div>
        </div>
        <div class="space-y-2 mb-4">
          <div class="flex justify-between text-xs"><span class="text-muted-soft">状态</span><span class="text-primary font-medium">{{ ch.connected ? '已连接' : '未连接' }}</span></div>
          <div class="flex justify-between text-xs"><span class="text-muted-soft">本月发送</span><span class="text-ink font-medium">{{ ch.sent }}</span></div>
          <div class="flex justify-between text-xs"><span class="text-muted-soft">平均转化</span><span class="text-ink font-medium">{{ ch.avgConversion }}</span></div>
        </div>
        <button @click="toggleChannel(ch)"
          class="w-full bg-surface-soft text-ink px-3 py-2 rounded-lg text-xs font-medium cursor-pointer hover:bg-hairline transition-colors">
          {{ ch.connected ? '管理' : '连接' }}
        </button>
      </div>
    </div>

    <!-- Copy message -->
    <div v-if="copyMsg" class="fixed bottom-8 left-1/2 -translate-x-1/2 bg-ink text-white px-6 py-3 rounded-xl text-sm font-medium shadow-lg z-50">
      {{ copyMsg }}
    </div>
  </div>

  <!-- Create/Edit campaign modal -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showCreateCampaign" class="fixed inset-0 z-100 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-2xl p-6 w-100 shadow-xl">
          <h3 class="text-base font-semibold text-ink mb-4">{{ editingCampaign ? '编辑活动' : '创建活动' }}</h3>
          <div class="space-y-4 mb-6">
            <div>
              <label class="text-sm text-muted block mb-1.5">活动名称</label>
              <input v-model="campaignForm.name"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors"
                placeholder="输入活动名称" />
            </div>
            <div>
              <label class="text-sm text-muted block mb-1.5">投放渠道</label>
              <select v-model="campaignForm.channel"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors">
                <option>短信</option><option>小红书</option><option>朋友圈</option><option>全渠道</option>
              </select>
            </div>
            <div>
              <label class="text-sm text-muted block mb-1.5">活动周期</label>
              <input v-model="campaignForm.period"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors"
                placeholder="例如: 6.1 - 6.15" />
            </div>
          </div>
          <div class="flex gap-3 justify-end">
            <button @click="showCreateCampaign = false; editingCampaign = null"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-surface-soft text-ink hover:bg-hairline transition-colors cursor-pointer">
              取消
            </button>
            <button @click="saveCampaign"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-active transition-colors cursor-pointer">
              {{ editingCampaign ? '保存' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <BatchDeleteConfirm
    :open="showBatchDeleteConfirm"
    :count="selectedCount"
    entity-name="营销活动"
    :loading="batchDeleting"
    @confirm="doBatchDelete"
    @cancel="showBatchDeleteConfirm = false"
  />
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BatchDeleteConfirm from '../components/BatchDeleteConfirm.vue'
import { useBatchSelection } from '../composables/useBatchSelection'
import { request } from '../utils/request'
import StoreSelector from '../components/StoreSelector.vue'

const router = useRouter()
const currentStoreId = ref(null)

function onStoreChange(storeId) {
  currentStoreId.value = storeId
  fetchCampaigns()
  fetchCampaignStats()
}

async function fetchCampaigns() {
  try {
    const qs = currentStoreId.value ? `?store_id=${currentStoreId.value}` : ''
    const res = await request(`/api/dashboard/campaigns${qs}`)
    const data = res.data || []
    campaigns.value = data.map(c => ({
      id: c.id,
      name: c.name,
      channel: c.channel,
      status: c.status,
      period: '—',
      reach: c.budget ? Math.round(c.budget * 10).toLocaleString() : '—',
      clicks: c.spend ? Math.round(c.spend * 5).toLocaleString() : '—',
      conversion: c.conversion_rate ? `${(c.conversion_rate * 100).toFixed(1)}%` : '—',
      revenue: c.revenue_generated ? c.revenue_generated.toLocaleString() : '—',
      progress: c.status === 'completed' ? 100 : c.status === 'active' ? 60 : 0,
      content: c.content_text || '',
    }))
  } catch { /* API failed, keep existing data */ }
}

async function fetchCampaignStats() {
  statsLoading.value = true
  statsError.value = ''
  stats.value = statLabels.map((label) => ({ label, value: '...' }))
  try {
    const qs = currentStoreId.value ? `?store_id=${currentStoreId.value}` : ''
    const res = await request(`/api/dashboard/campaigns/stats${qs}`)
    const data = res.data || {}
    stats.value = [
      { label: '总活动数', value: String(data.total_campaigns ?? 0) },
      { label: '进行中活动数', value: String(data.active_campaigns ?? 0) },
      { label: '平均转化率', value: `${((data.avg_conversion_rate || 0) * 100).toFixed(1)}%` },
      { label: '营销 ROI', value: `${Number(data.marketing_roi || 0).toFixed(1)}x` },
    ]
  } catch (err) {
    statsError.value = `营销统计加载失败: ${err.message}`
    stats.value = statLabels.map((label) => ({ label, value: '-' }))
  } finally {
    statsLoading.value = false
  }
}

onMounted(() => {
  fetchCampaigns()
  fetchCampaignStats()
})
const activeTab = ref('campaigns')
const copyMsg = ref('')

function copyTemplate(text) {
  navigator.clipboard.writeText(text).then(() => {
    copyMsg.value = '模板已复制到剪贴板'
    setTimeout(() => { copyMsg.value = '' }, 2000)
  })
}

function aiGenerate(template) {
  router.push({ path: '/app/ai', query: { q: `请帮我基于以下模板生成营销文案：\n${template}` } })
}
const tabs = [
  { key: 'campaigns', label: '活动管理' },
  { key: 'copy', label: '文案模板' },
  { key: 'channels', label: '渠道配置' },
]

const statLabels = ['总活动数', '进行中活动数', '平均转化率', '营销 ROI']
const statsLoading = ref(false)
const statsError = ref('')
const stats = ref(statLabels.map((label) => ({ label, value: '...' })))

const campaigns = ref([])
const batchDeleting = ref(false)
const showBatchDeleteConfirm = ref(false)
const {
  isBatchMode,
  selectedIds,
  selectedCount,
  allSelected,
  exitBatchMode,
  toggleBatchMode,
  isSelected,
  toggleItem,
  toggleAll,
} = useBatchSelection(campaigns)

const copyTemplates = [
  { icon: '📕', name: '小红书种草文案', desc: '适合新品推广、美食推荐', preview: '☕️ 打工人续命神器！冰美式买一送一，活动截止本月底～ #咖啡推荐 #宝藏小店' },
  { icon: '💬', name: '朋友圈推广文案', desc: '适合门店活动、限时优惠', preview: '【夏日冰饮季 ☀️】冰美式买一送一，生椰拿铁第二杯半价！📍门店地址：XX路XX号' },
  { icon: '📱', name: '短信营销文案', desc: '适合会员召回、精准触达', preview: '【AuraSaaS】会员专属：冰美式买一送一，活动截止本月底。退订回T' },
  { icon: '🎬', name: '短视频脚本', desc: '适合抖音、快手推广', preview: '【开头】打工人午休续命必备！【展示】现磨咖啡豆...【结尾】限时买一送一！' },
]

const channelSettings = [
  { icon: '📕', name: '小红书', desc: '种草营销平台', connected: true, sent: '2,400', avgConversion: '4.2%' },
  { icon: '💬', name: '微信朋友圈', desc: '社交广告投放', connected: true, sent: '5,600', avgConversion: '2.8%' },
  { icon: '📱', name: '短信营销', desc: '精准短信触达', connected: true, sent: '12,000', avgConversion: '3.5%' },
  { icon: '🎬', name: '抖音', desc: '短视频推广', connected: false, sent: '—', avgConversion: '—' },
  { icon: '🛵', name: '美团/饿了么', desc: '外卖平台推广', connected: true, sent: '8,900', avgConversion: '5.1%' },
  { icon: '📧', name: '邮件营销', desc: 'EDM 邮件推送', connected: false, sent: '—', avgConversion: '—' },
]

const showCreateCampaign = ref(false)
const editingCampaign = ref(null)
const campaignForm = reactive({ name: '', channel: '短信', status: 'draft', period: '' })

function editCampaign(c) {
  editingCampaign.value = c
  campaignForm.name = c.name
  campaignForm.channel = c.channel
  campaignForm.status = c.status
  campaignForm.period = c.period
  showCreateCampaign.value = true
}

function viewCampaignData(c) {
  alert(`活动「${c.name}」\n渠道: ${c.channel}\n触达: ${c.reach}\n点击: ${c.clicks}\n转化率: ${c.conversion}\n带来营收: ¥${c.revenue}`)
}

async function saveCampaign() {
  if (editingCampaign.value) {
    try {
      await request(`/api/dashboard/campaigns/${editingCampaign.value.id}`, {
        method: 'PUT',
        body: JSON.stringify({ campaign_name: campaignForm.name, channel: campaignForm.channel, status: campaignForm.status }),
      })
      editingCampaign.value.name = campaignForm.name
      editingCampaign.value.channel = campaignForm.channel
      editingCampaign.value.status = campaignForm.status
      editingCampaign.value.period = campaignForm.period
    } catch (e) { alert('保存失败: ' + e.message) }
  } else {
    try {
      await request('/api/dashboard/campaigns', {
        method: 'POST',
        body: JSON.stringify({ name: campaignForm.name, channel: campaignForm.channel }),
      })
    } catch (e) { alert('创建失败: ' + e.message) }
  }
  showCreateCampaign.value = false
  editingCampaign.value = null
  campaignForm.name = ''
  campaignForm.channel = '短信'
  campaignForm.status = 'draft'
  campaignForm.period = ''
  await fetchCampaigns()
}

async function doBatchDelete() {
  if (!selectedCount.value) return
  batchDeleting.value = true
  try {
    await request('/api/dashboard/campaigns/batch-delete', {
      method: 'POST',
      body: JSON.stringify(selectedIds.value),
    })
    showBatchDeleteConfirm.value = false
    exitBatchMode()
    await fetchCampaigns()
  } catch (e) {
    alert('批量删除失败: ' + e.message)
  } finally {
    batchDeleting.value = false
  }
}

function toggleChannel(ch) {
  if (ch.connected) {
    alert(`正在管理「${ch.name}」渠道配置\n已发送: ${ch.sent}\n平均转化: ${ch.avgConversion}`)
  } else {
    ch.connected = true
    ch.sent = '0'
    ch.avgConversion = '0%'
  }
}
</script>
