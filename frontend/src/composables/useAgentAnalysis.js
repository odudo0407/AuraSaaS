/**
 * Composable for AI Analysis page — state, streaming, chat history, approvals.
 */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { request, streamSSE } from '../utils/request'
import { useLanguage } from '../utils/language'

const _translations = {
  zh: {
    kicker: 'AI 分析工作台',
    title: '多智能体经营诊断',
    playbook: 'Playbook',
    emptyTitle: '你想分析什么经营问题？',
    emptyBody: '输入问题后，AI Agent 将依次执行意图识别、数据诊断、RAG策略检索、风险评估、人工审批和文案生成。你可以实时查看每个节点的执行状态。',
    newAnalysis: '+ 新分析',
    selectedStore: '选择门店',
    allStores: '全部门店',
    traceHistory: '历史分析',
    noHistory: '暂无历史，开始新分析后将自动保存。',
    agentRun: 'Agent 运行',
    localStream: 'Local stream',
    waiting: '等待 Agent 响应...',
    startAnalysis: '开始分析',
    askAgent: '向 Agent 提问...',
    quickPrompts: ['最近退单率为什么升高？', '帮我写个会员日营销文案', '生成上周各门店战报'],
    capabilities: [
      { kicker: 'diagnose', title: '实时数据诊断', desc: '自动检测营收下滑、退单飙升和毛利恶化等异常信号。', prompt: '帮我诊断最近一周的营收变化和异常' },
      { kicker: 'plan', title: 'RAG 策略建议', desc: '基于 SOP 和经营知识库生成可执行策略。', prompt: '根据 SOP 为最弱门店设计一个低预算提升方案' },
      { kicker: 'approve', title: '人工审批控制', desc: '高风险策略建议先经过审批再进入执行。', prompt: '起草一个需要店长审批的营销方案' },
    ],
    pipeline: {
      skill_executor: 'Skill', intent_router: '意图', data_analyst: '数据', fetch_context: '环境',
      rag_strategist: 'RAG', risk_controller: '风险', human_approval: '审批',
      copywriter: '文案', data_editor: '数据', agent_form: '表格', general_chat: '直答', report_generator: '报告',
    },
    eventTitles: {
      skill_executor: 'Skill 执行', intent_router: '意图识别', data_analyst: '数据诊断', fetch_context: '外部环境',
      rag_strategist: 'RAG 策略', risk_controller: '风险评估', human_approval: '审批门',
      copywriter: '营销文案', data_editor: '数据编辑', agent_form: '经营表格', general_chat: '直接回答', report_generator: '最终报告',
    },
    thinkingPhrases: ['正在思考...', '正在分析数据...', '正在规划策略...', '经营中...', '正在检索知识库...', '正在评估风险...', '正在生成方案...', '即将完成...'],
    statuses: { pending: '等待', running: '执行中', complete: '完成', failed: '失败' },
    agentEvent: 'Agent 事件',
    connectionError: '连接错误',
    approvalUpdated: '审批已更新',
    campaignDraftCreated: '审批通过，活动草稿已创建。',
    approvedResult: '策略已审批通过。',
    rejectedResult: '策略已拒绝。',
    processing: '处理中',
    ready: '准备就绪',
    starting: '启动中',
    completed: '完成',
    approvalRequired: '需要审批',
    approve: '批准',
    reject: '拒绝',
    copyReport: '复制报告',
    downloadReport: '下载报告',
    viewCampaignDraft: '查看活动草稿',
    untitled: '未命名',
    locale: 'zh-CN',
  },
  en: {
    quickPrompts: ['Why did refunds rise recently?', 'Write member-day campaign copy', 'Generate last week store report'],
    capabilities: [
      { kicker: 'diagnose', title: 'Realtime diagnosis', desc: 'Detect revenue drops, refund spikes, and margin issues.', prompt: 'Diagnose revenue changes and anomalies from the last week' },
      { kicker: 'plan', title: 'RAG strategy', desc: 'Generate executable plans grounded in SOPs and business knowledge.', prompt: 'Use our SOPs to design a low-budget campaign for the weakest store' },
      { kicker: 'approve', title: 'Human approval', desc: 'Route risky strategies to approval before execution.', prompt: 'Draft a marketing plan that requires store manager approval' },
    ],
    pipeline: {
      skill_executor: 'Skill', intent_router: 'Intent', data_analyst: 'Data', fetch_context: 'Context',
      rag_strategist: 'RAG', risk_controller: 'Risk', human_approval: 'Approval',
      copywriter: 'Copy', data_editor: 'Data', agent_form: 'Form', general_chat: 'Answer', report_generator: 'Report',
    },
    eventTitles: {
      intent_router: 'Intent routing', data_analyst: 'Data diagnosis', fetch_context: 'External context',
      rag_strategist: 'RAG strategy', risk_controller: 'Risk assessment', human_approval: 'Approval gate',
      copywriter: 'Campaign copy', data_editor: 'Data edit', agent_form: 'Business form', general_chat: 'Direct answer', report_generator: 'Final report',
    },
    thinkingPhrases: ['Thinking...', 'Analyzing data...', 'Planning strategy...', 'Operating...', 'Searching knowledge base...', 'Assessing risk...', 'Generating plan...', 'Almost done...'],
    statuses: { pending: 'Waiting', running: 'Running', complete: 'Done', failed: 'Failed' },
    agentEvent: 'Agent event',
    connectionError: 'Connection error',
    approvalUpdated: 'Approval updated',
    campaignDraftCreated: 'Approved. Campaign draft created.',
    approvedResult: 'Strategy approved.',
    rejectedResult: 'Strategy rejected.',
    processing: 'Processing',
    ready: 'Ready',
    starting: 'Starting',
    completed: 'Completed',
    untitled: 'Untitled',
    locale: 'en-US',
  },
}

export function useAgentAnalysis() {
  const { language } = useLanguage()
  const copy = computed(() => _translations[language.value] || _translations.zh)

  // --- state ---
  const input = ref('')
  const inputRef = ref(null)
  const chatArea = ref(null)
  const streaming = ref(false)
  const streamingStatus = ref('')
  const thinkingPhraseIndex = ref(0)
  const messages = ref([])
  const chatHistory = ref([])
  const currentChatId = ref(null)
  const storeList = ref([])
  const selectedStoreId = ref(null)
  const selectedStoreName = ref('')
  const showStoreDropdown = ref(false)
  const ragDocs = ref([])
  const ragSearchQuery = ref('')
  const ragSearchResults = ref([])
  const recentTraces = ref([])
  const selectedTrace = ref(null)

  const skills = ref([])
  const activeSkillId = ref(null)

  const pipeline = reactive([
    { id: 'skill_executor', status: 'pending' },
    { id: 'intent_router', status: 'pending' },
    { id: 'data_analyst', status: 'pending' },
    { id: 'fetch_context', status: 'pending' },
    { id: 'rag_strategist', status: 'pending' },
    { id: 'risk_controller', status: 'pending' },
    { id: 'human_approval', status: 'pending' },
    { id: 'copywriter', status: 'pending' },
    { id: 'data_editor', status: 'pending' },
    { id: 'agent_form', status: 'pending' },
    { id: 'general_chat', status: 'pending' },
    { id: 'report_generator', status: 'pending' },
  ])

  const quickPrompts = computed(() => copy.value.quickPrompts)
  const capabilities = computed(() => copy.value.capabilities)
  const thinkingPhrase = computed(() => {
    const phrases = copy.value.thinkingPhrases || [copy.value.processing]
    return phrases[thinkingPhraseIndex.value % phrases.length]
  })

  let thinkingTimer = null

  // --- helpers ---
  function agentLabel(id) { return copy.value.pipeline[id] || id }
  function eventTitle(node) { return copy.value.eventTitles[node] || copy.value.processing }
  function statusLabel(s) { return copy.value.statuses[s] || s }
  function statusClass(s) {
    return { pending: 'text-muted', running: 'text-primary', complete: 'text-[#237b4b]', failed: 'text-error-text' }[s] || 'text-muted'
  }

  function resetPipeline() { pipeline.forEach(a => { a.status = 'pending' }) }
  function markPipeline(node, s) { const item = pipeline.find(a => a.id === node); if (item) item.status = s }

  function messageStatus(status) { return statusLabel(status || 'running') }

  function startThinkingTicker() {
    stopThinkingTicker()
    thinkingPhraseIndex.value = 0
    thinkingTimer = window.setInterval(() => {
      thinkingPhraseIndex.value += 1
    }, 1800)
  }

  function stopThinkingTicker() {
    if (thinkingTimer) {
      window.clearInterval(thinkingTimer)
      thinkingTimer = null
    }
  }

  function autoResize(event) {
    const el = event?.target || inputRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      if (chatArea.value) chatArea.value.scrollTop = chatArea.value.scrollHeight
    })
  }

  function selectStore(store) {
    selectedStoreId.value = store?.id || null
    selectedStoreName.value = store?.name || ''
    showStoreDropdown.value = false
  }

  // --- data loading ---
  async function fetchSkills() {
    try {
      const data = await request('/api/skills')
      skills.value = data?.data?.skills || []
    } catch { skills.value = [] }
  }

  async function loadStores() {
    try { const r = await request('/api/dashboard/stores'); storeList.value = r.data || [] } catch { storeList.value = [] }
  }

  async function loadRagDocs() {
    try { const r = await request('/api/rag/documents'); ragDocs.value = r.data || [] } catch { ragDocs.value = [] }
  }

  async function searchKnowledge() {
    if (!ragSearchQuery.value.trim()) return
    try {
      const form = new URLSearchParams()
      form.append('query', ragSearchQuery.value)
      form.append('top_k', '3')
      const r = await request('/api/rag/search', { method: 'POST', body: form, headers: {} })
      ragSearchResults.value = r.data || []
    } catch { ragSearchResults.value = [] }
  }

  async function loadTraces() {
    try { const r = await request('/api/agent/traces?limit=12'); recentTraces.value = r.data || [] } catch { recentTraces.value = [] }
  }

  async function loadTrace(traceId) {
    try { const r = await request(`/api/agent/traces/${traceId}`); selectedTrace.value = r.data } catch { selectedTrace.value = null }
  }

  // --- chat management ---
  function saveCurrentChat() {
    const firstUser = messages.value.find(m => m.role === 'user')
    const entry = {
      id: currentChatId.value,
      title: firstUser?.content?.slice(0, 42) || copy.value.untitled,
      time: new Date().toLocaleString(copy.value.locale, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
      messages: JSON.parse(JSON.stringify(messages.value)),
    }
    const existing = chatHistory.value.find(c => c.id === entry.id)
    if (existing) Object.assign(existing, entry)
    else chatHistory.value.unshift(entry)
    localStorage.setItem('aurasaas_chat_history', JSON.stringify(chatHistory.value))
  }

  function startNewChat() {
    if (messages.value.length && currentChatId.value) saveCurrentChat()
    currentChatId.value = null
    messages.value = []
    resetPipeline()
  }

  function loadChat(chat) {
    currentChatId.value = chat.id
    messages.value = JSON.parse(JSON.stringify(chat.messages || []))
  }

  // --- core: send & stream ---
  async function sendMessage(text, _scrollFn) {
    const query = text?.trim()
    if (!query || streaming.value) return

    if (!currentChatId.value) currentChatId.value = String(Date.now())
    input.value = ''
    resetPipeline()
    messages.value.push({ id: crypto.randomUUID(), role: 'user', content: query })

    const aiMessage = reactive({
      id: crypto.randomUUID(), role: 'ai', traceId: '', status: 'running', sections: [], approval: null,
    })
    messages.value.push(aiMessage)
    streaming.value = true
    streamingStatus.value = copy.value.starting
    startThinkingTicker()

    try {
      // Build conversation history from previous messages (exclude the two we just pushed)
      const history = []
      const allMsgs = messages.value.slice(0, -2)  // exclude user + ai stub just added
      for (const m of allMsgs) {
        if (m.role === 'user') {
          history.push({ role: 'user', content: m.content || '' })
        } else if (m.role === 'ai' && m.sections && m.sections.length > 0) {
          // Concatenate all section contents as the assistant's response
          const text = m.sections.map(s => s.content || '').filter(Boolean).join('\n')
          if (text) history.push({ role: 'assistant', content: text })
        }
      }

      const body = { query, history }
      if (selectedStoreId.value) body.store_id = selectedStoreId.value

      // Pass user-configured API key / base URL / model from Settings page
      const savedKey = localStorage.getItem('aura_apiKey')
      const savedUrl = localStorage.getItem('aura_baseUrl')
      const savedModel = localStorage.getItem('aura_model')
      if (savedKey) body.api_key = savedKey
      if (savedUrl) body.base_url = savedUrl
      if (savedModel) body.model = savedModel

      // Auto-route endpoint: LangGraph (HITL) for high-risk, ReAct for quick queries
      const url = '/api/agent/stream'
      for await (const event of streamSSE(url, { method: 'POST', body: JSON.stringify(body) })) {
        if (event.trace_id) aiMessage.traceId = event.trace_id
        if (event.type === 'error') {
          aiMessage.status = 'error'
          aiMessage.errorContent = event.content || '未知错误'
          aiMessage.sections.push({
            id: crypto.randomUUID(),
            node: event.node || 'report_generator',
            title: event.title || '❌ 执行异常',
            content: event.content || '',
            type: 'error',
          })
          streamingStatus.value = '执行异常'
          break
        }
        if (event.node === 'end') {
          if (event.awaiting_approval) {
            aiMessage.status = 'awaiting_approval'
            streamingStatus.value = '等待审批...'
          } else {
            aiMessage.status = 'complete'
            streamingStatus.value = copy.value.completed
          }
          break
        }
        if (event.node) { markPipeline(event.node, event.done ? 'complete' : 'running'); streamingStatus.value = eventTitle(event.node) }
        if (event.type === 'approval_required') aiMessage.approval = { id: event.approval_id, proposal: event.content }
        if (event.content) {
          aiMessage.sections.push({
            id: crypto.randomUUID(),
            node: event.node || 'agent',
            title: event.title || eventTitle(event.node) || copy.value.agentEvent,
            content: event.type === 'rag_reference' && event.strategy ? event.strategy : event.content,
            type: event.type,
            form: event.form || null,
            references: event.references || [],
            durationMs: event.duration_ms || 0,
          })
          scrollToBottom()
        }
      }
    } catch (error) {
      aiMessage.status = 'failed'
      aiMessage.sections.push({ id: crypto.randomUUID(), node: 'error', title: copy.value.connectionError, content: error.message })
      pipeline.forEach(a => { if (a.status === 'running') a.status = 'failed' })
    } finally {
      streaming.value = false
      stopThinkingTicker()
      pipeline.forEach(a => { if (a.status === 'running') a.status = 'complete' })
      saveCurrentChat()
      loadTraces()
    }
  }

  async function approveProposal(id, action) {
    if (!id) return
    try {
      const res = await request('/api/agent/approve', { method: 'POST', body: JSON.stringify({ approval_id: id, action, comment: '' }) })
      const lastAi = [...messages.value].reverse().find(m => m.role === 'ai' && m.approval)
      if (lastAi) {
        lastAi.approval = null
        lastAi.sections.push({
          id: crypto.randomUUID(), node: 'human_approval', title: copy.value.approvalUpdated,
          content: action === 'approve' && res.data?.campaign_id ? copy.value.campaignDraftCreated
            : action === 'approve' ? copy.value.approvedResult : copy.value.rejectedResult,
          type: 'approval_update', campaignId: res.data?.campaign_id,
        })
        // If approved, resume Phase 2 (copywriter -> report_generator) via SSE
        if (action === 'approve' && lastAi.traceId) {
          streaming.value = true
          streamingStatus.value = copy.value.starting
          startThinkingTicker()
          try {
            const resumeUrl = `/api/agent/stream-resume?trace_id=${lastAi.traceId}`
            for await (const event of streamSSE(resumeUrl)) {
              if (event.node === 'end') {
                lastAi.status = 'complete'
                streamingStatus.value = copy.value.completed
                break
              }
              if (event.node) {
                markPipeline(event.node, event.done ? 'complete' : 'running')
                streamingStatus.value = eventTitle(event.node)
              }
              if (event.content) {
                lastAi.sections.push({
                  id: crypto.randomUUID(),
                  node: event.node || 'agent',
                  title: event.title || eventTitle(event.node) || copy.value.agentEvent,
                  content: event.type === 'rag_reference' && event.strategy ? event.strategy : event.content,
                  type: event.type,
                  references: event.references || [],
                  durationMs: event.duration_ms || 0,
                })
                scrollToBottom()
              }
            }
          } catch (e) {
            lastAi.sections.push({ id: crypto.randomUUID(), node: 'error', title: copy.value.connectionError, content: e.message })
          } finally {
            streaming.value = false
            stopThinkingTicker()
            pipeline.forEach(a => { if (a.status === 'running') a.status = 'complete' })
          }
        }
      }
      saveCurrentChat()
      loadTraces()
    } catch (e) { console.error('Approval failed:', e) }
  }

  // --- init ---
  onMounted(() => {
    try { chatHistory.value = JSON.parse(localStorage.getItem('aurasaas_chat_history') || '[]') } catch { chatHistory.value = [] }
    loadStores(); loadRagDocs(); loadTraces()
  })
  onUnmounted(stopThinkingTicker)

  // --- delete ---
  async function deleteChat(chatId) {
    chatHistory.value = chatHistory.value.filter(c => c.id !== chatId)
    localStorage.setItem('aurasaas_chat_history', JSON.stringify(chatHistory.value))
    if (currentChatId.value === chatId) { startNewChat() }
    try { await request(`/api/agent/traces/${chatId}`, { method: 'DELETE' }) } catch { /* ok */ }
  }

  async function clearAllHistory() {
    chatHistory.value = []
    localStorage.removeItem('aurasaas_chat_history')
    startNewChat()
    try { await request('/api/agent/traces', { method: 'DELETE' }) } catch { /* ok */ }
  }

  return {
    copy, input, inputRef, chatArea, streaming, streamingStatus, thinkingPhrase,
    messages, chatHistory, currentChatId,
    storeList, selectedStoreId, selectedStoreName, showStoreDropdown,
    ragDocs, ragSearchQuery, ragSearchResults,
    recentTraces, selectedTrace,
    skills, activeSkillId, fetchSkills,
    pipeline, quickPrompts, capabilities,
    agentLabel, eventTitle, statusLabel, statusClass, messageStatus,
    selectStore, startNewChat, loadChat, saveCurrentChat,
    sendMessage, approveProposal,
    deleteChat, clearAllHistory,
    searchKnowledge, loadTraces, loadTrace,
    resetPipeline, markPipeline, autoResize, scrollToBottom,
  }
}
