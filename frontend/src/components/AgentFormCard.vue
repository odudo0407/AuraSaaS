<template>
  <div class="rounded-lg border border-hairline bg-white p-4">
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div>
        <div class="text-sm font-bold text-ink">{{ form.title }}</div>
        <p class="mt-1 text-xs leading-5 text-muted">{{ form.description }}</p>
      </div>
      <span class="w-fit rounded-full px-3 py-1 text-xs font-bold" :class="riskClass">
        {{ riskLabel }}
      </span>
    </div>

    <div v-if="confirmRequired" class="mt-4 rounded-lg border border-primary/30 bg-primary/5 p-3">
      <div class="text-sm font-bold text-primary">需要二次确认</div>
      <p class="mt-1 text-xs leading-5 text-body">{{ confirmSummary }}</p>
      <div class="mt-3 flex flex-wrap gap-2">
        <button @click="submit(true)" :disabled="submitting" class="h-9 rounded-lg bg-primary px-4 text-xs font-bold text-white disabled:opacity-50">
          确认执行
        </button>
        <button @click="confirmRequired = false" class="h-9 rounded-lg border border-hairline bg-white px-4 text-xs font-bold text-ink">
          返回修改
        </button>
      </div>
    </div>

    <div class="mt-4 overflow-x-auto">
      <table class="min-w-full table-fixed border-collapse text-left text-xs">
        <thead>
          <tr class="border-b border-hairline bg-[#fbfaf8] text-muted">
            <th v-for="field in form.fields" :key="field.key" class="min-w-140px px-3 py-2 font-bold">
              {{ field.label }}<span v-if="field.required" class="text-error-text"> *</span>
            </th>
            <th class="w-72px px-3 py-2 font-bold">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in rows" :key="row.__id" class="border-b border-hairline-soft align-top">
            <td v-for="field in form.fields" :key="field.key" class="px-3 py-2">
              <select
                v-if="field.type === 'store'"
                v-model="row[field.key]"
                class="h-9 w-full rounded-md border border-hairline bg-white px-2 text-xs text-ink outline-none focus:border-primary"
                :class="errorClass(rowIndex, field.key)"
              >
                <option value="">请选择</option>
                <option v-for="store in stores" :key="store.id" :value="store.id">{{ store.name }}</option>
              </select>
              <select
                v-else-if="field.type === 'select'"
                v-model="row[field.key]"
                class="h-9 w-full rounded-md border border-hairline bg-white px-2 text-xs text-ink outline-none focus:border-primary"
                :class="errorClass(rowIndex, field.key)"
              >
                <option value="">请选择</option>
                <option v-for="option in field.options || []" :key="option" :value="option">{{ optionLabel(field.key, option) }}</option>
              </select>
              <div v-else-if="field.type === 'product_search'" class="min-w-0">
                <input
                  v-if="isBulkProductTarget(field, row)"
                  :value="bulkProductLabel"
                  readonly
                  class="h-9 w-full rounded-md border border-hairline bg-surface-soft px-2 text-xs text-ink outline-none"
                  :class="errorClass(rowIndex, field.key)"
                />
                <div v-else>
                  <input
                    v-model="row[field.key]"
                    type="search"
                    placeholder="搜索商品名称..."
                    class="h-9 w-full rounded-md border border-hairline bg-white px-2 text-xs text-ink outline-none focus:border-primary"
                    :class="errorClass(rowIndex, field.key)"
                    @focus="searchProducts(row)"
                    @input="handleProductInput(row)"
                  />
                  <div v-if="productOptions[row.__id]?.length" class="mt-1 max-h-36 overflow-y-auto rounded-md border border-hairline bg-white shadow-sm">
                    <button
                      v-for="product in productOptions[row.__id]"
                      :key="product.id"
                      type="button"
                      class="flex w-full items-center justify-between gap-3 px-2 py-2 text-left text-xs text-ink hover:bg-surface-soft"
                      @click="selectProduct(row, product)"
                    >
                      <span class="font-bold">{{ product.sku_name }}</span>
                      <span class="shrink-0 text-muted">{{ product.category }}</span>
                    </button>
                  </div>
                </div>
              </div>
              <input
                v-else-if="isBulkProductTarget(field, row)"
                :value="bulkProductLabel"
                readonly
                class="h-9 w-full rounded-md border border-hairline bg-surface-soft px-2 text-xs text-ink outline-none"
                :class="errorClass(rowIndex, field.key)"
              />
              <input
                v-else
                v-model="row[field.key]"
                :type="inputType(field)"
                :min="field.min"
                class="h-9 w-full rounded-md border border-hairline bg-white px-2 text-xs text-ink outline-none focus:border-primary"
                :class="errorClass(rowIndex, field.key)"
              />
              <div v-if="fieldError(rowIndex, field.key)" class="mt-1 text-[11px] leading-4 text-error-text">
                {{ fieldError(rowIndex, field.key) }}
              </div>
            </td>
            <td class="px-3 py-2">
              <button @click="removeRow(rowIndex)" :disabled="rows.length === 1" class="h-9 rounded-md border border-hairline bg-white px-3 text-xs font-bold text-muted disabled:opacity-40">
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="resultMessage" class="mt-3 rounded-lg border border-hairline bg-[#fbfaf8] p-3 text-xs leading-5 text-body">
      {{ resultMessage }}
    </div>

    <div class="mt-4 flex flex-wrap gap-2">
      <button @click="addRow" class="h-9 rounded-lg border border-hairline bg-white px-4 text-xs font-bold text-ink">
        添加一行
      </button>
      <button @click="submit(false)" :disabled="submitting || confirmRequired" class="h-9 rounded-lg bg-ink px-4 text-xs font-bold text-white disabled:opacity-50">
        {{ submitting ? '提交中...' : (form.requires_confirmation ? '修改后重新校验' : '提交表格') }}
      </button>
      <button @click="$emit('cancelled')" class="h-9 rounded-lg border border-hairline bg-white px-4 text-xs font-bold text-muted">
        取消
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { request } from '../utils/request'

const props = defineProps({
  form: { type: Object, required: true },
  stores: { type: Array, default: () => [] },
})

const emit = defineEmits(['submitted', 'cancelled'])

const rows = ref((props.form.rows || [{}]).map(row => ({ __id: crypto.randomUUID(), ...row })))
const errors = ref([])
const submitting = ref(false)
const confirmRequired = ref(Boolean(props.form.requires_confirmation))
const confirmSummary = ref(initialConfirmSummary())
const resultMessage = ref('')
const bulkProductLabel = '全部商品'
const productOptions = ref({})

const riskLabel = computed(() => ({ low: '低风险', medium: '中风险', high: '高风险' }[props.form.risk_level] || '低风险'))
const riskClass = computed(() => ({
  low: 'bg-primary/8 text-primary',
  medium: 'bg-[#fff4d6] text-[#8a5a00]',
  high: 'bg-error-text/8 text-error-text',
}[props.form.risk_level] || 'bg-primary/8 text-primary'))

function inputType(field) {
  if (field.type === 'date') return 'date'
  if (field.type === 'number' || field.type === 'integer') return 'number'
  return 'text'
}

function initialConfirmSummary() {
  if (props.form.action === 'delete') return '这是高风险删除操作，点击确认执行后才会真正删除。'
  return '这是敏感操作，点击确认执行后才会写入系统。'
}

function isBulkProductTarget(field, row) {
  return field.key === 'target_product' && (row[field.key] === '__ALL_PRODUCTS__' || row[field.key] === bulkProductLabel)
}

async function searchProducts(row) {
  if (!row?.__id || isBulkProductTarget({ key: 'target_product' }, row)) return
  const params = new URLSearchParams()
  const keyword = row.target_product || ''
  if (keyword) params.set('search', keyword)
  if (row.store_id) params.set('store_id', row.store_id)
  params.set('limit', '8')
  try {
    const res = await request(`/api/sku/list?${params.toString()}`)
    productOptions.value = {
      ...productOptions.value,
      [row.__id]: res.data?.items || [],
    }
  } catch {
    productOptions.value = { ...productOptions.value, [row.__id]: [] }
  }
}

function handleProductInput(row) {
  confirmRequired.value = false
  searchProducts(row)
}

function selectProduct(row, product) {
  row.target_product = product.sku_name
  row.target_product_id = product.id
  productOptions.value = { ...productOptions.value, [row.__id]: [] }
  confirmRequired.value = false
}

function optionLabel(key, value) {
  const labels = {
    manager: '店长',
    staff: '员工',
    chef: '厨师',
    barista: '咖啡师',
    cashier: '收银员',
    active: '在职',
    leave: '请假',
    resigned: '离职',
    resign: '标记离职',
    delete: '永久删除',
  }
  return labels[value] || value
}

function addRow() {
  const base = {}
  for (const field of props.form.fields || []) base[field.key] = field.type === 'store' ? (rows.value[0]?.store_id || '') : ''
  rows.value.push({ __id: crypto.randomUUID(), ...base })
  confirmRequired.value = false
}

function removeRow(index) {
  if (rows.value.length === 1) return
  rows.value.splice(index, 1)
  confirmRequired.value = false
}

function cleanRows() {
  return rows.value.map(({ __id, ...row }) => {
    if (row.target_product === bulkProductLabel) row.target_product = '__ALL_PRODUCTS__'
    return row
  })
}

async function submit(confirm) {
  submitting.value = true
  resultMessage.value = ''
  try {
    const res = await request('/api/agent/forms/submit', {
      method: 'POST',
      body: JSON.stringify({ form_id: props.form.form_id, rows: cleanRows(), confirm }),
    })
    const data = res.data || {}
    if (data.status === 'validation_failed') {
      errors.value = data.errors || []
      resultMessage.value = res.message || '表格校验失败，请修正后再提交。'
      confirmRequired.value = false
      return
    }
    if (data.status === 'confirmation_required') {
      errors.value = []
      confirmRequired.value = true
      confirmSummary.value = data.summary || res.message
      return
    }
    errors.value = []
    confirmRequired.value = false
    resultMessage.value = `已完成 ${data.success_count || 0} 行，失败 ${data.failure_count || 0} 行。`
    emit('submitted', data)
  } catch (error) {
    resultMessage.value = error.message
  } finally {
    submitting.value = false
  }
}

function fieldError(rowIndex, key) {
  const item = errors.value.find(error => error.row_index === rowIndex)
  return item?.fields?.[key] || ''
}

function errorClass(rowIndex, key) {
  return fieldError(rowIndex, key) ? 'border-error-text bg-error-text/5' : ''
}
</script>
