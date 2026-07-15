<template>
  <div class="auth-shell min-h-screen overflow-hidden bg-[#fbfaf8] px-4 py-8 text-ink">
    <div class="auth-ribbon auth-ribbon-one"></div>
    <div class="auth-ribbon auth-ribbon-two"></div>

    <div class="relative z-10 mx-auto grid min-h-[calc(100vh-4rem)] max-w-1160px items-center gap-8 lg:grid-cols-[1fr_430px]">
      <section class="hidden lg:block">
        <router-link to="/" class="mb-10 inline-flex items-center gap-3 text-ink no-underline">
          <span class="flex h-11 w-11 items-center justify-center rounded-xl bg-ink text-base font-black text-white">A</span>
          <span class="text-xl font-black">AuraSaaS</span>
        </router-link>

        <p class="mb-4 inline-flex rounded-full border border-primary/20 bg-white/60 px-4 py-2 text-xs font-bold uppercase tracking-wide text-primary backdrop-blur-sm">
          {{ copy.badge }}
        </p>
        <h1 class="max-w-680px text-6xl font-black leading-[1.02] tracking-normal text-ink">
          {{ copy.heroTitle }}
        </h1>
        <p class="mt-6 max-w-600px text-base leading-8 text-muted">
          {{ copy.heroBody }}
        </p>

        <div class="mt-10 grid max-w-720px grid-cols-3 gap-4">
          <article v-for="item in benefits" :key="item.title" class="soft-glass rounded-2xl p-5">
            <div class="text-xs font-black uppercase tracking-wide text-primary">{{ item.kicker }}</div>
            <div class="mt-3 text-lg font-black text-ink">{{ item.title }}</div>
            <p class="mt-2 text-sm leading-6 text-muted">{{ item.body }}</p>
          </article>
        </div>
      </section>

      <section class="auth-card rounded-3xl border border-white/70 bg-white/54 p-2 shadow-[0_28px_90px_rgba(34,34,34,0.13)] backdrop-blur-md">
        <div class="rounded-[20px] border border-white/70 bg-white/48 p-7 text-ink backdrop-blur-sm">
          <router-link to="/" class="mb-6 inline-flex items-center gap-3 text-ink no-underline lg:hidden">
            <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-ink text-sm font-black text-white">A</span>
            <span class="text-lg font-black">AuraSaaS</span>
          </router-link>

          <div class="mb-7">
            <div class="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-ink text-sm font-black text-white">AI</div>
            <h2 class="text-3xl font-black">{{ copy.title }}</h2>
            <p class="mt-2 text-sm leading-6 text-muted">{{ copy.subtitle }}</p>
          </div>

          <form @submit.prevent="handleLogin" class="space-y-4">
            <label class="auth-field block rounded-2xl border border-hairline bg-white/62 p-3 transition">
              <span class="block text-xs font-black uppercase tracking-wide text-muted">{{ copy.email }}</span>
              <input v-model="form.email" type="email" autocomplete="email" :placeholder="copy.emailPlaceholder" class="mt-2 w-full border-none bg-transparent text-base font-semibold text-ink outline-none" />
            </label>

            <label class="auth-field block rounded-2xl border border-hairline bg-white/62 p-3 transition">
              <span class="block text-xs font-black uppercase tracking-wide text-muted">{{ copy.password }}</span>
              <input v-model="form.password" type="password" autocomplete="current-password" :placeholder="copy.passwordPlaceholder" class="mt-2 w-full border-none bg-transparent text-base font-semibold text-ink outline-none" />
            </label>

            <div v-if="error" class="rounded-2xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm font-semibold text-primary">
              {{ error }}
            </div>

            <button type="submit" :disabled="loading" class="h-13 w-full rounded-2xl bg-primary text-sm font-black text-white transition hover:bg-primary-active disabled:cursor-not-allowed disabled:opacity-50">
              {{ loading ? copy.loading : copy.submit }}
            </button>
          </form>

          <div class="mt-6 rounded-2xl border border-white/70 bg-white/44 p-4">
            <div class="flex items-center justify-between text-xs">
              <span class="font-black uppercase text-muted">{{ copy.readiness }}</span>
              <span class="font-black text-[#16a34a]">{{ copy.online }}</span>
            </div>
            <div class="mt-3 grid grid-cols-3 gap-2 text-center">
              <div v-for="metric in readiness" :key="metric.label" class="rounded-xl bg-white/60 px-2 py-3">
                <div class="text-sm font-black">{{ metric.value }}</div>
                <div class="mt-1 text-[10px] font-bold uppercase text-muted">{{ metric.label }}</div>
              </div>
            </div>
          </div>

          <p class="mt-6 text-center text-sm text-muted">
            {{ copy.noAccount }}
            <router-link to="/register" class="font-black text-primary no-underline hover:underline">{{ copy.createOne }}</router-link>
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useLanguage } from '../utils/language'

const router = useRouter()
const auth = useAuthStore()
const { language } = useLanguage()
const form = reactive({ email: '', password: '' })
const error = ref('')
const loading = ref(false)

const copy = computed(() => translations[language.value])
const benefits = computed(() => copy.value.benefits)

const readiness = [
  { value: '7', label: 'nodes' },
  { value: 'SSE', label: 'stream' },
  { value: 'RAG', label: 'ready' },
]

const translations = {
  zh: {
    badge: '智能经营指挥中心',
    heroTitle: '登录后观察你的智能体如何思考。',
    heroBody: '进入实时 BI、LangGraph trace、RAG 经营知识库和审批工作流构成的自托管经营工作台。',
    title: '欢迎回来',
    subtitle: '登录并继续你的本地运营会话。',
    email: '邮箱',
    emailPlaceholder: 'operator@example.com',
    password: '密码',
    passwordPlaceholder: '输入密码',
    submit: '登录',
    loading: '登录中...',
    readiness: '演示状态',
    online: '在线',
    noAccount: '还没有账号？',
    createOne: '立即创建',
    emailRequired: '请输入邮箱。',
    passwordRequired: '请输入密码。',
    benefits: [
      { kicker: 'Trace', title: '可回放运行', body: '每个智能体步骤都可见、可保存、可复盘。' },
      { kicker: 'RAG', title: '有依据的建议', body: '策略引用经营知识库，而不是泛泛回答。' },
      { kicker: 'HITL', title: '审批闸门', body: '高风险动作会等待运营人员确认。' },
    ],
  },
  en: {
    badge: 'Agentic business command center',
    heroTitle: 'Sign in to watch your agents think.',
    heroBody: 'Explore live BI signals, traceable LangGraph runs, RAG-backed playbooks, and approval gates from a polished self-hosted workspace.',
    title: 'Welcome back',
    subtitle: 'Sign in to continue your local operator session.',
    email: 'Email',
    emailPlaceholder: 'operator@example.com',
    password: 'Password',
    passwordPlaceholder: 'Enter your password',
    submit: 'Sign in',
    loading: 'Signing in...',
    readiness: 'Demo readiness',
    online: 'online',
    noAccount: 'No account yet?',
    createOne: 'Create one',
    emailRequired: 'Email is required.',
    passwordRequired: 'Password is required.',
    benefits: [
      { kicker: 'Trace', title: 'Replay runs', body: 'Every agent step is visible, stored, and reviewable.' },
      { kicker: 'RAG', title: 'Grounded advice', body: 'Strategies cite playbooks instead of generic guesses.' },
      { kicker: 'HITL', title: 'Approval gates', body: 'Risky actions wait for an operator decision.' },
    ],
  },
}

async function handleLogin() {
  error.value = ''
  if (!form.email.trim()) {
    error.value = copy.value.emailRequired
    return
  }
  if (!form.password) {
    error.value = copy.value.passwordRequired
    return
  }

  loading.value = true
  try {
    await auth.login(form.email, form.password)
    router.push('/app/dashboard')
  } catch (event) {
    error.value = event.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-shell {
  position: relative;
  isolation: isolate;
}

.auth-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(34,34,34,0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34,34,34,0.035) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(to bottom, black, transparent 88%);
}

.auth-ribbon {
  position: absolute;
  border-radius: 999px;
  pointer-events: none;
}

.auth-ribbon-one {
  left: -14%;
  top: 10%;
  width: 58%;
  height: 34%;
  background: linear-gradient(90deg, rgba(255,56,92,0.18), rgba(255,255,255,0));
  transform: rotate(-14deg);
}

.auth-ribbon-two {
  right: -18%;
  bottom: 8%;
  width: 62%;
  height: 34%;
  background: linear-gradient(90deg, rgba(34,34,34,0.09), rgba(255,56,92,0.11), rgba(255,255,255,0));
  transform: rotate(-16deg);
}

.soft-glass {
  border: 1px solid rgba(255,255,255,0.72);
  background: rgba(255,255,255,0.58);
  backdrop-filter: blur(10px);
  box-shadow: 0 14px 38px rgba(34,34,34,0.08);
}

.auth-card {
  animation: cardIn 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.auth-field:focus-within {
  border-color: #222222;
  box-shadow: 0 0 0 4px rgba(34,34,34,0.07);
}

@keyframes cardIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
