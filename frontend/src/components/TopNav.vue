<template>
  <nav class="h-20 bg-canvas border-b border-hairline flex items-center justify-between px-12 sticky top-0 z-50">
    <!-- Left: Logo + Nav -->
    <div class="flex items-center gap-12">
      <router-link to="/" class="text-primary text-xl font-bold tracking-tight select-none">
        ◆ AuraSaaS
      </router-link>
      <div class="flex gap-8">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex flex-col items-center gap-1.5 py-2 cursor-pointer"
        >
          <span
            class="text-base font-semibold transition-colors"
            :class="$route.path === item.path ? 'text-ink' : 'text-muted hover:text-ink'"
          >
            {{ item.label }}
          </span>
          <div
            class="w-full h-0.5 rounded-sm transition-all"
            :class="$route.path === item.path ? 'bg-ink' : 'bg-transparent'"
          />
        </router-link>
      </div>
    </div>

    <!-- Right: Clock + Avatar -->
    <div class="flex items-center gap-4">
      <span class="text-muted-soft text-sm">{{ clock }}</span>
      <div
        class="w-10 h-10 rounded-full bg-ink flex items-center justify-center text-white font-semibold text-sm cursor-pointer select-none"
      >
        K
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const navItems = [
  { path: '/', label: 'Dashboard' },
  { path: '/app/ai', label: 'AI Analysis' },
  { path: '/app/marketing', label: 'Marketing' },
]

const clock = ref('')
let timer

function updateClock() {
  clock.value = new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

onMounted(() => {
  updateClock()
  timer = setInterval(updateClock, 1000)
})

onUnmounted(() => clearInterval(timer))
</script>
