<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-semibold text-ink mb-1">门店管理</h2>
        <p class="text-muted text-sm">管理连锁门店，监控各店经营状态</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="toggleBatchMode"
          class="bg-surface-soft text-ink px-4 py-2 rounded-lg text-sm font-medium hover:bg-hairline transition-colors">
          {{ isBatchMode ? '退出批量删除' : '批量删除' }}
        </button>
        <button @click="showAddModal = true"
          class="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-active transition-colors">
          + 添加门店
        </button>
      </div>
    </div>

    <div v-if="isBatchMode" class="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-hairline bg-canvas p-3">
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

    <!-- Store overview stats -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <div v-for="s in storeStats" :key="s.label"
        class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="text-muted text-xs font-medium mb-1">{{ s.label }}</div>
        <div class="text-ink font-bold" style="font-size: 22px">{{ s.value }}</div>
      </div>
    </div>

    <!-- Stores list -->
    <div class="grid grid-cols-2 gap-4">
      <div v-for="store in stores" :key="store.id"
        class="bg-canvas border border-hairline rounded-xl p-5">
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <input v-if="isBatchMode" type="checkbox" class="h-4 w-4 shrink-0 accent-primary" :checked="isSelected(store.id)" @change="toggleItem(store.id)" />
            <span class="w-12 h-12 rounded-xl bg-surface-soft flex items-center justify-center text-2xl">🏪</span>
            <div>
              <div class="text-sm font-semibold text-ink">{{ store.name }}</div>
              <div class="text-xs text-muted-soft">{{ store.address }}</div>
            </div>
          </div>
          <span class="text-xs px-2.5 py-0.5 rounded-full font-medium"
            :class="store.status === 'open' ? 'bg-primary/8 text-primary' : 'bg-muted/8 text-muted'">
            {{ store.status === 'open' ? '营业中' : '已打烊' }}
          </span>
        </div>

        <div class="grid grid-cols-3 gap-3 mb-4">
          <div><div class="text-base font-bold text-ink">¥{{ store.revenue }}</div><div class="text-xs text-muted-soft">今日营收</div></div>
          <div><div class="text-base font-bold text-ink">{{ store.orders }}</div><div class="text-xs text-muted-soft">今日订单</div></div>
          <div><div class="text-base font-bold text-ink">{{ store.rating }}</div><div class="text-xs text-muted-soft">评分</div></div>
        </div>

        <!-- Staff & capacity -->
        <div class="flex items-center gap-4 mb-4 text-xs text-muted">
          <span>👨‍🍳 员工 {{ store.staff_count }}人</span>
          <span>🪑 座位 {{ store.seats }}个</span>
          <span>📍 {{ store.area }}</span>
        </div>

        <!-- Performance bar -->
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xs text-muted-soft w-16">目标达成</span>
          <div class="flex-1 h-1.5 bg-surface-soft rounded-full overflow-hidden">
            <div class="h-full bg-primary rounded-full" :style="{ width: Math.min(100, store.achievement) + '%' }"></div>
          </div>
          <span class="text-xs text-ink font-medium w-10 text-right">{{ store.achievement }}%</span>
        </div>

        <div v-if="!isBatchMode" class="flex gap-2">
          <button @click="viewDetail(store)" class="flex-1 bg-surface-soft text-ink px-3 py-2 rounded-lg text-xs font-medium cursor-pointer hover:bg-hairline transition-colors">详情</button>
          <button @click="openManage(store)" class="flex-1 bg-primary/8 text-primary px-3 py-2 rounded-lg text-xs font-medium cursor-pointer hover:bg-primary/15 transition-colors">管理</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Add store modal -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showAddModal" class="fixed inset-0 z-100 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-2xl p-6 w-120 shadow-xl">
          <h3 class="text-base font-semibold text-ink mb-4">添加门店</h3>
          <div class="space-y-4 mb-4">
            <div>
              <label class="text-sm text-muted block mb-1.5">门店名称 <span class="text-red-400">*</span></label>
              <input v-model="addForm.name" placeholder="例如: 望京SOHO店"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-sm text-muted block mb-1.5">城市</label>
                <input v-model="addForm.city" placeholder="例如: 北京"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
              <div>
                <label class="text-sm text-muted block mb-1.5">商圈</label>
                <input v-model="addForm.area" placeholder="例如: 朝阳区"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
            </div>
            <div>
              <label class="text-sm text-muted block mb-1.5">详细地址</label>
              <input v-model="addForm.address" placeholder="街道门牌号"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
            </div>
            <div>
              <label class="text-sm text-muted block mb-1.5">店长姓名</label>
              <input v-model="addForm.manager_name" placeholder="负责人姓名"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="text-sm text-muted block mb-1.5">座位数</label>
                <input v-model.number="addForm.seats" type="number" placeholder="0"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
              <div>
                <label class="text-sm text-muted block mb-1.5">员工数</label>
                <input v-model.number="addForm.staff_count" type="number" placeholder="0"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
              <div>
                <label class="text-sm text-muted block mb-1.5">评分</label>
                <input v-model.number="addForm.rating" type="number" step="0.1" min="1" max="5" placeholder="4.5"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
            </div>
          </div>
          <p v-if="addMsg" class="text-sm mb-3" :class="addMsgType === 'error' ? 'text-red-500' : 'text-muted'">{{ addMsg }}</p>
          <div class="flex gap-3 justify-end">
            <button @click="showAddModal = false"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-surface-soft text-ink hover:bg-hairline transition-colors cursor-pointer">
              取消
            </button>
            <button @click="addStore"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-active transition-colors cursor-pointer">
              添加
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Store detail modal -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showDetailModal && selectedStore" class="fixed inset-0 z-100 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-2xl p-6 w-120 shadow-xl">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-base font-semibold text-ink">{{ selectedStore.name }}</h3>
            <span class="text-xs px-2.5 py-0.5 rounded-full font-medium"
              :class="selectedStore.status === 'open' ? 'bg-primary/8 text-primary' : 'bg-muted/8 text-muted'">
              {{ selectedStore.status === 'open' ? '营业中' : '已打烊' }}
            </span>
          </div>

          <!-- Basic info -->
          <div class="grid grid-cols-2 gap-x-6 gap-y-3 mb-5">
            <div class="flex justify-between text-sm"><span class="text-muted">城市</span><span class="text-ink">{{ selectedStore.city || '—' }}</span></div>
            <div class="flex justify-between text-sm"><span class="text-muted">商圈</span><span class="text-ink">{{ selectedStore.area || '—' }}</span></div>
            <div class="flex justify-between text-sm"><span class="text-muted">店长</span><span class="text-ink">{{ selectedStore.manager_name || '—' }}</span></div>
            <div class="flex justify-between text-sm"><span class="text-muted">评分</span><span class="text-ink">{{ selectedStore.rating || '—' }}</span></div>
            <div class="flex justify-between text-sm"><span class="text-muted">员工</span><span class="text-ink">{{ selectedStore.staff_count || 0 }}人</span></div>
            <div class="flex justify-between text-sm"><span class="text-muted">座位</span><span class="text-ink">{{ selectedStore.seats || 0 }}个</span></div>
          </div>
          <div class="text-sm text-muted mb-5">📍 {{ selectedStore.address || selectedStore.city }}</div>

          <!-- Performance metrics -->
          <div class="bg-surface-soft rounded-xl p-4 mb-5">
            <div class="text-xs font-semibold text-ink mb-3">经营数据（近30天）</div>
            <div class="grid grid-cols-3 gap-4">
              <div class="text-center">
                <div class="text-lg font-bold text-ink">¥{{ selectedStore.month_revenue?.toLocaleString() || '—' }}</div>
                <div class="text-xs text-muted-soft">总营收</div>
              </div>
              <div class="text-center">
                <div class="text-lg font-bold text-ink">{{ selectedStore.month_orders || '—' }}</div>
                <div class="text-xs text-muted-soft">总订单</div>
              </div>
              <div class="text-center">
                <div class="text-lg font-bold text-ink">{{ selectedStore.avg_margin || '—' }}%</div>
                <div class="text-xs text-muted-soft">平均毛利率</div>
              </div>
            </div>
          </div>

          <div class="flex justify-end">
            <button @click="showDetailModal = false"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-surface-soft text-ink hover:bg-hairline transition-colors cursor-pointer">
              关闭
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Store manage modal -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showManageModal && selectedStore" class="fixed inset-0 z-100 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-2xl p-6 w-120 shadow-xl">
          <h3 class="text-base font-semibold text-ink mb-4">管理门店 — {{ selectedStore.name }}</h3>
          <div class="space-y-4 mb-4">
            <div>
              <label class="text-sm text-muted block mb-1.5">门店名称</label>
              <input v-model="manageForm.name"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-sm text-muted block mb-1.5">城市</label>
                <input v-model="manageForm.city"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
              <div>
                <label class="text-sm text-muted block mb-1.5">商圈</label>
                <input v-model="manageForm.area"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
            </div>
            <div>
              <label class="text-sm text-muted block mb-1.5">详细地址</label>
              <input v-model="manageForm.address"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
            </div>
            <div>
              <label class="text-sm text-muted block mb-1.5">店长</label>
              <input v-model="manageForm.manager_name"
                class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="text-sm text-muted block mb-1.5">座位数</label>
                <input v-model.number="manageForm.seats" type="number"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
              <div>
                <label class="text-sm text-muted block mb-1.5">员工数</label>
                <input v-model.number="manageForm.staff_count" type="number"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
              <div>
                <label class="text-sm text-muted block mb-1.5">评分</label>
                <input v-model.number="manageForm.rating" type="number" step="0.1" min="1" max="5"
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors" />
              </div>
            </div>
            <div>
              <label class="text-sm text-muted block mb-1.5">营业状态</label>
              <div class="flex gap-3">
                <button @click="manageForm.status = 'open'"
                  class="flex-1 px-4 py-2 rounded-lg text-sm font-medium border transition-colors cursor-pointer"
                  :class="manageForm.status === 'open' ? 'bg-primary/8 border-primary text-primary' : 'border-hairline text-muted hover:border-ink'">
                  营业中
                </button>
                <button @click="manageForm.status = 'closed'"
                  class="flex-1 px-4 py-2 rounded-lg text-sm font-medium border transition-colors cursor-pointer"
                  :class="manageForm.status === 'closed' ? 'bg-muted/8 border-muted text-muted' : 'border-hairline text-muted hover:border-ink'">
                  已打烊
                </button>
              </div>
            </div>
          </div>
          <p v-if="manageMsg" class="text-sm mb-3" :class="manageMsgType === 'error' ? 'text-red-500' : 'text-muted'">{{ manageMsg }}</p>
          <div class="flex gap-3 justify-end">
            <button @click="showManageModal = false"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-surface-soft text-ink hover:bg-hairline transition-colors cursor-pointer">
              取消
            </button>
            <button @click="saveStore"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-active transition-colors cursor-pointer">
              保存
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <BatchDeleteConfirm
    :open="showBatchDeleteConfirm"
    :count="selectedCount"
    entity-name="门店"
    :loading="batchDeleting"
    @confirm="doBatchDelete"
    @cancel="showBatchDeleteConfirm = false"
  />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import BatchDeleteConfirm from '../components/BatchDeleteConfirm.vue'
import { useBatchSelection } from '../composables/useBatchSelection'
import { request } from '../utils/request'

const showDetailModal = ref(false)
const showManageModal = ref(false)
const showAddModal = ref(false)
const selectedStore = ref(null)
const manageForm = ref({ name: '', city: '', area: '', address: '', manager_name: '', seats: 0, staff_count: 0, rating: 4.5, status: 'open' })
const manageMsg = ref('')
const manageMsgType = ref('')
const addForm = ref({ name: '', city: '', area: '', address: '', manager_name: '', seats: 0, staff_count: 0, rating: 4.5 })
const addMsg = ref('')
const addMsgType = ref('')

const stores = ref([
  { id: 1, name: '朝阳大悦城店', city: '北京', address: '北京市朝阳区朝阳北路101号', status: 'open', revenue: '18,450', orders: 234, rating: '4.8', staff_count: 12, seats: 80, area: '朝阳区', achievement: 92, manager_name: '李然' },
  { id: 2, name: '三里屯太古里店', city: '北京', address: '北京市朝阳区三里屯路19号', status: 'open', revenue: '16,800', orders: 198, rating: '4.7', staff_count: 10, seats: 60, area: '朝阳区', achievement: 88, manager_name: '张敏' },
  { id: 3, name: '中关村店', city: '北京', address: '北京市海淀区中关村大街15号', status: 'open', revenue: '14,200', orders: 176, rating: '4.6', staff_count: 8, seats: 50, area: '海淀区', achievement: 85, manager_name: '王磊' },
  { id: 4, name: '西单大悦城店', city: '北京', address: '北京市西城区西单北大街110号', status: 'open', revenue: '15,600', orders: 189, rating: '4.9', staff_count: 10, seats: 65, area: '西城区', achievement: 95, manager_name: '陈晨' },
  { id: 5, name: '望京店', city: '北京', address: '北京市朝阳区望京西路8号', status: 'open', revenue: '12,400', orders: 145, rating: '4.5', staff_count: 7, seats: 45, area: '朝阳区', achievement: 78, manager_name: '赵阳' },
  { id: 6, name: '国贸店', city: '北京', address: '北京市朝阳区建国门外大街1号', status: 'closed', revenue: '5,000', orders: 67, rating: '4.4', staff_count: 6, seats: 40, area: '朝阳区', achievement: 65, manager_name: '刘芳' },
])
stores.value = []
const loadingStores = ref(false)
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
} = useBatchSelection(stores)

const storeStats = computed(() => [
  { label: '总门店数', value: String(stores.value.length) },
  { label: '营业中', value: String(stores.value.filter(s => s.status === 'open').length) },
  { label: '平均评分', value: stores.value.length ? (stores.value.reduce((a, s) => a + parseFloat(s.rating), 0) / stores.value.length).toFixed(1) : '—' },
  { label: '总员工数', value: String(stores.value.reduce((a, s) => a + (s.staff_count || 0), 0)) },
])

function normalizeStore(store) {
  return {
    ...store,
    revenue: Number(store.revenue || 0).toLocaleString(),
    orders: Number(store.orders || 0),
    rating: store.rating == null ? '0.0' : String(store.rating),
    staff_count: Number(store.staff_count || 0),
    seats: Number(store.seats || 0),
    achievement: Number(store.achievement || 0),
  }
}

async function fetchStores() {
  loadingStores.value = true
  try {
    const res = await request('/api/dashboard/stores')
    stores.value = (res.data || []).map(normalizeStore)
  } finally {
    loadingStores.value = false
  }
}

function handleDataImported(event) {
  const importType = event.detail?.importType
  if (importType === 'stores' || importType === 'store' || importType === '门店') {
    fetchStores()
  }
}

async function viewDetail(store) {
  try {
    const res = await request(`/api/dashboard/stores/${store.id}`)
    selectedStore.value = { ...store, ...res.data }
  } catch {
    selectedStore.value = store
  }
  showDetailModal.value = true
}

function openManage(store) {
  selectedStore.value = store
  manageForm.value = {
    name: store.name, city: store.city || '', area: store.area || '',
    address: store.address || '', manager_name: store.manager_name || '',
    seats: store.seats || 0, staff_count: store.staff_count || 0,
    rating: parseFloat(store.rating) || 4.5, status: store.status || 'open',
  }
  showManageModal.value = true
  manageMsg.value = ''
}

async function saveStore() {
  if (!selectedStore.value) return
  try {
    await request(`/api/dashboard/stores/${selectedStore.value.id}`, {
      method: 'PUT',
      body: JSON.stringify(manageForm.value),
    })
    Object.assign(selectedStore.value, manageForm.value)
    await fetchStores()
    manageMsg.value = '保存成功'
    manageMsgType.value = 'success'
    setTimeout(() => { showManageModal.value = false; manageMsg.value = '' }, 1000)
  } catch (e) {
    manageMsg.value = '保存失败: ' + e.message
    manageMsgType.value = 'error'
  }
}

async function addStore() {
  if (!addForm.value.name.trim()) {
    addMsg.value = '请输入门店名称'
    addMsgType.value = 'error'
    return
  }
  try {
    const res = await request('/api/dashboard/stores', {
      method: 'POST',
      body: JSON.stringify(addForm.value),
    })
    stores.value.push({
      id: res.data?.id || Date.now(),
      ...addForm.value,
      status: 'open',
      revenue: '0',
      orders: 0,
      achievement: 0,
    })
    await fetchStores()
    addMsg.value = '添加成功'
    addMsgType.value = 'success'
    setTimeout(() => {
      showAddModal.value = false
      addMsg.value = ''
      addForm.value = { name: '', city: '', area: '', address: '', manager_name: '', seats: 0, staff_count: 0, rating: 4.5 }
    }, 1000)
  } catch (e) {
    addMsg.value = '添加失败: ' + e.message
    addMsgType.value = 'error'
  }
}

async function doBatchDelete() {
  if (!selectedCount.value) return
  batchDeleting.value = true
  try {
    await request('/api/dashboard/stores/batch-delete', {
      method: 'POST',
      body: JSON.stringify(selectedIds.value),
    })
    showBatchDeleteConfirm.value = false
    exitBatchMode()
    await fetchStores()
  } catch (e) {
    alert('批量删除失败: ' + e.message)
  } finally {
    batchDeleting.value = false
  }
}

onMounted(() => {
  fetchStores()
  window.addEventListener('aurasaas:data-imported', handleDataImported)
})

onUnmounted(() => {
  window.removeEventListener('aurasaas:data-imported', handleDataImported)
})
</script>
