<template>
  <div
    class="mb-3 overflow-hidden transition-all"
    :style="{ borderLeft: `3px solid ${accentColor}`, borderRadius: '0 14px 14px 0', background: '#f7f7f7' }"
  >
    <div class="flex items-center justify-between px-5 py-3.5 cursor-pointer select-none" @click="open = !open">
      <div class="flex items-center gap-2.5">
        <span class="text-lg">{{ icon }}</span>
        <span class="text-base font-semibold text-ink">{{ title }}</span>
      </div>
      <span class="text-xs text-muted-soft transition-transform duration-200"
        :style="{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }">▼</span>
    </div>
    <div v-if="open && content" class="px-5 pb-5 text-base leading-relaxed text-body whitespace-pre-wrap">
      {{ content }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({
  icon: String, title: String, content: String,
  defaultOpen: { type: Boolean, default: false },
  accentColor: { type: String, default: '#ff385c' },
})
const open = ref(props.defaultOpen)
</script>
