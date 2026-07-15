<template>
  <div class="bg-canvas border border-hairline rounded-3.5 p-5 mb-3">
    <div class="flex items-center justify-between mb-3.5">
      <div class="flex items-center gap-2">
        <span class="text-lg">{{ icon }}</span>
        <span class="text-sm font-semibold text-ink">{{ channel }}</span>
      </div>
      <button @click="copy"
        class="bg-primary text-white border-none px-4 py-1.5 rounded-full text-sm font-medium cursor-pointer hover:bg-primary-active transition-colors">
        {{ copied ? '已复制 ✓' : '复制' }}
      </button>
    </div>
    <div class="text-base leading-relaxed text-body whitespace-pre-wrap">{{ content }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({ channel: String, content: String, icon: String })
const copied = ref(false)
function copy() {
  navigator.clipboard.writeText(props.content).then(() => {
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  })
}
</script>
