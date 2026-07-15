<template>
  <div class="flex h-screen flex-col overflow-hidden bg-[#f5f4f0]">
    <header class="z-40 flex h-16 shrink-0 items-center border-b border-hairline bg-white px-6">
      <router-link to="/" class="mr-8 flex items-center gap-3 text-ink no-underline">
        <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-ink text-sm font-bold text-white">A</span>
        <span class="text-lg font-bold">AuraSaaS</span>
      </router-link>

      <nav class="hidden items-center gap-1 lg:flex">
        <router-link
          v-for="item in primaryNav"
          :key="item.path"
          :to="item.path"
          class="rounded-lg px-3 py-2 text-sm font-bold no-underline transition"
          :class="isActive(item) ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-[#f5f4f0] hover:text-ink'"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <div class="flex-1"></div>

      <div class="flex items-center gap-3">
        <div class="hidden items-center rounded-lg border border-hairline bg-[#f5f4f0] px-3 py-2 md:flex">
          <span class="text-xs text-muted">{{ copy.search }}</span>
          <span class="ml-8 rounded border border-hairline bg-white px-1.5 py-0.5 text-[10px] font-bold text-muted">/</span>
        </div>

        <button
          @click="refreshNotifications"
          class="relative flex h-10 w-10 items-center justify-center rounded-lg border border-hairline bg-white text-sm font-bold text-ink transition hover:border-ink"
          :title="copy.refreshNotifications"
        >
          {{ copy.notificationShort }}
          <span
            v-if="notifications.length"
            class="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-white"
          >
            {{ notifications.length }}
          </span>
        </button>

        <div class="relative" ref="userDropdownRef">
          <button
            @click="openUser = !openUser"
            class="flex h-10 w-10 items-center justify-center rounded-lg bg-ink text-sm font-bold text-white"
            :title="copy.userMenu"
          >
            {{ auth.user?.username?.[0]?.toUpperCase() || 'U' }}
          </button>
          <Transition name="dropdown">
            <div v-if="openUser" class="absolute right-0 top-full mt-2 w-48 rounded-lg border border-hairline bg-white p-2 shadow-lg">
              <div class="border-b border-hairline-soft px-3 py-2">
                <div class="text-sm font-bold text-ink">{{ auth.user?.username || copy.operator }}</div>
                <div class="truncate text-xs text-muted">{{ auth.user?.email || copy.localSession }}</div>
              </div>
              <router-link
                to="/app/settings"
                class="mt-1 block rounded-md px-3 py-2 text-sm font-semibold text-ink no-underline hover:bg-[#f5f4f0]"
                @click="openUser = false"
              >
                {{ copy.settings }}
              </router-link>
              <button
                @click="handleLogout"
                class="w-full rounded-md px-3 py-2 text-left text-sm font-semibold text-primary hover:bg-primary/10"
              >
                {{ copy.logout }}
              </button>
            </div>
          </Transition>
        </div>

        <div class="hidden rounded-lg border border-hairline bg-white p-1 md:flex">
          <button
            v-for="option in languageOptions"
            :key="option.value"
            @click="setLanguage(option.value)"
            class="h-8 rounded-md px-2.5 text-xs font-black transition"
            :class="language === option.value ? 'bg-ink text-white' : 'text-muted hover:bg-[#f5f4f0] hover:text-ink'"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
    </header>

    <main class="flex-1 overflow-y-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { request } from '../utils/request'
import { useLanguage } from '../utils/language'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { language, setLanguage } = useLanguage()
const notifications = ref([])
const openUser = ref(false)
const userDropdownRef = ref(null)

const languageOptions = [
  { value: 'zh', label: '中' },
  { value: 'en', label: 'EN' },
]

const copy = computed(() => translations[language.value])
const primaryNav = computed(() => copy.value.primaryNav)

const translations = {
  zh: {
    search: '搜索',
    notificationShort: '通',
    refreshNotifications: '刷新通知',
    userMenu: '用户菜单',
    operator: '运营人员',
    localSession: '本地演示会话',
    settings: '系统设置',
    logout: '退出登录',
    primaryNav: [
      { path: '/app/dashboard', label: '工作台' },
      { path: '/app/ai', label: 'AI 分析' },
      { path: '/app/reports', label: '报表' },
      { path: '/app/products', label: '商品' },
      { path: '/app/staff', label: '人员' },
      { path: '/app/stores', label: '门店' },
      { path: '/app/marketing', label: '营销' },
      { path: '/app/finance', label: '财务' },
    ],
  },
  en: {
    search: 'Search',
    notificationShort: 'N',
    refreshNotifications: 'Refresh notifications',
    userMenu: 'User menu',
    operator: 'Operator',
    localSession: 'Local demo session',
    settings: 'Settings',
    logout: 'Log out',
    primaryNav: [
      { path: '/app/dashboard', label: 'Dashboard' },
      { path: '/app/ai', label: 'AI Analysis' },
      { path: '/app/reports', label: 'Reports' },
      { path: '/app/products', label: 'Products' },
      { path: '/app/staff', label: 'Staff' },
      { path: '/app/stores', label: 'Stores' },
      { path: '/app/marketing', label: 'Marketing' },
      { path: '/app/finance', label: 'Finance' },
    ],
  },
}

function isActive(item) {
  return route.path === item.path
}

async function refreshNotifications() {
  try {
    const res = await request('/api/tasks?status=pending&limit=10')
    notifications.value = res.data || []
  } catch {
    notifications.value = []
  }
}

function handleLogout() {
  auth.logout()
  openUser.value = false
  router.push('/login')
}

function handleClickOutside(event) {
  if (userDropdownRef.value && !userDropdownRef.value.contains(event.target)) {
    openUser.value = false
  }
}

onMounted(() => {
  refreshNotifications()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
