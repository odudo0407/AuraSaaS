<template>
  <div class="flex h-full overflow-hidden bg-[#f5f4f0]">
    <AIAnalysisSidebar
      :copy="copy"
      :stores="storeList"
      :selectedName="selectedStoreName"
      :history="chatHistory"
      :currentId="currentChatId"
      @newChat="startNewChat"
      @selectStore="selectStore"
      @loadChat="loadChat"
      @deleteChat="deleteChat"
      @clearAll="clearAllHistory"
    />

    <main class="flex min-w-0 flex-1 flex-col">
      <section ref="chatArea" class="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <div v-if="messages.length === 0" class="mx-auto max-w-920px py-10">
          <div class="rounded-lg border border-hairline bg-white p-6">
            <p class="text-sm font-bold text-primary">{{ copy.playbook }}</p>
            <h2 class="mt-2 text-3xl font-bold text-ink">{{ copy.emptyTitle }}</h2>
            <p class="mt-3 max-w-720px text-sm leading-6 text-muted">
              {{ copy.emptyBody }}
            </p>
            <div class="mt-6 grid gap-3 md:grid-cols-3">
              <button
                v-for="capability in capabilities"
                :key="capability.title"
                @click="sendMessage(capability.prompt)"
                class="rounded-lg border border-hairline bg-[#fbfaf8] p-4 text-left transition hover:border-ink"
              >
                <div class="text-xs font-bold uppercase text-muted">{{ capability.kicker }}</div>
                <div class="mt-2 text-base font-bold text-ink">{{ capability.title }}</div>
                <div class="mt-2 text-sm leading-6 text-muted">{{ capability.desc }}</div>
              </button>
            </div>
          </div>
        </div>

        <div class="mx-auto max-w-980px">
          <div v-for="message in messages" :key="message.id" class="mb-5">
            <div v-if="message.role === 'user'" class="flex justify-end">
              <div class="max-w-720px rounded-lg bg-ink px-4 py-3 text-sm leading-6 text-white">{{ message.content }}</div>
            </div>

            <div v-else class="rounded-lg border border-hairline bg-white p-4">
              <div class="mb-3 flex items-center justify-between gap-3">
                <div>
                  <div class="text-sm font-bold text-ink">{{ copy.agentRun }}</div>
                  <div class="text-xs text-muted">{{ message.traceId || copy.localStream }}</div>
                </div>
                <span
                  v-if="message.status === 'error'"
                  class="rounded-full bg-red-50 px-3 py-1 text-xs font-bold text-red-600"
                >失败</span>
                <span v-else class="rounded-full bg-[#f5f4f0] px-3 py-1 text-xs font-bold text-muted">{{ messageStatus(message.status) }}</span>
              </div>

              <div v-if="message.sections.length === 0 && message.status !== 'error'" class="text-sm text-muted">{{ copy.waiting }}</div>

              <!-- Error display -->
              <div v-if="message.status === 'error' && message.errorContent" class="text-sm text-red-600 mb-3">{{ message.errorContent }}</div>

              <!-- Thinking steps (collapsible) -->
              <div v-if="thinkingSteps(message).length > 0" class="mb-3">
                <button
                  @click="message._showSteps = !message._showSteps"
                  class="flex items-center gap-2 text-xs font-bold text-muted hover:text-ink transition"
                >
                  <span class="inline-block transition-transform" :class="{ 'rotate-90': message._showSteps }">▸</span>
                  <span v-if="message.status === 'running'">{{ copy.thinking }}</span>
                  <span v-else>{{ copy.thinkingDone.replace('{n}', thinkingSteps(message).length) }}</span>
                </button>
                <div v-if="message._showSteps" class="mt-2 grid gap-2">
                  <div
                    v-for="section in thinkingSteps(message)"
                    :key="section.id"
                    class="rounded-lg border border-hairline bg-[#fbfaf8] p-3"
                  >
                    <div class="mb-1 flex items-center justify-between gap-3">
                      <div class="text-xs font-bold text-ink">{{ section.title }}</div>
                      <span class="rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-muted-soft">{{ section.node }}</span>
                    </div>
                    <div v-if="section.content" class="markdown-body text-xs leading-5 text-body" v-html="renderMarkdown(section.content)"></div>
                  </div>
                </div>
              </div>

              <!-- Final answer (always visible) -->
              <div v-for="section in finalSections(message)" :key="section.id">
                <AgentFormCard
                  v-if="section.form"
                  :form="section.form"
                  :stores="storeList"
                  @submitted="handleFormSubmitted(message, section, $event)"
                  @cancelled="section.content = '已取消本次表格操作。'; section.form = null"
                />
                <div v-else class="markdown-body text-sm leading-6 text-body" v-html="renderMarkdown(section.content)"></div>
                <div v-if="section.references?.length" class="mt-3 grid gap-2 md:grid-cols-2">
                  <div v-for="ref in section.references" :key="ref.source" class="rounded-md border border-hairline bg-white p-3">
                    <div class="text-xs font-black text-ink">{{ ref.title }}</div>
                    <div class="mt-1 text-[11px] text-muted">{{ ref.source }}</div>
                    <div v-if="ref.snippet" class="mt-2 text-xs leading-5 text-body">{{ ref.snippet }}</div>
                  </div>
                </div>
                <div v-if="section.type === 'final_answer' || section.type === 'error'" class="mt-3 flex flex-wrap gap-2">
                  <button @click="copyText(section.content)" class="h-8 rounded-lg border border-hairline bg-white px-3 text-xs font-bold text-ink">
                    {{ copy.copyReport }}
                  </button>
                  <button @click="downloadMarkdown(section.content)" class="h-8 rounded-lg bg-ink px-3 text-xs font-bold text-white">
                    {{ copy.downloadReport }}
                  </button>
                </div>
                <router-link
                  v-if="section.campaignId"
                  to="/app/marketing"
                  class="mt-3 inline-flex h-8 items-center rounded-lg bg-primary px-3 text-xs font-bold text-white no-underline"
                >
                  {{ copy.viewCampaignDraft }}
                </router-link>
                <router-link
                  v-if="section.routeTo"
                  :to="section.routeTo"
                  class="mt-3 inline-flex h-8 items-center rounded-lg bg-primary px-3 text-xs font-bold text-white no-underline"
                >
                  查看结果
                </router-link>
              </div>

              <div v-if="message.approval" class="mt-3 rounded-lg border border-primary bg-primary/5 p-4">
                <div class="text-sm font-bold text-primary">{{ copy.approvalRequired }}</div>
                <p class="mt-2 text-sm leading-6 text-body">{{ message.approval.proposal }}</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <button
                    @click="approveProposal(message.approval.id, 'approve')"
                    class="h-9 rounded-lg bg-primary px-4 text-xs font-bold text-white"
                  >
                    {{ copy.approve }}
                  </button>
                  <button
                    @click="approveProposal(message.approval.id, 'reject')"
                    class="h-9 rounded-lg border border-hairline bg-white px-4 text-xs font-bold text-ink"
                  >
                    {{ copy.reject }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="streaming" class="mb-5 rounded-lg border border-hairline bg-white p-4">
            <div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="flex min-w-0 items-center gap-3">
                <span class="thinking-mark" aria-hidden="true"></span>
                <div class="min-w-0">
                  <div class="text-sm font-bold text-ink">{{ thinkingPhrase }}</div>
                  <div class="text-xs text-muted">{{ streamingStatus }}</div>
                </div>
              </div>
              <div class="thinking-flow" aria-hidden="true">
                <span></span>
              </div>
            </div>
            <div class="grid gap-2 md:grid-cols-4">
              <div v-for="agent in pipeline" :key="agent.id" class="rounded-lg border border-hairline bg-[#fbfaf8] p-3">
                <div class="text-xs font-bold text-ink">{{ agentLabel(agent.id) }}</div>
                <div class="mt-2 text-xs" :class="statusClass(agent.status)">{{ statusLabel(agent.status) }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="border-t border-hairline bg-white px-6 py-3">
        <div class="mx-auto max-w-980px">
          <!-- Skills selector -->
          <div v-if="skills.length" class="flex flex-wrap items-center gap-2 mb-3">
            <span class="text-xs font-bold text-muted shrink-0">Skill:</span>
            <button
              v-for="skill in skills"
              :key="skill.name"
              @click="activeSkillId = activeSkillId === skill.name ? null : skill.name"
              :class="[
                'rounded-lg border px-3 py-1.5 text-xs font-bold transition',
                activeSkillId === skill.name
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-hairline bg-[#fbfaf8] text-ink hover:border-ink'
              ]"
              :title="skill.description"
            >
              {{ skill.name === 'review_reply' ? '差评回复' : skill.name === 'store_health' ? '健康度诊断' : skill.name }}
            </button>
          </div>
          <!-- Quick prompts above input -->
          <div class="flex flex-wrap gap-2 mb-3">
            <button
              v-for="prompt in quickPrompts"
              :key="prompt"
              @click="sendMessage(prompt)"
              class="rounded-lg border border-hairline bg-[#fbfaf8] px-3 py-2 text-xs font-bold text-ink transition hover:border-ink"
            >
              {{ prompt }}
            </button>
          </div>
          <!-- Streaming indicator -->
          <div v-if="streaming" class="flex items-center gap-3 mb-3">
            <div class="water-flow">
              <span class="water-drop d1"></span>
              <span class="water-drop d2"></span>
              <span class="water-drop d3"></span>
              <span class="water-drop d4"></span>
              <span class="water-drop d5"></span>
              <span class="water-ripple"></span>
            </div>
            <span class="text-sm font-bold text-primary thinking-label">{{ thinkingText }}</span>
          </div>
          <div class="flex items-start gap-3">
            <textarea
              ref="inputRef"
              v-model="input"
              @keydown.enter.exact.prevent="sendMessage(input)"
              @input="autoResize"
              :placeholder="copy.inputPlaceholder"
              :disabled="streaming"
              class="min-h-44px flex-1 resize-none rounded-xl border border-hairline bg-[#fbfaf8] px-5 py-2 text-sm leading-6 text-body placeholder:text-muted-soft focus:border-ink focus:outline-none focus:ring-1 focus:ring-ink/10"
              rows="1"
            ></textarea>
            <button
              @click="sendMessage(input)"
              :disabled="streaming || !input.trim()"
              class="h-10 shrink-0 rounded-xl bg-primary px-6 text-sm font-bold text-white transition hover:bg-primary-active disabled:opacity-40"
            >
              {{ copy.send }}
            </button>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, nextTick } from 'vue'
import { useLanguage } from '../utils/language.js'
import { useAgentAnalysis } from '../composables/useAgentAnalysis.js'
import { renderMarkdown } from '../utils/markdown.js'
import AIAnalysisSidebar from '../components/AIAnalysisSidebar.vue'
import AgentFormCard from '../components/AgentFormCard.vue'

const { language } = useLanguage()
const {
  messages, streaming, streamingStatus, pipeline, chatHistory, currentChatId,
  thinkingPhrase,
  storeList, selectedStoreId, selectedStoreName,
  input, inputRef, chatArea,
  skills, activeSkillId, fetchSkills,
  startNewChat, sendMessage, loadChat, selectStore, approveProposal,
  deleteChat, clearAllHistory,
  agentLabel, statusLabel, statusClass, messageStatus,
  autoResize, scrollToBottom,
} = useAgentAnalysis()

const copy = computed(() => translations[language.value])

const translations = {
  zh: {
    kicker: 'AI 分析工作台', title: '多智能体协作诊断',
    newAnalysis: '新分析', selectedStore: '选择门店', allStores: '全部门店',
    traceHistory: '历史记录', noHistory: '暂无历史记录', clearAll: '清空',
    playbook: 'Playbook', emptyTitle: '你的 AI 经营指挥室',
    emptyBody: '输入问题，AI 会自动调用数据诊断、外部环境、SOP 知识库、风险评估、审批和营销文案生成模块，最终给出可执行建议。',
    inputPlaceholder: '描述你的问题，例如“为什么昨天营收下降”', send: '发送',
    agentTagline: '多智能体工具运作中',
    agentRun: 'AI Agent', localStream: 'local stream',
    waiting: '等待 AI 响应中...',
    ready: '就绪', starting: '正在启动...', completed: '已完成',
    processing: '处理中', agentEvent: '事件',
    connectionError: '连接错误',
    approvalRequired: '需要审批', approve: '批准', reject: '驳回',
    approvalUpdated: '审批已更新',
    approvedResult: '已批准，策略已转为活动草稿。',
    rejectedResult: '已驳回。',
    campaignDraftCreated: '已生成活动草稿，请查看营销模块。',
    viewCampaignDraft: '查看活动草稿',
    copyReport: '复制报告', downloadReport: '下载 Markdown',
    thinking: '正在思考...', thinkingDone: '思考过程（{n}步）',
    quickPrompts: ['近 7 天营收趋势', '哪些 SKU 退款最高', '给我一份营销方案', '查看最新存量预警'],
    capabilities: [
      { kicker: 'diagnose', title: '营收异常诊断', desc: '跨门店对比数据找出营收下滑、退款异常、毛利恶化等信号。', prompt: '分析近三天营收下降原因' },
      { kicker: 'plan', title: 'RAG 策略规划', desc: '基于 SOP 知识库生成可执行营销方案。', prompt: '用我们的 SOP 为最弱门店设计低预算活动' },
      { kicker: 'approve', title: '人工审批控制', desc: '高风险策略需要管理者审批才能执行。', prompt: '生成一份需要店长审批的营销方案' },
    ],
    pipeline: { skill_executor: 'Skill', intent_router: 'Intent', data_analyst: 'Data', fetch_context: 'Context', rag_strategist: 'RAG', risk_controller: 'Risk', human_approval: 'Approval', copywriter: 'Copy', data_editor: 'Data Edit', general_chat: 'Answer', report_generator: 'Report' },
    statuses: { pending: '等待', running: '执行中', complete: '完成', failed: '失败' },
  },
  en: {
    kicker: 'AI Analysis', title: 'Multi-agent Diagnosis',
    newAnalysis: 'New Analysis', selectedStore: 'Select Store', allStores: 'All Stores',
    traceHistory: 'History', noHistory: 'No history yet', clearAll: 'Clear all',
    playbook: 'Playbook', emptyTitle: 'Your AI Command Center',
    emptyBody: 'Describe your question. AI will automatically invoke data diagnosis, external context, SOP knowledge base, risk assessment, approval, and copywriting modules to provide actionable advice.',
    inputPlaceholder: 'Describe your question, e.g. "Why did revenue drop yesterday"', send: 'Send',
    agentTagline: 'Multi-agent Tools Running',
    agentRun: 'AI Agent', localStream: 'local stream',
    waiting: 'Waiting for AI response...',
    ready: 'Ready', starting: 'Starting...', completed: 'Completed',
    processing: 'Processing', agentEvent: 'Event',
    connectionError: 'Connection error',
    approvalRequired: 'Approval required', approve: 'Approve', reject: 'Reject',
    approvalUpdated: 'Approval updated',
    approvedResult: 'Approved. Strategy converted to campaign draft.',
    rejectedResult: 'Rejected.',
    campaignDraftCreated: 'Campaign draft created. View in Marketing module.',
    viewCampaignDraft: 'View campaign draft',
    copyReport: 'Copy report', downloadReport: 'Download Markdown',
    thinking: 'Thinking...', thinkingDone: 'Thinking process ({n} steps)',
    quickPrompts: ['Revenue trend (7d)', 'Top refund SKUs', 'Marketing plan', 'Inventory alerts'],
    capabilities: [
      { kicker: 'diagnose', title: 'Revenue anomaly diagnosis', desc: 'Cross-store comparison to find revenue drops, refund anomalies, margin deterioration.', prompt: 'Analyze why revenue dropped in the last three days' },
      { kicker: 'plan', title: 'RAG strategy planning', desc: 'Generate actionable marketing plans grounded in SOP knowledge.', prompt: 'Use our SOPs to design a low-budget campaign for the weakest store' },
      { kicker: 'approve', title: 'HITL approval control', desc: 'High-risk strategies require manager approval before execution.', prompt: 'Draft a marketing action requiring store manager approval' },
    ],
    pipeline: { skill_executor: 'Skill', intent_router: 'Intent', data_analyst: 'Data', fetch_context: 'Context', rag_strategist: 'RAG', risk_controller: 'Risk', human_approval: 'Approval', copywriter: 'Copy', data_editor: 'Data Edit', general_chat: 'Answer', report_generator: 'Report' },
    statuses: { pending: 'Waiting', running: 'Running', complete: 'Done', failed: 'Failed' },
  },
}

const quickPrompts = computed(() => copy.value.quickPrompts)
const capabilities = computed(() => copy.value.capabilities)

const thinkingText = computed(() => {
  if (!streaming.value) return ''
  return thinkingPhrase.value
})

function thinkingSteps(msg) {
  return (msg.sections || []).filter(s => s.type !== 'final_answer' && s.type !== 'error')
}
function finalSections(msg) {
  return (msg.sections || []).filter(s => s.type === 'final_answer' || s.type === 'error')
}

function copyText(text) {
  navigator.clipboard?.writeText(text)
}

function downloadMarkdown(text) {
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `aurasaas-report-${new Date().toISOString().slice(0, 10)}.md`
  link.click()
  URL.revokeObjectURL(url)
}

function handleFormSubmitted(message, section, result) {
  section.form = null
  section.type = 'form_submitted'
  section.content = `表格已提交：成功 ${result.success_count || 0} 行，失败 ${result.failure_count || 0} 行。`
  const target = result.form_type === 'staff' ? '/app/staff' : '/app/products'
  message.sections.push({
    id: crypto.randomUUID(),
    node: 'agent_form',
    title: result.form_type === 'staff' ? '人员操作完成' : '商品操作完成',
    content: `操作已写入系统，可前往${result.form_type === 'staff' ? '人员' : '商品'}页面查看。`,
    type: 'form_submitted',
    routeTo: target,
  })
  scrollToBottom()
}

onMounted(() => { fetchSkills() })
</script>

<style scoped>
/* === Water flowing animation === */
.water-flow {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 28px;
  padding: 0 4px;
}

.water-drop {
  display: inline-block;
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(180deg, #4da6ff 0%, #2563eb 40%, #1d4ed8 100%);
  transform-origin: bottom center;
}

.water-drop.d1 { height: 10px; animation: waterFlow 1.2s ease-in-out infinite; }
.water-drop.d2 { height: 16px; animation: waterFlow 1.2s ease-in-out 0.15s infinite; }
.water-drop.d3 { height: 22px; animation: waterFlow 1.2s ease-in-out 0.3s infinite; }
.water-drop.d4 { height: 16px; animation: waterFlow 1.2s ease-in-out 0.45s infinite; }
.water-drop.d5 { height: 10px; animation: waterFlow 1.2s ease-in-out 0.6s infinite; }

@keyframes waterFlow {
  0%, 100% { transform: scaleY(0.3); opacity: 0.25; }
  30% { transform: scaleY(1.1); opacity: 0.9; }
  60% { transform: scaleY(0.5); opacity: 0.4; }
}

/* Ripple effect behind the bars */
.water-ripple {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, #4da6ff, #2563eb, #4da6ff, transparent);
  background-size: 200% 100%;
  animation: rippleFlow 2s linear infinite;
  opacity: 0.5;
}

@keyframes rippleFlow {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* Thinking label with soft pulse */
.thinking-label {
  animation: labelPulse 1.8s ease-in-out infinite;
  background: linear-gradient(90deg, #2563eb, #4da6ff, #2563eb);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

@keyframes labelPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
</style>
