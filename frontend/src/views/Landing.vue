<template>
  <div class="min-h-screen bg-[#fbfaf8] text-ink">
    <header class="sticky top-0 z-40 border-b border-hairline bg-[#fbfaf8]/92 backdrop-blur">
      <div class="mx-auto flex min-h-16 max-w-1200px flex-wrap items-center justify-between gap-3 px-6 py-2">
        <router-link to="/" class="flex items-center gap-3 no-underline">
          <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-ink text-white font-bold">A</span>
          <span class="text-xl font-bold text-ink">AuraSaaS</span>
        </router-link>

        <nav class="hidden items-center gap-6 text-sm text-muted md:flex">
          <a href="#agents" class="text-muted no-underline hover:text-ink">{{ copy.navAgents }}</a>
          <a href="#ops" class="text-muted no-underline hover:text-ink">{{ copy.navOps }}</a>
          <a href="#stack" class="text-muted no-underline hover:text-ink">{{ copy.navStack }}</a>
        </nav>

        <div class="flex items-center gap-3">
          <div class="inline-flex rounded-xl border border-ink bg-white p-1 shadow-[0_8px_22px_rgba(34,34,34,0.08)]">
            <button
              v-for="option in languageOptions"
              :key="option.value"
              @click="setLanguage(option.value)"
              class="h-10 min-w-88px rounded-lg px-4 text-sm font-black transition"
              :class="language === option.value ? 'bg-ink text-white' : 'text-ink hover:bg-[#f5f4f0]'"
            >
              {{ option.label }}
            </button>
          </div>
          <button
            @click="goWorkspace"
            class="h-10 rounded-lg border border-ink bg-ink px-4 text-sm font-semibold text-white transition hover:bg-body"
          >
            {{ copy.openWorkspace }}
          </button>
        </div>
      </div>
    </header>

    <main>
      <section class="mx-auto grid max-w-1200px items-center gap-10 px-6 py-10 lg:min-h-[calc(100vh-9rem)] lg:grid-cols-[0.92fr_1.08fr]">
        <div>
          <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-hairline bg-white px-3 py-1 text-xs font-semibold text-body">
            <span class="h-2 w-2 rounded-full bg-[#2f9e44]"></span>
            {{ copy.badge }}
          </div>

          <h1 class="max-w-680px text-5xl font-bold leading-[1.05] tracking-normal text-ink md:text-6xl">
            {{ copy.heroTitle }}
          </h1>
          <p class="mt-5 max-w-620px text-lg leading-8 text-muted">
            {{ copy.heroBody }}
          </p>
          <div class="mt-7 flex flex-wrap gap-3">
            <button
              @click="goWorkspace"
              class="h-12 rounded-lg bg-primary px-6 text-sm font-bold text-white transition hover:bg-primary-active"
            >
              {{ copy.launchDemo }}
            </button>
            <a
              href="https://github.com/Enndme-KK/AuraSaaS"
              target="_blank"
              rel="noreferrer"
              class="flex h-12 items-center rounded-lg border border-hairline bg-white px-6 text-sm font-bold text-ink no-underline transition hover:border-ink"
            >
              {{ copy.viewGithub }}
            </a>
          </div>

          <div class="mt-8 grid max-w-620px grid-cols-3 gap-3">
            <div v-for="metric in copy.heroMetrics" :key="metric.label" class="border-l border-hairline pl-4">
              <div class="text-2xl font-bold text-ink">{{ metric.value }}</div>
              <div class="mt-1 text-xs leading-5 text-muted">{{ metric.label }}</div>
            </div>
          </div>
        </div>

        <div class="relative">
          <div class="overflow-hidden rounded-lg border border-ink bg-white shadow-[0_22px_70px_rgba(34,34,34,0.14)]">
            <div class="flex items-center justify-between border-b border-hairline bg-[#f5f2ed] px-4 py-3">
              <div class="flex items-center gap-2">
                <span class="h-3 w-3 rounded-full bg-[#ff5f57]"></span>
                <span class="h-3 w-3 rounded-full bg-[#febc2e]"></span>
                <span class="h-3 w-3 rounded-full bg-[#28c840]"></span>
              </div>
              <span class="rounded-md bg-white px-3 py-1 text-xs text-muted">agent run #AURA-2048</span>
            </div>
            <div class="grid gap-0 lg:grid-cols-[1fr_300px]">
              <div class="p-5">
                <div class="mb-5 flex items-center justify-between">
                  <div>
                    <p class="text-xs font-semibold uppercase text-muted">{{ copy.previewKicker }}</p>
                    <h2 class="mt-1 text-2xl font-bold">{{ copy.previewTitle }}</h2>
                  </div>
                  <span class="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">{{ copy.previewStatus }}</span>
                </div>
                <div class="grid grid-cols-3 gap-3">
                  <div v-for="card in copy.previewCards" :key="card.label" class="rounded-lg border border-hairline bg-[#fbfaf8] p-4">
                    <div class="text-xs text-muted">{{ card.label }}</div>
                    <div class="mt-2 text-xl font-bold">{{ card.value }}</div>
                    <div class="mt-2 text-xs" :class="card.good ? 'text-[#2f9e44]' : 'text-primary'">{{ card.delta }}</div>
                  </div>
                </div>
                <div class="mt-5 rounded-lg border border-hairline p-4">
                  <div class="mb-4 flex items-center justify-between">
                    <span class="text-sm font-bold">{{ copy.signalGraph }}</span>
                    <span class="text-xs text-muted">{{ copy.liveContext }}</span>
                  </div>
                  <div class="flex h-36 items-end gap-2">
                    <span
                      v-for="(bar, index) in bars"
                      :key="index"
                      class="flex-1 rounded-t bg-primary/70"
                      :style="{ height: `${bar}%`, opacity: 0.45 + index / 24 }"
                    ></span>
                  </div>
                </div>
              </div>
              <aside class="border-t border-hairline bg-[#111827] p-5 text-white lg:border-l lg:border-t-0">
                <p class="text-xs font-semibold uppercase text-white/50">{{ copy.pipelineTitle }}</p>
                <div class="mt-5 space-y-4">
                  <div v-for="agent in copy.agents" :key="agent.name" class="flex gap-3">
                    <span class="mt-1 h-2.5 w-2.5 rounded-full" :class="agent.active ? 'bg-[#37d67a]' : 'bg-white/25'"></span>
                    <div>
                      <div class="text-sm font-bold">{{ agent.name }}</div>
                      <div class="mt-1 text-xs leading-5 text-white/55">{{ agent.note }}</div>
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </section>

      <section id="agents" class="border-y border-hairline bg-white">
        <div class="mx-auto max-w-1200px px-6 py-10">
          <div class="mb-8 flex items-end justify-between gap-6">
            <div>
              <p class="text-sm font-bold text-primary">{{ copy.agentKicker }}</p>
              <h2 class="mt-2 text-3xl font-bold">{{ copy.agentTitle }}</h2>
            </div>
            <p class="max-w-420px text-sm leading-6 text-muted">{{ copy.agentBody }}</p>
          </div>
          <div class="grid gap-4 md:grid-cols-4">
            <article v-for="feature in copy.features" :key="feature.title" class="rounded-lg border border-hairline bg-[#fbfaf8] p-5">
              <div class="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-ink text-sm font-bold text-white">{{ feature.short }}</div>
              <h3 class="text-base font-bold">{{ feature.title }}</h3>
              <p class="mt-2 text-sm leading-6 text-muted">{{ feature.body }}</p>
            </article>
          </div>
        </div>
      </section>

      <section id="ops" class="mx-auto max-w-1200px px-6 py-12">
        <div class="grid gap-4 md:grid-cols-3">
          <router-link
            v-for="module in copy.modules"
            :key="module.path"
            :to="module.path"
            class="rounded-lg border border-hairline bg-white p-5 text-ink no-underline transition hover:-translate-y-0.5 hover:border-ink hover:shadow-lg"
          >
            <div class="text-xs font-semibold uppercase text-muted">{{ module.kicker }}</div>
            <div class="mt-3 text-lg font-bold">{{ module.name }}</div>
            <p class="mt-2 text-sm leading-6 text-muted">{{ module.desc }}</p>
          </router-link>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useLanguage } from '../utils/language'

const router = useRouter()
const auth = useAuthStore()
const { language, setLanguage } = useLanguage()

const languageOptions = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
]

const copy = computed(() => translations[language.value])

function goWorkspace() {
  router.push(auth.isLoggedIn ? '/app/dashboard' : '/login')
}

const bars = [42, 58, 49, 66, 72, 61, 54, 74, 83, 68, 59, 77]

const baseModules = [
  { path: '/app/dashboard' },
  { path: '/app/ai' },
  { path: '/app/marketing' },
  { path: '/app/products' },
  { path: '/app/stores' },
  { path: '/app/finance' },
]

const translations = {
  zh: {
    navAgents: '智能体',
    navOps: '运营模块',
    navStack: '技术栈',
    openWorkspace: '进入工作台',
    badge: '面向多门店团队的开源 AI 经营系统',
    heroTitle: '把门店数据变成可审批、可执行的经营动作。',
    heroBody: 'AuraSaaS 将 BI 看板、LangGraph 多智能体、RAG 经营知识库、人类审批和营销文案生成整合进一个可自托管的经营指挥中心。',
    launchDemo: '启动演示',
    viewGithub: '查看 GitHub',
    heroMetrics: [
      { value: '7', label: 'LangGraph 节点' },
      { value: '4', label: '门店演示网络' },
      { value: 'SSE', label: '流式智能体追踪' },
    ],
    previewKicker: '营收恢复',
    previewTitle: '上海静安门店',
    previewStatus: '等待审批',
    previewCards: [
      { label: '营收', value: '-12.8%', delta: '雨天 + 配送延迟', good: false },
      { label: '退款率', value: '+3.1%', delta: '包装问题', good: false },
      { label: '动作成本', value: '¥1,980', delta: '低于审批上限', good: true },
    ],
    signalGraph: '7 日经营信号',
    liveContext: '实时 BI 上下文',
    pipelineTitle: '智能体流水线',
    agents: [
      { name: '意图路由', note: '识别经营问题类型。', active: true },
      { name: '数据分析师', note: '拉取营收、SKU、毛利和异常信号。', active: true },
      { name: 'RAG 策略顾问', note: '先检索 SOP 和案例，再提出动作。', active: true },
      { name: '人工审批', note: '高风险活动进入明确审批门。', active: false },
      { name: '文案专家', note: '把通过审批的动作生成多渠道内容。', active: false },
    ],
    agentKicker: 'Agent-native 工作流',
    agentTitle: '不是黑盒聊天，而是可追踪的经营决策。',
    agentBody: '借鉴成熟开源智能体平台的模式：可观测、可审批、可回放、可本地运行。',
    features: [
      { short: 'BI', title: '经营看板', body: '多门店 KPI、SKU 健康、任务、活动和趋势分析集中在一个工作台。' },
      { short: 'AI', title: '智能体编排', body: 'LangGraph 工作流负责意图路由、数据分析、RAG 检索、风险评估和流式输出。' },
      { short: 'HITL', title: '审批控制', body: '高影响策略会先变成待审批任务，再进入执行或投放。' },
      { short: 'OBS', title: '追踪可见性', body: '智能体运行会保存为 trace，便于浏览、回放和后续评测。' },
    ],
    modules: [
      { ...baseModules[0], kicker: '指挥中心', name: 'Dashboard', desc: '实时经营概览和优先级任务。' },
      { ...baseModules[1], kicker: '智能副驾', name: 'AI Analysis', desc: '提问经营问题并观察每个智能体步骤。' },
      { ...baseModules[2], kicker: '增长', name: 'Marketing', desc: '从审批后的策略生成并管理营销活动。' },
      { ...baseModules[3], kicker: '商品', name: 'Products', desc: '追踪 SKU 销售、毛利、缺货和退款风险。' },
      { ...baseModules[4], kicker: '网络', name: 'Stores', desc: '跨市场比较门店表现。' },
      { ...baseModules[5], kicker: '财务', name: 'Finance', desc: '监控收入、利润、成本和 ROI。' },
    ],
  },
  en: {
    navAgents: 'Agents',
    navOps: 'Operations',
    navStack: 'Stack',
    openWorkspace: 'Open workspace',
    badge: 'Open-source AI operating system for multi-store teams',
    heroTitle: 'Turn store data into approved actions.',
    heroBody: 'AuraSaaS combines BI dashboards, LangGraph agents, RAG playbooks, human approvals, and marketing copy generation into a self-hosted business command center.',
    launchDemo: 'Launch demo',
    viewGithub: 'View GitHub',
    heroMetrics: [
      { value: '7', label: 'LangGraph nodes' },
      { value: '4', label: 'store demo network' },
      { value: 'SSE', label: 'streaming trace replay' },
    ],
    previewKicker: 'Revenue recovery',
    previewTitle: "Shanghai Jing'an store",
    previewStatus: 'Needs approval',
    previewCards: [
      { label: 'Revenue', value: '-12.8%', delta: 'rain + delivery delay', good: false },
      { label: 'Refund rate', value: '+3.1%', delta: 'packaging issue', good: false },
      { label: 'Action cost', value: '$276', delta: 'under approval cap', good: true },
    ],
    signalGraph: '7-day signal graph',
    liveContext: 'live BI context',
    pipelineTitle: 'Agent pipeline',
    agents: [
      { name: 'Intent Router', note: 'Classifies the operator question.', active: true },
      { name: 'Data Analyst', note: 'Pulls revenue, SKU, margin, and anomaly signals.', active: true },
      { name: 'RAG Strategist', note: 'Retrieves SOPs and playbooks before proposing actions.', active: true },
      { name: 'Human Approval', note: 'Keeps risky campaigns behind an explicit review gate.', active: false },
      { name: 'Copywriter', note: 'Turns approved actions into multi-channel copy.', active: false },
    ],
    agentKicker: 'Agent-native workflow',
    agentTitle: 'Built for traceable decisions, not black-box chat.',
    agentBody: 'Inspired by modern open-source agent platforms: observability, approval gates, replayable traces, and runnable local demos.',
    features: [
      { short: 'BI', title: 'Operational dashboards', body: 'Multi-store KPIs, SKU health, tasks, campaigns, and trend exploration in one workspace.' },
      { short: 'AI', title: 'Agent orchestration', body: 'A LangGraph workflow routes intent, analyzes data, retrieves SOPs, scores risk, and streams progress.' },
      { short: 'HITL', title: 'Approval control', body: 'High-impact strategy proposals become reviewable tasks before execution or campaign launch.' },
      { short: 'OBS', title: 'Trace visibility', body: 'Agent runs are stored for timeline browsing, replay, and future evaluation workflows.' },
    ],
    modules: [
      { ...baseModules[0], kicker: 'Command center', name: 'Dashboard', desc: 'Live business overview and prioritized tasks.' },
      { ...baseModules[1], kicker: 'Copilot', name: 'AI Analysis', desc: 'Ask operational questions and watch each agent step.' },
      { ...baseModules[2], kicker: 'Growth', name: 'Marketing', desc: 'Generate and manage campaigns from approved strategy.' },
      { ...baseModules[3], kicker: 'Merchandising', name: 'Products', desc: 'Track SKU sales, margin, stockout, and refund risk.' },
      { ...baseModules[4], kicker: 'Network', name: 'Stores', desc: 'Compare store performance across markets.' },
      { ...baseModules[5], kicker: 'Finance', name: 'Finance', desc: 'Monitor revenue, profit, costs, and ROI.' },
    ],
  },
}
</script>
