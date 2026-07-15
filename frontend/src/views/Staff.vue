<template>
  <div class="p-4 md:p-8">
    <div class="mb-6 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
      <div>
        <h2 class="mb-1 text-lg font-semibold text-ink">人员管理</h2>
        <p class="text-sm text-muted">管理门店员工、角色、状态和基础联系信息</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <select v-model="filters.store_id" @change="fetchStaff" class="h-10 rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none">
          <option value="">全部门店</option>
          <option v-for="store in stores" :key="store.id" :value="store.id">{{ store.name }}</option>
        </select>
        <select v-model="filters.status" @change="fetchStaff" class="h-10 rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none">
          <option value="">全部状态</option>
          <option value="active">在职</option>
          <option value="leave">请假</option>
          <option value="resigned">离职</option>
        </select>
        <button @click="openAdd" class="h-10 rounded-lg bg-primary px-4 text-sm font-bold text-white hover:bg-primary-active">
          新增员工
        </button>
        <button @click="toggleBatchMode" class="h-10 rounded-lg bg-surface-soft px-4 text-sm font-bold text-ink hover:bg-hairline">
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
      <button @click="exitBatchMode" class="rounded-lg bg-surface-soft px-4 py-2 text-sm font-medium text-ink hover:bg-hairline">
        取消
      </button>
    </div>

    <div class="overflow-hidden rounded-lg border border-hairline bg-canvas">
      <div v-if="loading" class="p-10 text-center text-sm text-muted">加载人员数据...</div>
      <table v-else class="min-w-full table-fixed border-collapse text-left text-sm">
        <thead class="border-b border-hairline bg-[#fbfaf8] text-xs text-muted">
          <tr>
            <th v-if="isBatchMode" class="w-12 px-4 py-3 font-bold"></th>
            <th class="px-4 py-3 font-bold">姓名</th>
            <th class="px-4 py-3 font-bold">门店</th>
            <th class="px-4 py-3 font-bold">角色</th>
            <th class="px-4 py-3 font-bold">手机号</th>
            <th class="px-4 py-3 font-bold">状态</th>
            <th class="px-4 py-3 font-bold">薪资</th>
            <th class="px-4 py-3 font-bold">入职日期</th>
            <th class="w-160px px-4 py-3 font-bold">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="staff.length === 0">
            <td :colspan="isBatchMode ? 9 : 8" class="px-4 py-10 text-center text-sm text-muted">暂无人员数据</td>
          </tr>
          <tr v-for="person in staff" :key="person.id" class="border-b border-hairline-soft last:border-b-0">
            <td v-if="isBatchMode" class="px-4 py-3">
              <input type="checkbox" class="h-4 w-4 accent-primary" :checked="isSelected(person.id)" @change="toggleItem(person.id)" />
            </td>
            <td class="px-4 py-3 font-bold text-ink">{{ person.name }}</td>
            <td class="px-4 py-3 text-body">{{ storeName(person.store_id) }}</td>
            <td class="px-4 py-3 text-body">{{ roleLabel(person.role) }}</td>
            <td class="px-4 py-3 text-body">{{ person.phone || '-' }}</td>
            <td class="px-4 py-3">
              <span class="rounded-full px-2 py-1 text-xs font-bold" :class="statusClass(person.status)">
                {{ statusLabel(person.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-body">{{ person.salary ? `¥${person.salary}` : '-' }}</td>
            <td class="px-4 py-3 text-body">{{ person.hire_date || '-' }}</td>
            <td class="px-4 py-3">
              <div class="flex gap-2">
                <button v-if="!isBatchMode" @click="openEdit(person)" class="h-8 rounded-lg border border-hairline bg-white px-3 text-xs font-bold text-ink">编辑</button>
                <button v-if="!isBatchMode" @click="markResigned(person)" class="h-8 rounded-lg border border-hairline bg-white px-3 text-xs font-bold text-muted">离职</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Teleport to="body">
      <Transition name="fade">
        <div v-if="drawerOpen" class="fixed inset-0 z-200 flex justify-end bg-black/40">
          <div class="h-full w-full max-w-480px overflow-y-auto bg-white shadow-2xl">
            <div class="flex items-center justify-between border-b border-hairline px-6 py-4">
              <h3 class="text-base font-semibold text-ink">{{ editing ? '编辑员工' : '新增员工' }}</h3>
              <button @click="drawerOpen = false" class="h-8 w-8 rounded-full text-lg text-muted hover:bg-surface-soft">x</button>
            </div>
            <div class="space-y-4 px-6 py-5">
              <label class="block">
                <span class="mb-1.5 block text-sm text-muted">门店 *</span>
                <select v-model.number="form.store_id" class="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none">
                  <option v-for="store in stores" :key="store.id" :value="store.id">{{ store.name }}</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-sm text-muted">姓名 *</span>
                <input v-model="form.name" class="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-sm text-muted">手机号</span>
                <input v-model="form.phone" class="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-sm text-muted">角色</span>
                <select v-model="form.role" class="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none">
                  <option value="manager">店长</option>
                  <option value="staff">员工</option>
                  <option value="chef">厨师</option>
                  <option value="barista">咖啡师</option>
                  <option value="cashier">收银员</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-sm text-muted">状态</span>
                <select v-model="form.status" class="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none">
                  <option value="active">在职</option>
                  <option value="leave">请假</option>
                  <option value="resigned">离职</option>
                </select>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-sm text-muted">入职日期</span>
                <input v-model="form.hire_date" type="date" class="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-sm text-muted">薪资</span>
                <input v-model.number="form.salary" type="number" min="0" class="h-10 w-full rounded-lg border border-hairline bg-canvas px-3 text-sm text-ink outline-none" />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-sm text-muted">备注</span>
                <textarea v-model="form.notes" rows="3" class="w-full rounded-lg border border-hairline bg-canvas px-3 py-2 text-sm text-ink outline-none"></textarea>
              </label>
            </div>
            <div class="flex gap-3 border-t border-hairline px-6 py-4">
              <button @click="drawerOpen = false" class="h-10 flex-1 rounded-lg border border-hairline bg-white text-sm font-bold text-ink">取消</button>
              <button @click="saveStaff" :disabled="saving || !form.name || !form.store_id" class="h-10 flex-1 rounded-lg bg-primary text-sm font-bold text-white disabled:opacity-50">
                {{ saving ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <BatchDeleteConfirm
      :open="showBatchDeleteConfirm"
      :count="selectedCount"
      entity-name="人员"
      :loading="batchDeleting"
      @confirm="doBatchDelete"
      @cancel="showBatchDeleteConfirm = false"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import BatchDeleteConfirm from '../components/BatchDeleteConfirm.vue'
import { useBatchSelection } from '../composables/useBatchSelection'
import { request } from '../utils/request'

const stores = ref([])
const staff = ref([])
const loading = ref(false)
const saving = ref(false)
const drawerOpen = ref(false)
const editing = ref(false)
const filters = ref({ store_id: '', status: '' })
const form = ref(initForm())
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
} = useBatchSelection(staff)

function initForm() {
  return { id: null, store_id: '', name: '', phone: '', role: 'staff', hire_date: '', salary: 0, status: 'active', notes: '' }
}

async function fetchStores() {
  const res = await request('/api/dashboard/stores')
  stores.value = res.data || []
}

async function fetchStaff() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filters.value.store_id) params.set('store_id', filters.value.store_id)
    if (filters.value.status) params.set('status', filters.value.status)
    const res = await request(`/api/staff?${params.toString()}`)
    staff.value = res.data || []
  } finally {
    loading.value = false
  }
}

function storeName(id) {
  return stores.value.find(store => Number(store.id) === Number(id))?.name || `门店 ${id}`
}

function roleLabel(role) {
  return { manager: '店长', staff: '员工', chef: '厨师', barista: '咖啡师', cashier: '收银员' }[role] || role
}

function statusLabel(status) {
  return { active: '在职', leave: '请假', resigned: '离职' }[status] || status
}

function statusClass(status) {
  return {
    active: 'bg-primary/8 text-primary',
    leave: 'bg-[#fff4d6] text-[#8a5a00]',
    resigned: 'bg-muted/10 text-muted',
  }[status] || 'bg-muted/10 text-muted'
}

function openAdd() {
  editing.value = false
  form.value = initForm()
  form.value.store_id = stores.value[0]?.id || ''
  drawerOpen.value = true
}

function openEdit(person) {
  editing.value = true
  form.value = { ...person, hire_date: person.hire_date || '' }
  drawerOpen.value = true
}

async function saveStaff() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (!payload.hire_date) delete payload.hire_date
    if (editing.value && payload.id) {
      await request(`/api/staff/${payload.id}`, { method: 'PUT', body: JSON.stringify(payload) })
    } else {
      await request('/api/staff', { method: 'POST', body: JSON.stringify(payload) })
    }
    drawerOpen.value = false
    await fetchStaff()
  } finally {
    saving.value = false
  }
}

async function markResigned(person) {
  await request(`/api/staff/${person.id}`, { method: 'PUT', body: JSON.stringify({ status: 'resigned' }) })
  await fetchStaff()
}

async function doBatchDelete() {
  if (!selectedCount.value) return
  batchDeleting.value = true
  try {
    await request('/api/staff/batch-delete', {
      method: 'POST',
      body: JSON.stringify(selectedIds.value),
    })
    showBatchDeleteConfirm.value = false
    exitBatchMode()
    await fetchStaff()
  } catch (e) {
    alert('批量删除失败: ' + e.message)
  } finally {
    batchDeleting.value = false
  }
}

onMounted(async () => {
  await fetchStores()
  await fetchStaff()
})
</script>

<style scoped>
.fade-enter-active { animation: fadeIn 0.2s ease; }
.fade-leave-active { animation: fadeIn 0.15s ease reverse; }
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
