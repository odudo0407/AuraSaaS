<template>
  <div class="max-w-900px p-4 md:p-8">
    <div class="mb-6">
      <h2 class="text-lg font-semibold text-ink mb-1">系统设置</h2>
      <p class="text-muted text-sm">管理账户、AI 模型配置及系统偏好</p>
    </div>

    <div class="space-y-6">
      <!-- Profile -->
      <div class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="text-sm font-semibold text-ink mb-4">个人信息</div>
        <div class="flex items-center gap-4 mb-6">
          <!-- Clickable avatar -->
          <div class="relative group cursor-pointer" @click="triggerAvatarUpload" title="点击更换头像">
            <div v-if="displayAvatar" class="w-16 h-16 rounded-full overflow-hidden border-2 border-hairline group-hover:border-primary transition-colors">
              <img :src="displayAvatar" class="w-full h-full object-cover" @error="onAvatarError" />
            </div>
            <div v-else class="w-16 h-16 rounded-full bg-ink flex items-center justify-center text-white text-xl font-bold group-hover:bg-primary transition-colors">
              {{ auth.user?.username?.[0]?.toUpperCase() || 'U' }}
            </div>
            <!-- Hover overlay -->
            <div class="absolute inset-0 rounded-full bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <span class="text-white text-xs font-medium">📷</span>
            </div>
            <input ref="avatarInput" type="file" accept="image/*" class="hidden" @change="onAvatarFileSelected" />
          </div>
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <input v-if="editingName" ref="nameInput" v-model="editName" @keydown.enter="saveName" @blur="saveName"
                class="bg-canvas border border-primary rounded-lg px-3 py-1 text-base font-medium text-ink outline-none" />
              <div v-else class="text-base font-medium text-ink">{{ auth.user?.username || '未登录' }}</div>
              <button @click="startEditName"
                class="text-xs text-muted-soft hover:text-primary transition-colors cursor-pointer">
                ✏️
              </button>
            </div>
            <div class="text-sm text-muted">{{ auth.user?.email || '' }}</div>
            <p v-if="avatarMsg" class="text-xs mt-2" :class="avatarMsgType === 'error' ? 'text-error-text' : 'text-primary'">{{ avatarMsg }}</p>
          </div>
        </div>
      </div>

      <!-- AI Model Config -->
      <div class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="text-sm font-semibold text-ink mb-4">AI 模型配置</div>
        <div class="space-y-4">
          <div>
            <label class="text-sm text-muted block mb-1.5">DeepSeek API Key</label>
            <div class="flex gap-2">
              <input :type="showKey ? 'text' : 'password'" v-model="apiKey"
                class="flex-1 bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors"
                placeholder="sk-..." />
              <button @click="showKey = !showKey"
                class="bg-surface-soft text-muted px-4 py-2.5 rounded-lg text-sm cursor-pointer hover:text-ink transition-colors">
                {{ showKey ? '隐藏' : '显示' }}
              </button>
            </div>
          </div>
          <div>
            <label class="text-sm text-muted block mb-1.5">API Base URL</label>
            <input v-model="baseUrl"
              class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors"
              placeholder="https://api.deepseek.com" />
          </div>
          <div>
            <label class="text-sm text-muted block mb-1.5">模型选择</label>
            <select v-model="model"
              class="w-full bg-surface-soft border border-hairline rounded-lg px-4 py-2.5 text-sm text-ink outline-none focus:border-ink transition-colors">
              <option value="deepseek-chat">DeepSeek-V3 — 性价比高，适合日常对话与数据分析</option>
              <option value="deepseek-reasoner">DeepSeek-R1 — 推理增强，适合复杂诊断与策略规划</option>
              <option value="deepseek-v4">DeepSeek-V4 — 最新旗舰，综合能力强</option>
              <option value="deepseek-v4-pro">DeepSeek-V4 Pro — 顶级性能，适合高精度任务</option>
            </select>
            <p class="text-xs text-muted-soft mt-2 leading-relaxed">
              💡 <span class="font-medium text-ink">指引：</span>
              <span v-if="model === 'deepseek-chat'">V3 响应快速、成本低，推荐用于常规分析和文案生成。</span>
              <span v-else-if="model === 'deepseek-reasoner'">R1 会展示详细推理过程（&lt;think&gt;），适合深度诊断和策略制定，但响应较慢。</span>
              <span v-else-if="model === 'deepseek-v4'">V4 综合性能更强，推理与生成兼顾。</span>
              <span v-else>V4 Pro 是当下最强模型，适合对精度要求极高的场景。</span>
            </p>
          </div>
          <button @click="saveConfig"
            class="bg-primary text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-primary-active transition-colors cursor-pointer">
            保存配置
          </button>
          <p v-if="configMsg" class="text-xs" :class="configMsgType === 'error' ? 'text-error-text' : 'text-primary'">{{ configMsg }}</p>
        </div>
      </div>

      <!-- Notification settings -->
      <div class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="text-sm font-semibold text-ink mb-4">通知设置</div>
        <div class="space-y-4">
          <div v-for="setting in notifications" :key="setting.label"
            class="flex items-center justify-between py-2">
            <div>
              <div class="text-sm font-medium text-ink">{{ setting.label }}</div>
              <div class="text-xs text-muted-soft">{{ setting.desc }}</div>
            </div>
            <div class="w-10 h-6 rounded-full cursor-pointer transition-colors relative"
              :class="setting.enabled ? 'bg-primary' : 'bg-hairline'"
              @click="setting.enabled = !setting.enabled">
              <div class="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform"
                :style="{ left: setting.enabled ? '18px' : '2px' }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Smart data import -->
      <div class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="grid gap-3 md:grid-cols-[180px_1fr_auto] md:items-start">
          <select
            v-model="selectedImportType"
            class="h-10 rounded-lg border border-hairline bg-surface-soft px-3 text-sm text-ink outline-none focus:border-ink"
          >
            <option v-for="option in importOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
          <div>
            <div class="text-sm font-semibold text-ink">智能清洗导入</div>
            <p class="mt-1 text-xs leading-5 text-muted">上传 CSV 或 Excel，系统会先清洗校验并返回导入报告。</p>
          </div>
          <button
            @click="triggerSmartImportUpload"
            :disabled="smartImporting"
            class="h-10 rounded-lg bg-ink px-4 text-sm font-medium text-white transition-colors hover:bg-primary disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ smartImporting ? '清洗中...' : '上传并清洗' }}
          </button>
          <input ref="smartImportFileInput" type="file" accept=".csv,.xlsx,.xls,.xlsm" class="hidden" @change="onSmartImportFile" />
        </div>
        <p v-if="smartImportStatus" class="mt-3 text-sm" :class="smartImportMsgType === 'error' ? 'text-error-text' : 'text-muted'">{{ smartImportStatus }}</p>
        <div v-if="smartImportReport" class="mt-4 rounded-lg border border-hairline bg-surface-soft p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div class="text-sm font-semibold text-ink">清洗报告</div>
              <div class="mt-1 text-xs text-muted">{{ smartImportFileName }}</div>
            </div>
            <div class="text-xs text-muted">目标表: {{ smartImportStats?.target_table || '-' }}</div>
          </div>
          <div class="mt-4 grid gap-2 sm:grid-cols-5">
            <div v-for="item in smartImportSummary" :key="item.label" class="rounded-md border border-hairline bg-canvas p-3">
              <div class="text-[11px] text-muted">{{ item.label }}</div>
              <div class="mt-1 text-lg font-semibold text-ink">{{ item.value }}</div>
            </div>
          </div>
          <div v-if="smartImportReport.warnings?.length" class="mt-4">
            <div class="text-xs font-semibold text-ink">Warnings</div>
            <ul class="mt-2 space-y-1 text-xs leading-5 text-muted">
              <li v-for="(warning, index) in smartImportReport.warnings.slice(0, 5)" :key="`warning-${index}`">
                Row {{ warning.row }} · {{ warning.field }} · {{ warning.message }}
              </li>
            </ul>
          </div>
          <div v-if="smartImportReport.errors?.length" class="mt-4">
            <div class="text-xs font-semibold text-error-text">Errors</div>
            <ul class="mt-2 space-y-1 text-xs leading-5 text-error-text">
              <li v-for="(error, index) in smartImportReport.errors.slice(0, 8)" :key="`error-${index}`">
                Row {{ error.row }} · {{ error.field }} · {{ error.message }}
              </li>
            </ul>
          </div>
          <div v-if="smartPreviewRows.length" class="mt-4 overflow-x-auto">
            <div class="mb-2 text-xs font-semibold text-ink">Preview rows</div>
            <table class="min-w-full border-collapse text-xs">
              <thead>
                <tr>
                  <th v-for="key in smartPreviewKeys" :key="key" class="border border-hairline bg-canvas px-2 py-1 text-left font-semibold text-muted">{{ key }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in smartPreviewRows" :key="rowIndex">
                  <td v-for="key in smartPreviewKeys" :key="key" class="border border-hairline bg-white px-2 py-1 text-muted">{{ row[key] ?? '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Data import -->
      <div v-if="false" class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="text-sm font-semibold text-ink mb-4">数据导入</div>
        <div class="grid gap-3 md:grid-cols-[180px_1fr_auto] md:items-center">
          <select
            v-model="selectedImportType"
            class="h-11 rounded-lg border border-hairline bg-surface-soft px-3 text-sm text-ink outline-none focus:border-ink"
          >
            <option v-for="option in importOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
          <div class="flex h-11 min-w-0 items-center rounded-lg border border-hairline bg-surface-soft px-4 text-sm text-muted">
            <span class="truncate">{{ importFileName || '请上传文件' }}</span>
          </div>
          <button
            @click="triggerImportUpload"
            :disabled="importing"
            class="h-11 rounded-lg bg-primary px-4 text-sm font-medium text-white transition-colors hover:bg-primary-active disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ importing ? '上传中...' : '上传Excel文件' }}
          </button>
          <input ref="importFileInput" type="file" accept=".xlsx,.xlsm,.csv" class="hidden" @change="onImportFile" />
        </div>
        <button @click="downloadTemplate"
          class="mt-3 bg-surface-soft text-ink px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
          下载模板
        </button>
        <p v-if="importMsg" class="text-sm mt-3" :class="importMsgType === 'error' ? 'text-error-text' : 'text-muted'">{{ importMsg }}</p>
      </div>

      <div v-if="false" class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="text-sm font-semibold text-ink mb-4">数据导入</div>
        <p class="text-xs text-muted-soft mb-2">上传 CSV 文件导入数据，系统根据文件名自动识别类型：</p>
        <div class="text-xs text-muted-soft mb-4 space-y-1">
          <div>• 文件名含 <span class="font-medium text-ink">store</span> 或 <span class="font-medium text-ink">门店</span> → 导入门店</div>
          <div>• 文件名含 <span class="font-medium text-ink">sku</span> 或 <span class="font-medium text-ink">商品</span> → 导入商品</div>
          <div>• 文件名含 <span class="font-medium text-ink">revenue</span> 或 <span class="font-medium text-ink">营收</span> → 导入经营数据</div>
          <div>• 文件名含 <span class="font-medium text-ink">campaign</span> 或 <span class="font-medium text-ink">活动</span> → 导入营销活动</div>
        </div>
        <div class="flex flex-wrap gap-3 items-center">
          <label class="bg-primary text-white px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-primary-active transition-colors">
            选择文件上传
            <input type="file" accept=".csv" class="hidden" @change="onImportFile" />
          </label>
          <button @click="downloadTemplate"
            class="bg-surface-soft text-ink px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
            下载模板
          </button>
          <span v-if="importFileName" class="text-sm text-ink">{{ importFileName }}</span>
        </div>
        <p v-if="importMsg" class="text-sm mt-3" :class="importMsgType === 'error' ? 'text-error-text' : 'text-muted'">{{ importMsg }}</p>
      </div>

      <!-- Data management -->
      <div class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="text-sm font-semibold text-ink mb-4">数据管理</div>
        <div class="flex flex-wrap gap-3">
          <button @click="exportAllData"
            class="bg-surface-soft text-ink px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
            导出全部数据
          </button>
          <button @click="showResetConfirm = true"
            class="bg-surface-soft text-ink px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
            重新生成 Demo 数据
          </button>
          <button @click="showClearConfirm = true"
            class="bg-error-text/8 text-error-text px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-error-text/15 transition-colors">
            清空数据库
          </button>
        </div>
        <p v-if="dataMsg" class="text-sm mt-3 text-muted">{{ dataMsg }}</p>
      </div>


      <!-- Knowledge management -->
      <div class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="flex flex-wrap items-start justify-between gap-3 mb-2">
          <div>
            <div class="text-sm font-semibold text-ink">知识库管理</div>
            <p class="mt-1 text-xs leading-5 text-muted-soft">上传商家自己的 SOP、活动方案、门店制度或处理规范，AI 会在经营诊断和策略建议中优先引用这些私有知识。</p>
          </div>
          <button
            @click="triggerKnowledgeUpload"
            :disabled="knowledgeUploading"
            class="h-10 rounded-lg bg-primary px-4 text-sm font-medium text-white transition-colors hover:bg-primary-active disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ knowledgeUploading ? '上传中...' : '上传知识库' }}
          </button>
          <input ref="knowledgeFileInput" type="file" accept=".pdf,.docx,.txt,.md" class="hidden" @change="onKnowledgeFile" />
        </div>
        <div class="mt-3 text-xs leading-5 text-muted">
          支持 PDF、Word、TXT、Markdown。文件仅用于当前商家的私有经营问答，不会进入公共 SOP 知识库。
        </div>
        <p v-if="knowledgeMsg" class="mt-3 text-sm" :class="knowledgeMsgType === 'error' ? 'text-error-text' : 'text-muted'">{{ knowledgeMsg }}</p>
        <div class="mt-4 rounded-lg border border-hairline bg-surface-soft">
          <div class="flex items-center justify-between border-b border-hairline px-4 py-3">
            <div class="text-xs font-semibold text-ink">已上传知识库</div>
            <button @click="loadKnowledgeDocs" :disabled="knowledgeLoading" class="text-xs text-muted hover:text-ink disabled:opacity-60">
              {{ knowledgeLoading ? '刷新中...' : '刷新' }}
            </button>
          </div>
          <div v-if="knowledgeDocs.length" class="divide-y divide-hairline">
            <div v-for="doc in knowledgeDocs" :key="doc.id" class="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div class="min-w-0">
                <div class="truncate text-sm font-medium text-ink">{{ doc.file_name }}</div>
                <div class="mt-1 text-xs text-muted">{{ doc.file_type }} · {{ formatFileSize(doc.file_size) }} · {{ doc.chunk_count }} 个切片 · {{ doc.status }}</div>
              </div>
              <button
                @click="deleteKnowledgeDoc(doc)"
                :disabled="knowledgeDeletingId === doc.id"
                class="rounded-lg bg-error-text/8 px-3 py-2 text-xs font-medium text-error-text transition-colors hover:bg-error-text/15 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {{ knowledgeDeletingId === doc.id ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
          <div v-else class="px-4 py-5 text-sm text-muted">还没有上传私有知识库文件。</div>
        </div>
      </div>
      <!-- Account actions -->
      <div class="bg-canvas border border-hairline rounded-xl p-6">
        <div class="text-sm font-semibold text-ink mb-4">账号操作</div>
        <div class="flex flex-wrap gap-3">
          <button @click="handleLogout"
            class="bg-surface-soft text-ink px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-hairline transition-colors">
            退出登录
          </button>
          <button @click="handleDeleteAccount"
            class="bg-error-text/8 text-error-text px-4 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-error-text/15 transition-colors">
            注销账号
          </button>
        </div>
        <p v-if="accountMsg" class="text-sm mt-3" :class="accountMsgType === 'error' ? 'text-error-text' : 'text-muted'">
          {{ accountMsg }}
        </p>
      </div>
    </div>
  </div>

  <!-- Delete confirmation modal -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showDeleteConfirm" class="fixed inset-0 z-100 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-2xl p-6 w-90 shadow-xl">
          <h3 class="text-base font-semibold text-ink mb-2">确认注销账号？</h3>
          <p class="text-sm text-muted mb-6">此操作不可撤销，您的所有数据将被永久删除。</p>
          <div class="flex gap-3 justify-end">
            <button @click="showDeleteConfirm = false"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-surface-soft text-ink hover:bg-hairline transition-colors cursor-pointer">
              取消
            </button>
            <button @click="confirmDelete" :disabled="deleting"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors cursor-pointer disabled:opacity-50">
              {{ deleting ? '注销中...' : '确认注销' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Reset/Clear confirmation modals -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showResetConfirm" class="fixed inset-0 z-100 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-2xl p-6 w-90 shadow-xl">
          <h3 class="text-base font-semibold text-ink mb-2">重新生成 Demo 数据？</h3>
          <p class="text-sm text-muted mb-6">这将清除现有数据并重新生成模拟数据。</p>
          <div class="flex gap-3 justify-end">
            <button @click="showResetConfirm = false"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-surface-soft text-ink hover:bg-hairline transition-colors cursor-pointer">
              取消
            </button>
            <button @click="regenerateMock"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-active transition-colors cursor-pointer">
              确认重新生成
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showClearConfirm" class="fixed inset-0 z-100 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-2xl p-6 w-90 shadow-xl">
          <h3 class="text-base font-semibold text-ink mb-2">清空数据库？</h3>
          <p class="text-sm text-muted mb-6">此操作将删除所有数据并重新初始化，不可撤销。</p>
          <div class="flex gap-3 justify-end">
            <button @click="showClearConfirm = false"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-surface-soft text-ink hover:bg-hairline transition-colors cursor-pointer">
              取消
            </button>
            <button @click="clearDatabase"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors cursor-pointer">
              确认清空
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useUserProfileStore } from '../stores/userProfile'
import { request, streamSSE } from '../utils/request'

const router = useRouter()
const auth = useAuthStore()
const profile = useUserProfileStore()

const showKey = ref(false)
const apiKey = ref(localStorage.getItem('aura_apiKey') || '')
const baseUrl = ref(localStorage.getItem('aura_baseUrl') || 'https://api.deepseek.com')
const model = ref(profile.selectedModel || 'deepseek-chat')

const showDeleteConfirm = ref(false)
const showResetConfirm = ref(false)
const showClearConfirm = ref(false)
const deleting = ref(false)
const accountMsg = ref('')
const accountMsgType = ref('')
const dataMsg = ref('')
const importMsg = ref('')
const importMsgType = ref('')
const importFileName = ref('')
const importFileInput = ref(null)
const selectedImportType = ref('stores')
const importing = ref(false)
const smartImporting = ref(false)
const smartImportFileName = ref('')
const smartImportFileInput = ref(null)
const smartImportStatus = ref('')
const smartImportMsgType = ref('')
const smartImportReport = ref(null)
const smartImportStats = ref(null)
const smartPreviewRows = ref([])
const knowledgeFileInput = ref(null)
const knowledgeUploading = ref(false)
const knowledgeLoading = ref(false)
const knowledgeDeletingId = ref(null)
const knowledgeDocs = ref([])
const knowledgeMsg = ref('')
const knowledgeMsgType = ref('')
const tenantId = computed(() => String(auth.user?.tenant_id || localStorage.getItem('aura_tenant_id') || '1'))
const smartPreviewKeys = computed(() => {
  const first = smartPreviewRows.value[0]
  return first ? Object.keys(first) : []
})
const smartImportSummary = computed(() => {
  const report = smartImportReport.value || {}
  return [
    { label: '总行数', value: report.total_rows ?? 0 },
    { label: '可导入', value: report.valid_rows ?? 0 },
    { label: '跳过', value: report.skipped_rows ?? 0 },
    { label: '修正', value: report.fixed_cells ?? 0 },
    { label: '重复', value: report.duplicate_rows ?? 0 },
  ]
})
const importOptions = [
  { value: 'stores', label: '门店' },
  { value: 'products', label: '商品' },
  { value: 'campaigns', label: '营销' },
  { value: 'metrics', label: '营收' },
  { value: 'staff', label: '店员' },
]
const configMsg = ref('')
const configMsgType = ref('')
const avatarMsg = ref('')
const avatarMsgType = ref('')

// Avatar upload
const avatarInput = ref(null)
const editingName = ref(false)
const editName = ref('')
const nameInput = ref(null)

const displayAvatar = computed(() => {
  return profile.avatarUrl || auth.user?.avatar_url || ''
})

function onAvatarError() {
  profile.setAvatar('')
}

function triggerAvatarUpload() {
  avatarInput.value?.click()
}

async function onAvatarFileSelected(e) {
  const file = e.target.files[0]
  if (!file) return
  avatarMsg.value = '上传中...'
  avatarMsgType.value = ''
  try {
    await profile.uploadAvatar(file)
    avatarMsg.value = '头像已更新'
    avatarMsgType.value = 'success'
    setTimeout(() => { avatarMsg.value = '' }, 2000)
  } catch (err) {
    avatarMsg.value = '上传失败: ' + err.message
    avatarMsgType.value = 'error'
  }
  e.target.value = ''
}

function startEditName() {
  editName.value = auth.user?.username || ''
  editingName.value = true
  nextTick(() => nameInput.value?.focus())
}

async function saveName() {
  editingName.value = false
  if (!editName.value.trim() || editName.value.trim() === auth.user?.username) return
  try {
    await profile.updateProfile({ username: editName.value.trim() })
    auth.user.username = editName.value.trim()
    localStorage.setItem('user', JSON.stringify(auth.user))
    avatarMsg.value = '用户名已更新'
    avatarMsgType.value = 'success'
    setTimeout(() => { avatarMsg.value = '' }, 2000)
  } catch (err) {
    avatarMsg.value = '更新失败: ' + err.message
    avatarMsgType.value = 'error'
  }
}

// Model config
function saveConfig() {
  localStorage.setItem('aura_apiKey', apiKey.value)
  localStorage.setItem('aura_baseUrl', baseUrl.value)
  localStorage.setItem('aura_model', model.value)
  profile.setModel(model.value)
  configMsg.value = '配置已保存'
  configMsgType.value = 'success'
  setTimeout(() => { configMsg.value = '' }, 2000)
}

// File import
function triggerImportUpload() {
  importFileInput.value?.click()
}

function triggerSmartImportUpload() {
  smartImportFileInput.value?.click()
}

async function onSmartImportFile(e) {
  const file = e.target.files[0]
  if (!file) return

  smartImportFileName.value = file.name
  smartImporting.value = true
  smartImportStatus.value = '正在上传并清洗...'
  smartImportMsgType.value = ''
  smartImportReport.value = null
  smartImportStats.value = null
  smartPreviewRows.value = []

  const fd = new FormData()
  fd.append('file', file)
  fd.append('import_type', selectedImportType.value)

  try {
    for await (const event of streamSSE('/api/agent/import-data', { method: 'POST', body: fd })) {
      if (event.type === 'error') {
        throw new Error(event.content || '智能清洗导入失败')
      }
      if (event.content) {
        smartImportStatus.value = event.content
      }
      if (event.cleaning_report) {
        smartImportReport.value = event.cleaning_report
      }
      if (event.preview_rows) {
        smartPreviewRows.value = event.preview_rows
      }
      if (event.stats) {
        smartImportStats.value = event.stats
        smartImportReport.value = event.stats.cleaning_report || smartImportReport.value
      }
    }
    smartImportMsgType.value = 'success'
    smartImportStatus.value = smartImportStats.value
      ? `导入完成：成功 ${smartImportStats.value.imported || 0} 行，跳过 ${smartImportStats.value.skipped || 0} 行`
      : '清洗导入完成'
    window.dispatchEvent(new CustomEvent('aurasaas:data-imported', {
      detail: { importType: smartImportStats.value?.target_table || 'smart', imported: smartImportStats.value?.imported || 0, at: Date.now() },
    }))
  } catch (err) {
    smartImportStatus.value = '智能清洗导入失败: ' + err.message
    smartImportMsgType.value = 'error'
  } finally {
    smartImporting.value = false
    e.target.value = ''
  }
}

async function onImportFile(e) {
  const file = e.target.files[0]
  if (!file) return
  importFileName.value = file.name
  importing.value = true
  importMsg.value = '上传中...'
  importMsgType.value = ''
  const fd = new FormData()
  fd.append('import_type', selectedImportType.value)
  fd.append('file', file)
  try {
    const res = await request('/api/import/upload', { method: 'POST', body: fd })
    importing.value = false
    importMsg.value = res.message || '导入成功'
    importMsgType.value = 'success'
    window.dispatchEvent(new CustomEvent('aurasaas:data-imported', {
      detail: { importType: selectedImportType.value, imported: res.data?.imported || 0, at: Date.now() },
    }))
  } catch (err) {
    importMsg.value = '导入失败: ' + err.message
    importMsgType.value = 'error'
    importing.value = false
  }
  e.target.value = ''
}

function downloadTemplate() {
  {
  const templates = {
    stores: 'store_name,city,address,area,manager,seats,staff,rating\nDemo Store,Shanghai,Road 1,Center,Alice,60,12,4.7',
    products: 'store_id,sku_name,category,price,cost,sales_count,revenue,gross_margin,date\n1,Latte,Drink,28,9,120,3360,68,2026-06-01',
    campaigns: 'campaign_name,channel,status,budget,content\nMember Day,SMS,draft,2000,Member coupon campaign',
    metrics: 'date,store_id,revenue,orders,avg_ticket,gross_margin,refund_rate,net_profit\n2026-06-01,1,18500,234,79,65,1.2,5200',
    staff: 'store_id,name,phone,role,email,hire_date,status,salary,notes\n1,Alice,13800000000,manager,alice@example.com,2026-06-01,active,8000,',
  }
  const csv = templates[selectedImportType.value] || templates.metrics
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${selectedImportType.value}_template.csv`
  a.click()
  URL.revokeObjectURL(url)
  return
  }
  const csv = `日期,门店ID,营收,订单数,客单价,毛利率,退单率,净利润
2026-06-01,1,18500,234,79,65,1.2,5200
2026-06-01,2,16800,198,85,62,0.8,4800`
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'revenue_template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

// Notifications
const savedNotifications = (() => {
  try { return JSON.parse(localStorage.getItem('aura_notifications')) } catch { return null }
})()

const notifications = reactive(savedNotifications || [
  { label: '库存预警通知', desc: '当商品库存低于阈值时发送通知', enabled: true },
  { label: '异常数据预警', desc: '当检测到成本或销量异常时通知', enabled: true },
  { label: '营销活动提醒', desc: '活动开始/结束时发送提醒', enabled: false },
  { label: '日报推送', desc: '每日经营数据摘要推送', enabled: true },
  { label: '系统更新通知', desc: '系统版本更新及新功能通知', enabled: false },
])

watch(notifications, (val) => {
  localStorage.setItem('aura_notifications', JSON.stringify(val))
}, { deep: true })

// Knowledge management

function triggerKnowledgeUpload() {
  knowledgeFileInput.value?.click()
}

function formatFileSize(size) {
  const value = Number(size || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

async function loadKnowledgeDocs() {
  knowledgeLoading.value = true
  try {
    const res = await request(`/api/tenant/knowledge/list?tenant_id=${encodeURIComponent(tenantId.value)}`)
    knowledgeDocs.value = res.data?.items || []
  } catch (err) {
    knowledgeMsg.value = '加载知识库失败: ' + err.message
    knowledgeMsgType.value = 'error'
  } finally {
    knowledgeLoading.value = false
  }
}

async function onKnowledgeFile(e) {
  const file = e.target.files[0]
  if (!file) return
  knowledgeUploading.value = true
  knowledgeMsg.value = '正在上传并索引知识库...'
  knowledgeMsgType.value = ''
  const fd = new FormData()
  fd.append('file', file)
  fd.append('tenant_id', tenantId.value)
  fd.append('created_by', auth.user?.username || auth.user?.email || 'settings')
  try {
    const res = await request('/api/tenant/knowledge/upload', { method: 'POST', body: fd })
    knowledgeMsg.value = `上传成功：${res.data?.file_name || file.name}，生成 ${res.data?.chunk_count || 0} 个知识切片`
    knowledgeMsgType.value = 'success'
    await loadKnowledgeDocs()
  } catch (err) {
    knowledgeMsg.value = '上传知识库失败: ' + err.message
    knowledgeMsgType.value = 'error'
  } finally {
    knowledgeUploading.value = false
    e.target.value = ''
  }
}

async function deleteKnowledgeDoc(doc) {
  if (!window.confirm(`确认删除知识库文件「${doc.file_name}」？删除后 AI 将不再引用该文件。`)) return
  knowledgeDeletingId.value = doc.id
  try {
    await request(`/api/tenant/knowledge/${doc.id}?tenant_id=${encodeURIComponent(tenantId.value)}`, { method: 'DELETE' })
    knowledgeMsg.value = '知识库文件已删除'
    knowledgeMsgType.value = 'success'
    await loadKnowledgeDocs()
  } catch (err) {
    knowledgeMsg.value = '删除知识库失败: ' + err.message
    knowledgeMsgType.value = 'error'
  } finally {
    knowledgeDeletingId.value = null
  }
}
// Data management
async function exportAllData() {
  try {
    const res = await fetch('/api/dashboard/export?format=csv&days=90')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `aura_export_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    dataMsg.value = '导出成功'
  } catch (err) {
    dataMsg.value = '导出失败: ' + err.message
  }
  setTimeout(() => { dataMsg.value = '' }, 3000)
}

async function regenerateMock() {
  showResetConfirm.value = false
  try {
    await request('/api/admin/regenerate-mock', { method: 'POST' })
    dataMsg.value = 'Demo 数据已重新生成'
  } catch (err) {
    dataMsg.value = '操作失败: ' + err.message
  }
  setTimeout(() => { dataMsg.value = '' }, 3000)
}

async function clearDatabase() {
  showClearConfirm.value = false
  try {
    await request('/api/admin/reset-db', { method: 'POST' })
    dataMsg.value = '数据库已清空并重新初始化'
  } catch (err) {
    dataMsg.value = '操作失败: ' + err.message
  }
  setTimeout(() => { dataMsg.value = '' }, 3000)
}

// Account actions
function handleLogout() {
  auth.logout()
  router.push('/login')
}

function handleDeleteAccount() {
  showDeleteConfirm.value = true
  accountMsg.value = ''
}

async function confirmDelete() {
  deleting.value = true
  try {
    await auth.deleteAccount()
    showDeleteConfirm.value = false
    router.push('/')
  } catch (err) {
    accountMsg.value = err.message
    accountMsgType.value = 'error'
    showDeleteConfirm.value = false
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  // Sync with backend profile
  try {
    await profile.fetchProfile()
  } catch { /* ignore */ }
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
