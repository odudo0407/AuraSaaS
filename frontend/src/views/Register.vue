<template>
  <div class="auth-shell min-h-screen overflow-hidden bg-[#fbfaf8] px-4 py-8 text-ink">
    <div class="auth-ribbon auth-ribbon-one"></div>
    <div class="auth-ribbon auth-ribbon-two"></div>

    <div class="relative z-10 mx-auto grid min-h-[calc(100vh-4rem)] max-w-1160px items-center gap-8 lg:grid-cols-[1fr_450px]">
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

        <div class="mt-10 rounded-3xl border border-white/70 bg-white/54 p-5 shadow-[0_14px_38px_rgba(34,34,34,0.08)] backdrop-blur-sm">
          <div class="mb-4 flex items-center justify-between">
            <span class="text-sm font-black">{{ copy.setupTitle }}</span>
            <span class="rounded-full bg-primary/10 px-3 py-1 text-xs font-black text-primary">{{ copy.setupBadge }}</span>
          </div>
          <div class="space-y-3">
            <div v-for="step in steps" :key="step" class="flex items-center gap-3 rounded-2xl bg-white/56 p-3">
              <span class="h-2.5 w-2.5 rounded-full bg-primary"></span>
              <span class="text-sm text-body">{{ step }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="auth-card rounded-3xl border border-white/70 bg-white/54 p-2 shadow-[0_28px_90px_rgba(34,34,34,0.13)] backdrop-blur-md">
        <div class="rounded-[20px] border border-white/70 bg-white/48 p-7 text-ink backdrop-blur-sm">
          <router-link to="/" class="mb-6 inline-flex items-center gap-3 text-ink no-underline lg:hidden">
            <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-ink text-sm font-black text-white">A</span>
            <span class="text-lg font-black">AuraSaaS</span>
          </router-link>

          <div class="mb-7">
            <div class="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-sm font-black text-white">01</div>
            <h2 class="text-3xl font-black">{{ copy.title }}</h2>
            <p class="mt-2 text-sm leading-6 text-muted">{{ copy.subtitle }}</p>
          </div>

          <form @submit.prevent="handleRegister" class="space-y-4">
            <label class="auth-field block rounded-2xl border border-hairline bg-white/62 p-3 transition">
              <span class="block text-xs font-black uppercase tracking-wide text-muted">{{ copy.name }}</span>
              <input v-model="form.username" type="text" autocomplete="name" :placeholder="copy.namePlaceholder" class="mt-2 w-full border-none bg-transparent text-base font-semibold text-ink outline-none" />
            </label>

            <label class="auth-field block rounded-2xl border border-hairline bg-white/62 p-3 transition">
              <span class="block text-xs font-black uppercase tracking-wide text-muted">{{ copy.email }}</span>
              <input v-model="form.email" type="email" autocomplete="email" :placeholder="copy.emailPlaceholder" class="mt-2 w-full border-none bg-transparent text-base font-semibold text-ink outline-none" />
            </label>

            <label class="auth-field block rounded-2xl border border-hairline bg-white/62 p-3 transition">
              <span class="block text-xs font-black uppercase tracking-wide text-muted">{{ copy.password }}</span>
              <input v-model="form.password" type="password" autocomplete="new-password" :placeholder="copy.passwordPlaceholder" class="mt-2 w-full border-none bg-transparent text-base font-semibold text-ink outline-none" />
            </label>

            <label class="auth-field block rounded-2xl border border-hairline bg-white/62 p-3 transition">
              <span class="block text-xs font-black uppercase tracking-wide text-muted">{{ copy.confirmPassword }}</span>
              <input v-model="form.confirmPassword" type="password" autocomplete="new-password" :placeholder="copy.confirmPasswordPlaceholder" class="mt-2 w-full border-none bg-transparent text-base font-semibold text-ink outline-none" />
            </label>

            <div v-if="error" class="rounded-2xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm font-semibold text-primary">
              {{ error }}
            </div>

            <button type="submit" :disabled="loading" class="h-13 w-full rounded-2xl bg-primary text-sm font-black text-white transition hover:bg-primary-active disabled:cursor-not-allowed disabled:opacity-50">
              {{ loading ? copy.loading : copy.submit }}
            </button>
          </form>

          <p class="mt-6 text-center text-sm text-muted">
            {{ copy.hasAccount }}
            <router-link to="/login" class="font-black text-primary no-underline hover:underline">{{ copy.signIn }}</router-link>
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
const form = reactive({ username: '', email: '', password: '', confirmPassword: '' })
const error = ref('')
const loading = ref(false)

const copy = computed(() => translations[language.value])
const steps = computed(() => copy.value.steps)

const translations = {
  zh: {
    badge: '自托管智能体演示',
    heroTitle: '创建你的 AI 经营工作台。',
    heroBody: '注册一个本地账号，体验 BI 看板、RAG 知识库、审批流和营销动作生成的完整工作流。',
    setupTitle: '工作台初始化',
    setupBadge: '快速开始',
    title: '创建账号',
    subtitle: '开启一个本地运营会话。',
    name: '姓名',
    namePlaceholder: 'Kenny',
    email: '邮箱',
    emailPlaceholder: 'operator@example.com',
    password: '密码',
    passwordPlaceholder: '至少 6 位字符',
    confirmPassword: '确认密码',
    confirmPasswordPlaceholder: '再次输入密码',
    submit: '创建账号',
    loading: '创建中...',
    hasAccount: '已经有账号？',
    signIn: '去登录',
    nameRequired: '请输入姓名。',
    emailRequired: '请输入邮箱。',
    emailInvalid: '请输入有效邮箱。',
    passwordInvalid: '密码至少 6 位。',
    passwordMismatch: '两次密码不一致。',
    steps: [
      '生成演示门店、KPI 和 SKU 信号',
      '通过 SSE 运行 LangGraph 智能体工作流',
      '在执行前审批策略建议',
    ],
  },
  en: {
    badge: 'Self-hosted agent demo',
    heroTitle: 'Create your AI operations workspace.',
    heroBody: 'Register a local account and explore the full BI, RAG, approval, and campaign workflow from one polished console.',
    setupTitle: 'Workspace setup',
    setupBadge: 'fast start',
    title: 'Create account',
    subtitle: 'Start a local operator session.',
    name: 'Name',
    namePlaceholder: 'Kenny',
    email: 'Email',
    emailPlaceholder: 'operator@example.com',
    password: 'Password',
    passwordPlaceholder: 'At least 6 characters',
    confirmPassword: 'Confirm password',
    confirmPasswordPlaceholder: 'Repeat your password',
    submit: 'Create account',
    loading: 'Creating account...',
    hasAccount: 'Already have an account?',
    signIn: 'Sign in',
    nameRequired: 'Name is required.',
    emailRequired: 'Email is required.',
    emailInvalid: 'Enter a valid email address.',
    passwordInvalid: 'Password must be at least 6 characters.',
    passwordMismatch: 'Passwords do not match.',
    steps: [
      'Seed demo stores, KPIs, and SKU signals',
      'Run LangGraph agent workflows through SSE',
      'Review strategy proposals before execution',
    ],
  },
}

async function handleRegister() {
  error.value = ''
  if (!form.username.trim()) {
    error.value = copy.value.nameRequired
    return
  }
  if (!form.email.trim()) {
    error.value = copy.value.emailRequired
    return
  }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) {
    error.value = copy.value.emailInvalid
    return
  }
  if (form.password.length < 6) {
    error.value = copy.value.passwordInvalid
    return
  }
  if (form.password !== form.confirmPassword) {
    error.value = copy.value.passwordMismatch
    return
  }

  loading.value = true
  try {
    await auth.register(form.username, form.email, form.password)
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
