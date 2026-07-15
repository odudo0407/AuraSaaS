<template>
  <div class="p-4 md:p-8">
    <div class="flex flex-col justify-between gap-4 mb-6 xl:flex-row xl:items-center">
      <div>
        <h2 class="text-lg font-semibold text-ink mb-1">商品管理</h2>
        <p class="text-muted text-sm">管理所有 SKU，监控销售表现与成本</p>
      </div>
      <div class="flex flex-wrap gap-2 items-center">
        <StoreSelector @change="onStoreChange" />
        <div class="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-hairline bg-canvas px-3 py-2 sm:w-56 sm:flex-none">
          <span class="text-muted-soft text-sm">🔍</span>
          <input v-model="search" @input="fetchProducts" placeholder="搜索商品名称..."
            class="bg-transparent border-none outline-none text-sm text-ink flex-1" />
        </div>
        <select v-model="filterCategory" @change="fetchProducts"
          class="bg-canvas border border-hairline rounded-lg px-3 py-2 text-sm text-ink outline-none">
          <option value="">全部品类</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
        <button @click="openAddDrawer"
          class="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-active transition-colors cursor-pointer">
          + 添加商品
        </button>
        <button @click="toggleBatchMode"
          class="bg-surface-soft text-ink px-4 py-2 rounded-lg text-sm font-medium hover:bg-hairline transition-colors cursor-pointer">
          {{ isBatchMode ? '退出批量删除' : '批量删除' }}
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
      <button @click="exitBatchMode"
        class="rounded-lg bg-surface-soft px-4 py-2 text-sm font-medium text-ink hover:bg-hairline">
        取消
      </button>
    </div>

    <!-- Category tabs -->
    <div class="flex gap-2 mb-6 flex-wrap">
      <span @click="filterCategory = ''; fetchProducts()"
        class="px-4 py-2 rounded-full text-sm font-medium cursor-pointer transition-all"
        :class="filterCategory === '' ? 'bg-ink text-white' : 'bg-canvas border border-hairline text-muted hover:text-ink'">
        全部 ({{ allTotalCount || totalCount }})
      </span>
      <span v-for="c in categories" :key="c" @click="filterCategory = c; fetchProducts()"
        class="px-4 py-2 rounded-full text-sm font-medium cursor-pointer transition-all"
        :class="filterCategory === c ? 'bg-ink text-white' : 'bg-canvas border border-hairline text-muted hover:text-ink'">
        {{ c }}
      </span>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="text-center py-16">
      <div class="inline-block w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      <p class="text-muted text-sm mt-3">加载商品数据...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="products.length === 0" class="text-center py-16">
      <div class="text-4xl mb-3">📦</div>
      <p class="text-muted text-sm">暂无商品数据</p>
      <button @click="openAddDrawer" class="text-primary text-sm font-medium mt-2 hover:underline cursor-pointer">添加第一个商品</button>
    </div>

    <!-- Products grid -->
    <div v-else class="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
      <div v-for="p in products" :key="p.id"
        class="bg-canvas border border-hairline rounded-xl p-5 hover:shadow-md transition-shadow group">
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center gap-3">
            <input v-if="isBatchMode" type="checkbox" class="h-4 w-4 shrink-0 accent-primary" :checked="isSelected(p.id)" @change="toggleItem(p.id)" />
            <div class="w-14 h-14 rounded-xl bg-surface-soft flex items-center justify-center overflow-hidden shrink-0">
              <img v-if="p.image_url" :src="p.image_url" class="w-full h-full object-cover" @error="$event.target.style.display='none'" />
              <span v-else class="text-2xl">{{ getIcon(p.category) }}</span>
            </div>
            <div>
              <div class="text-sm font-semibold text-ink">{{ p.sku_name }}</div>
              <span class="text-xs px-2 py-0.5 rounded-full bg-surface-soft text-muted">{{ p.category }}</span>
            </div>
          </div>
          <span class="text-xs px-2 py-0.5 rounded-full font-medium"
            :class="p.gross_margin >= 60 ? 'bg-primary/8 text-primary' : p.gross_margin >= 40 ? 'bg-muted/8 text-muted' : 'bg-error-text/8 text-error-text'">
            {{ p.gross_margin >= 60 ? '高毛利' : p.gross_margin >= 40 ? '中毛利' : '低毛利' }}
          </span>
        </div>

        <div class="grid grid-cols-3 gap-3 mb-3 min-w-0">
          <div><div class="text-base font-bold text-ink">{{ p.sales_count || 0 }}</div><div class="text-xs text-muted-soft">7日销量</div></div>
          <div><div class="text-base font-bold text-ink">¥{{ p.price || 0 }}</div><div class="text-xs text-muted-soft">单价</div></div>
          <div><div class="text-base font-bold text-ink">{{ p.gross_margin || 0 }}%</div><div class="text-xs text-muted-soft">毛利率</div></div>
        </div>

        <!-- Margin bar -->
        <div class="flex items-center gap-2 mb-3">
          <div class="flex-1 h-1.5 bg-surface-soft rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all" :style="{ width: (p.gross_margin || 0) + '%', background: (p.gross_margin || 0) >= 60 ? '#ff385c' : (p.gross_margin || 0) >= 40 ? '#6a6a6a' : '#c13515' }"></div>
          </div>
          <span class="text-xs text-muted-soft">¥{{ formatNum(p.revenue) }}</span>
        </div>

        <div v-if="!isBatchMode" class="flex gap-2">
          <button @click="openEditDrawer(p)"
            class="flex-1 bg-surface-soft text-ink px-3 py-2 rounded-lg text-xs font-medium cursor-pointer hover:bg-hairline transition-colors">
            编辑
          </button>
          <button @click="confirmDelete(p)"
            class="flex-1 bg-error-text/8 text-error-text px-3 py-2 rounded-lg text-xs font-medium cursor-pointer hover:bg-error-text/15 transition-colors">
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- ============ Floating Drawer (Add / Edit) ============ -->
    <Teleport to="body">
      <Transition name="drawer-slide">
        <div v-if="drawerOpen" class="fixed inset-0 z-200 flex justify-end">
          <!-- Backdrop -->
          <div class="absolute inset-0 bg-black/40" @click="closeDrawer"></div>

          <!-- Drawer sheet -->
          <div class="relative w-full max-w-480px bg-white h-full overflow-y-auto shadow-2xl flex flex-col"
            style="animation: slideUp 0.3s ease">
            <!-- Header -->
            <div class="flex items-center justify-between px-6 py-4 border-b border-hairline-soft shrink-0">
              <h3 class="text-base font-semibold text-ink">{{ isEditing ? '编辑商品' : '添加商品' }}</h3>
              <button @click="closeDrawer"
                class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-soft text-muted hover:text-ink transition-colors text-lg leading-none">
                ×
              </button>
            </div>

            <!-- Form body -->
            <div class="flex-1 px-6 py-5 space-y-5 overflow-y-auto">
              <!-- SKU ID (read-only when editing) -->
              <div v-if="isEditing">
                <label class="text-sm text-muted block mb-1.5">SKU ID</label>
                <input :value="form.id" disabled
                  class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-muted-soft outline-none" />
              </div>

              <!-- Image upload -->
              <div>
                <label class="text-sm text-muted block mb-1.5">商品图片</label>
                <div class="flex items-center gap-4">
                  <div class="w-20 h-20 rounded-xl bg-surface-soft flex items-center justify-center overflow-hidden border-2 border-dashed"
                    :class="imagePreview ? 'border-primary' : 'border-hairline'">
                    <img v-if="imagePreview" :src="imagePreview" class="w-full h-full object-cover" />
                    <span v-else class="text-3xl text-muted-soft">📷</span>
                  </div>
                  <label class="bg-surface-soft text-ink px-4 py-2 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
                    {{ form.image_url || imagePreview ? '更换图片' : '选择图片' }}
                    <input type="file" accept="image/*" class="hidden" @change="onImageSelect" />
                  </label>
                  <button v-if="imagePreview" @click="clearImage"
                    class="text-xs text-muted hover:text-error-text transition-colors cursor-pointer">清除</button>
                </div>
              </div>

              <!-- Name -->
              <div>
                <label class="text-sm text-muted block mb-1.5">商品名称 <span class="text-error-text">*</span></label>
                <input v-model="form.sku_name" placeholder="输入商品名称"
                  class="w-full bg-canvas border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-primary transition-colors" />
              </div>

              <!-- Category picker -->
              <div>
                <label class="text-sm text-muted block mb-1.5">品类 <span class="text-error-text">*</span></label>
                <div class="flex gap-2 flex-wrap">
                  <button v-for="cat in PRESET_CATEGORIES" :key="cat"
                    @click="form.category = cat"
                    class="px-4 py-2 rounded-full text-sm font-medium cursor-pointer transition-all border-2"
                    :class="form.category === cat ? 'bg-primary/8 text-primary border-primary' : 'bg-canvas text-muted border-hairline hover:border-ink'">
                    {{ cat }}
                  </button>
                </div>
                <input v-if="form.category && !PRESET_CATEGORIES.includes(form.category)"
                  v-model="form.category" placeholder="自定义品类"
                  class="mt-2 w-full bg-canvas border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none" />
              </div>

              <!-- Price slider -->
              <div>
                <label class="text-sm text-muted block mb-1.5">单价 (¥)</label>
                <div class="flex items-center gap-4">
                  <input type="range" v-model.number="form.price" min="1" max="500" step="1"
                    class="flex-1 accent-primary h-2" />
                  <input type="number" v-model.number="form.price" min="1" max="99999"
                    class="w-24 bg-canvas border border-hairline rounded-lg px-3 py-2 text-sm text-ink text-center outline-none focus:border-primary transition-colors" />
                </div>
              </div>

              <!-- Cost -->
              <div>
                <label class="text-sm text-muted block mb-1.5">成本 (¥)</label>
                <input type="number" v-model.number="form.cost" min="0" max="99999" step="0.01"
                  class="w-full bg-canvas border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-primary transition-colors" />
              </div>

              <!-- Margin live calculation -->
              <div class="bg-primary/4 border border-primary/20 rounded-xl p-4">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-ink font-medium">毛利率</span>
                  <span class="text-lg font-bold" :class="computedMargin >= 60 ? 'text-primary' : computedMargin >= 40 ? 'text-ink' : 'text-error-text'">
                    {{ computedMargin }}%
                  </span>
                </div>
                <div class="mt-2 h-2 bg-surface-soft rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-300" :style="{ width: computedMargin + '%', background: computedMargin >= 60 ? '#ff385c' : computedMargin >= 40 ? '#6a6a6a' : '#c13515' }"></div>
                </div>
                <div class="mt-1 text-xs text-muted-soft">
                  利润: ¥{{ computedProfit.toFixed(2) }} / 件
                </div>
              </div>

              <!-- Sales count -->
              <div>
                <label class="text-sm text-muted block mb-1.5">销量</label>
                <input type="number" v-model.number="form.sales_count" min="0"
                  class="w-full bg-canvas border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-primary transition-colors" />
              </div>

              <!-- Store selector -->
              <div>
                <label class="text-sm text-muted block mb-1.5">所属门店</label>
                <select v-model.number="form.store_id"
                  class="w-full bg-canvas border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-primary transition-colors">
                  <option v-for="s in storeList" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
            </div>

            <!-- Footer actions -->
            <div class="px-6 py-4 border-t border-hairline-soft shrink-0 flex gap-3">
              <button @click="closeDrawer"
                class="flex-1 bg-surface-soft text-ink px-4 py-3 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
                取消
              </button>
              <button @click="saveProduct" :disabled="saving || !form.sku_name || !form.category"
                class="flex-1 bg-primary text-white px-4 py-3 rounded-lg text-sm font-medium cursor-pointer hover:bg-primary-active disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2">
                <span v-if="saving" class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                {{ saving ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Delete confirmation modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="deleteTarget" class="fixed inset-0 z-200 flex items-center justify-center bg-black/40">
          <div class="bg-white rounded-2xl p-6 w-90 shadow-xl">
            <div class="text-center mb-4">
              <span class="text-4xl">🗑</span>
            </div>
            <h3 class="text-base font-semibold text-ink mb-2 text-center">确认删除？</h3>
            <p class="text-sm text-muted mb-6 text-center">将永久删除商品「{{ deleteTarget.sku_name }}」，此操作不可撤销。</p>
            <div class="flex gap-3 justify-center">
              <button @click="deleteTarget = null"
                class="px-4 py-2 rounded-lg text-sm font-medium bg-surface-soft text-ink hover:bg-hairline transition-colors cursor-pointer">
                取消
              </button>
              <button @click="doDelete" :disabled="deleting"
                class="px-4 py-2 rounded-lg text-sm font-medium bg-error-text text-white hover:bg-red-700 transition-colors cursor-pointer disabled:opacity-50">
                {{ deleting ? '删除中...' : '确认删除' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
    <BatchDeleteConfirm
      :open="showBatchDeleteConfirm"
      :count="selectedCount"
      entity-name="商品"
      :loading="batchDeleting"
      @cancel="showBatchDeleteConfirm = false"
      @confirm="doBatchDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { request } from '../utils/request'
import StoreSelector from '../components/StoreSelector.vue'
import BatchDeleteConfirm from '../components/BatchDeleteConfirm.vue'
import { useBatchSelection } from '../composables/useBatchSelection'

const PRESET_CATEGORIES = ['热菜', '饮品', '甜品', '主食', '凉菜', '小吃', '汤品', '酒水', '其他']

const search = ref('')
const filterCategory = ref('')
const products = ref([])
const totalCount = ref(0)
const allTotalCount = ref(0)
const categoryCounts = ref([])
const categoryOrder = ref([])
const loading = ref(false)
const storeList = ref([])
const currentStoreId = ref(null)

// Drawer state
const drawerOpen = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const imagePreview = ref('')
const selectedFile = ref(null)

// Delete state
const deleteTarget = ref(null)
const deleting = ref(false)
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
} = useBatchSelection(products)

const form = ref(initForm())

function initForm() {
  return {
    id: null,
    store_id: 1,
    sku_name: '',
    category: '热菜',
    price: 38,
    cost: 12,
    sales_count: 0,
    image_url: '',
  }
}

const computedMargin = computed(() => {
  if (!form.value.price || form.value.price <= 0) return 0
  return Math.round(((form.value.price - (form.value.cost || 0)) / form.value.price) * 100)
})

const computedProfit = computed(() => {
  return (form.value.price || 0) - (form.value.cost || 0)
})

const categories = computed(() => categoryOrder.value.filter(Boolean))

function formatNum(n) {
  if (!n) return '0'
  return n >= 10000 ? (n / 10000).toFixed(1) + '万' : n.toLocaleString()
}

function getIcon(cat) {
  const map = { '热菜': '🦆', '饮品': '☕', '甜品': '🍰', '主食': '🍚', '凉菜': '🥒', '小吃': '🍟', '汤品': '🍲', '酒水': '🍺' }
  return map[cat] || '📦'
}

function syncCategoryCounts(counts = []) {
  categoryCounts.value = counts
  const seen = new Set(categoryOrder.value)
  counts.forEach(item => {
    const category = item?.category
    if (category && !seen.has(category)) {
      categoryOrder.value.push(category)
      seen.add(category)
    }
  })
}

function onStoreChange(storeId) {
  currentStoreId.value = storeId
  categoryOrder.value = []
  fetchProducts()
}

async function fetchStores() {
  try {
    const res = await request('/api/dashboard/stores')
    storeList.value = res.data || []
    if (storeList.value.length > 0) form.value.store_id = storeList.value[0].id
  } catch { storeList.value = [] }
}

async function fetchProducts() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (currentStoreId.value) params.set('store_id', currentStoreId.value)
    if (filterCategory.value) params.set('category', filterCategory.value)
    if (search.value) params.set('search', search.value)
    params.set('limit', '50')

    const res = await request(`/api/sku/list?${params.toString()}`)
    products.value = res.data?.items || []
    totalCount.value = res.data?.total || 0
    allTotalCount.value = res.data?.all_total ?? totalCount.value
    syncCategoryCounts(res.data?.category_counts || [])
  } catch {
    products.value = []
  } finally {
    loading.value = false
  }
}

// Drawer actions
function openAddDrawer() {
  isEditing.value = false
  form.value = initForm()
  if (storeList.value.length > 0) form.value.store_id = storeList.value[0].id
  imagePreview.value = ''
  selectedFile.value = null
  drawerOpen.value = true
}

function openEditDrawer(product) {
  isEditing.value = true
  form.value = {
    id: product.id,
    store_id: product.store_id || 1,
    sku_name: product.sku_name,
    category: product.category,
    price: product.price || 0,
    cost: product.cost || 0,
    sales_count: product.sales_count || 0,
    image_url: product.image_url || '',
  }
  imagePreview.value = product.image_url || ''
  selectedFile.value = null
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
  imagePreview.value = ''
  selectedFile.value = null
}

function onImageSelect(e) {
  const file = e.target.files[0]
  if (!file) return
  selectedFile.value = file
  const reader = new FileReader()
  reader.onload = (ev) => { imagePreview.value = ev.target.result }
  reader.readAsDataURL(file)
  e.target.value = ''
}

function clearImage() {
  imagePreview.value = ''
  selectedFile.value = null
  form.value.image_url = ''
}

async function saveProduct() {
  if (!form.value.sku_name || !form.value.category) return
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('store_id', form.value.store_id)
    fd.append('sku_name', form.value.sku_name)
    fd.append('category', form.value.category)
    fd.append('price', form.value.price)
    fd.append('cost', form.value.cost || 0)
    fd.append('sales_count', form.value.sales_count || 0)
    if (selectedFile.value) {
      fd.append('image', selectedFile.value)
    }

    if (isEditing.value && form.value.id) {
      await request(`/api/sku/update/${form.value.id}`, { method: 'PUT', body: fd })
    } else {
      await request('/api/sku/add', { method: 'POST', body: fd })
    }
    closeDrawer()
    await fetchProducts()
  } catch (err) {
    alert(`保存失败: ${err.message}`)
  } finally {
    saving.value = false
  }
}

// Delete actions
function confirmDelete(product) {
  deleteTarget.value = product
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    const deleted = deleteTarget.value
    await request(`/api/sku/delete/${deleted.id}`, { method: 'DELETE' })
    products.value = products.value.filter(p => p.id !== deleted.id)
    totalCount.value = Math.max(0, totalCount.value - 1)
    allTotalCount.value = Math.max(0, allTotalCount.value - 1)
    categoryCounts.value = categoryCounts.value.map(item => {
      if (item.category !== deleted.category) return item
      return { ...item, count: Math.max(0, (item.count || 0) - 1) }
    })
    deleteTarget.value = null
  } catch (err) {
    alert(`删除失败: ${err.message}`)
  } finally {
    deleting.value = false
  }
}

async function doBatchDelete() {
  if (selectedCount.value === 0) return
  batchDeleting.value = true
  try {
    await request('/api/sku/batch-delete', { method: 'POST', body: JSON.stringify(selectedIds.value) })
    showBatchDeleteConfirm.value = false
    exitBatchMode()
    await fetchProducts()
  } catch (err) {
    alert(`批量删除失败: ${err.message}`)
  } finally {
    batchDeleting.value = false
  }
}

onMounted(async () => {
  await fetchStores()
  if (storeList.value.length > 0) form.value.store_id = storeList.value[0].id
  await fetchProducts()
})
</script>

<style scoped>
.fade-enter-active { animation: fadeIn 0.2s ease; }
.fade-leave-active { animation: fadeIn 0.15s ease reverse; }
.drawer-slide-enter-active { animation: fadeIn 0.25s ease; }
.drawer-slide-leave-active { animation: fadeIn 0.2s ease reverse; }
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes slideUp {
  from { transform: translateY(10px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
.animate-spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
