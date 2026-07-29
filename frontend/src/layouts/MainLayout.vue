<template>
  <div class="h-screen overflow-hidden bg-[#f5f4f0]">
    <!-- Transparent trigger zone — active only when header is hidden -->
    <div
      class="fixed top-0 left-0 right-0 h-16 transition-[z-index] duration-300"
      :class="headerHidden ? 'z-50 pointer-events-auto' : 'z-0 pointer-events-none'"
      @mouseenter="onTriggerEnter"
    />

    <header
      ref="headerRef"
      class="fixed top-0 left-0 right-0 flex h-16 items-center border-b border-hairline bg-white px-6 transition-transform duration-300"
      :class="headerHidden ? 'z-40 pointer-events-none' : 'z-50'"
      :style="{ transform: headerHidden ? 'translateY(-100%)' : 'translateY(0)' }"
      @mouseleave="onHeaderLeave"
    >
      <!-- Logo -->
      <router-link to="/" class="flex items-center gap-3 text-ink no-underline shrink-0">
        <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-ink text-sm font-bold text-white">A</span>
        <span class="text-lg font-bold hidden sm:inline">AuraSaaS</span>
      </router-link>

      <!-- Nav (centered) -->
      <nav class="hidden items-center gap-3 lg:flex flex-1 justify-center">
        <router-link
          v-for="item in primaryNav"
          :key="item.path"
          :to="item.path"
          class="rounded-lg px-4 py-2 text-sm font-bold no-underline transition !bg-transparent"
          :class="isActive(item) ? 'text-primary' : 'text-muted hover:text-ink'"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <!-- Right controls -->
      <div class="flex items-center gap-3 shrink-0">
        <!-- Search -->
        <div ref="searchRef" class="relative hidden md:flex">
          <div class="relative">
            <input
              v-model="keyword"
              type="text"
              :placeholder="placeholder"
              class="w-80 max-w-full rounded-lg border border-hairline bg-[#f5f4f0] py-2 pl-3 pr-8 text-sm text-ink outline-none transition focus:border-ink"
              @focus="onSearchFocus"
            />
            <button
              v-if="keyword"
              class="absolute right-1.5 top-1/2 -translate-y-1/2 rounded px-1 py-0.5 text-xs font-bold text-muted hover:text-ink transition"
              @click="clearSearch"
            >
              &times;
            </button>
          </div>

          <!-- Search results dropdown -->
          <div
            v-show="searchOpen && results.length"
            class="absolute left-0 top-full mt-1 w-120 max-w-[calc(100vw-3rem)] max-h-80 overflow-y-auto rounded-lg border border-hairline bg-white shadow-lg z-50"
          >
            <div v-for="group in results" :key="group.category">
              <div class="sticky top-0 px-3 py-1.5 text-xs font-bold text-muted bg-[#f5f4f0] border-b border-hairline-soft">
                {{ group.label }} ({{ group.items.length }})
              </div>
              <div
                v-for="item in group.items"
                :key="item.id"
                class="px-4 py-2.5 cursor-pointer hover:bg-[#f5f4f0] transition border-b border-hairline-soft last:border-b-0"
                @mousedown.prevent
                @click="handleSearchClick(item, group.category)"
              >
                <div class="text-sm font-semibold text-ink">{{ item.name }}</div>
                <div class="text-xs text-muted mt-0.5">
                  <template v-if="group.category === 'users'">{{ item.role }} · {{ item.department }} · {{ item.email }}</template>
                  <template v-else-if="group.category === 'products'">&yen;{{ item.price }} · {{ item.sku }} · {{ language === 'zh' ? '库存' : 'Stock' }} {{ item.stock }} · {{ language === 'zh' ? '销量' : 'Sales' }} {{ item.sales }}</template>
                  <template v-else-if="group.category === 'stores'">{{ item.manager }} · {{ item.area }} · {{ language === 'zh' ? '日营收' : 'Daily' }} &yen;{{ item.dailyRevenue }}</template>
                  <template v-else-if="group.category === 'reports'">{{ item.type }} · {{ item.author }} · {{ item.updatedAt }} · {{ item.status }}</template>
                  <template v-else-if="group.category === 'campaigns'">{{ item.type }} · {{ language === 'zh' ? '预算' : 'Budget' }} &yen;{{ item.budget }} · ROI {{ item.roi }} · {{ item.startDate }} ~ {{ item.endDate }}</template>
                </div>
              </div>
            </div>
          </div>

          <!-- No results -->
          <div
            v-show="searchOpen && keyword && !results.length"
            class="absolute left-0 top-full mt-1 w-80 rounded-lg border border-hairline bg-white p-4 text-center text-sm text-muted shadow-lg z-50"
          >
            {{ language === 'zh' ? '未找到相关结果' : 'No results found' }}
          </div>
        </div>

        <!-- Notifications -->
        <div ref="notifRef" class="relative">
          <button
            @click="toggleNotif"
            class="relative flex h-10 w-10 items-center justify-center rounded-lg border border-hairline bg-white text-sm font-bold text-ink transition hover:border-ink"
            :title="copy.refreshNotifications"
          >
            {{ copy.notificationShort }}
            <span
              v-if="unreadCount"
              class="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-white"
            >
              {{ unreadCount }}
            </span>
          </button>

          <!-- Notification dropdown -->
          <Transition name="dropdown">
            <div v-if="notifOpen" class="absolute right-0 top-full mt-2 w-80 rounded-lg border border-hairline bg-white shadow-lg z-50">
              <div class="px-4 py-2.5 border-b border-hairline text-sm font-bold text-ink">
                {{ language === 'zh' ? '通知' : 'Notifications' }}
                <span class="text-xs text-muted font-normal ml-2">{{ unreadCount }} {{ language === 'zh' ? '条未读' : 'unread' }}</span>
              </div>
              <div class="max-h-80 overflow-y-auto">
                <div
                  v-for="item in displayList"
                  :key="item.id"
                  class="px-4 py-3 border-b border-hairline-soft last:border-b-0 cursor-pointer hover:bg-[#f5f4f0] transition"
                  :class="{ 'bg-primary/[0.03]': !item.isRead }"
                  @click="clickNotifItem(item)"
                >
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-1.5">
                        <span v-if="!item.isRead" class="inline-block w-2 h-2 rounded-full bg-primary shrink-0"></span>
                        <span class="text-sm font-semibold text-ink truncate">{{ item.displayTitle }}</span>
                      </div>
                      <div class="text-xs text-muted mt-1 ml-3.5">{{ item.displayTime }}</div>
                    </div>
                    <button
                      v-if="!item.isRead"
                      class="shrink-0 rounded-md px-2.5 py-1 text-xs font-bold text-primary hover:bg-primary/10 transition"
                      @click.stop="markAsRead(item.id)"
                    >
                      {{ language === 'zh' ? '标记已读' : 'Mark read' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <!-- User dropdown -->
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

        <!-- Language switcher -->
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

    <main
      ref="mainRef"
      class="h-full overflow-y-auto"
      :style="{ paddingTop: headerHidden ? '0px' : '64px', transition: 'padding-top 0.3s ease' }"
    >
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useLanguage } from '../utils/language'
import { useSearch } from '../composables/useSearch'
import { useNotification } from '../composables/useNotification'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { language, setLanguage } = useLanguage()

const {
  keyword, results, isOpen: searchOpen, placeholder,
  search, clear: clearSearch, clickItem: getSearchRoute, close: closeSearch
} = useSearch()

const {
  isOpen: notifOpen, unreadCount, displayList,
  toggle: toggleNotif, close: closeNotif, markAsRead, clickItem: clickNotifItem
} = useNotification()

const openUser = ref(false)
const userDropdownRef = ref(null)
const searchRef = ref(null)
const notifRef = ref(null)
const headerRef = ref(null)
const mainRef = ref(null)
const headerHidden = ref(false)
let lastScrollY = 0
let scrollDirection = 'up'

function getScrollTop() {
  return mainRef.value?.scrollTop ?? 0
}

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
    refreshNotifications: '通知',
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
    refreshNotifications: 'Notifications',
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

function onSearchFocus() {
  if (keyword.value) {
    search()
  }
}

function handleSearchClick(item, category) {
  const route = getSearchRoute(item, category)
  if (route) {
    router.push(route)
  }
}

function handleLogout() {
  auth.logout()
  openUser.value = false
  router.push('/login')
}

function onScroll() {
  const currentY = getScrollTop()
  if (currentY <= 50) {
    headerHidden.value = false
  } else if (currentY > lastScrollY) {
    scrollDirection = 'down'
    headerHidden.value = true
  } else if (currentY < lastScrollY) {
    scrollDirection = 'up'
    headerHidden.value = false
  }
  lastScrollY = currentY
}

function onTriggerEnter() {
  headerHidden.value = false
  scrollDirection = 'up'
}

function onHeaderLeave() {
  if (getScrollTop() > 50 && scrollDirection === 'down') {
    headerHidden.value = true
  }
}

function handleClickOutside(event) {
  if (userDropdownRef.value && !userDropdownRef.value.contains(event.target)) {
    openUser.value = false
  }
  if (searchRef.value && !searchRef.value.contains(event.target)) {
    closeSearch()
  }
  if (notifRef.value && !notifRef.value.contains(event.target)) {
    closeNotif()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  mainRef.value?.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  mainRef.value?.removeEventListener('scroll', onScroll)
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
