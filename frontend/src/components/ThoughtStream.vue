<template>
  <div class="thought-stream">
    <!-- Thinking chain header -->
    <div v-if="thinkContent" class="mb-3">
      <div class="flex items-center gap-2 mb-2 cursor-pointer" @click="thinkExpanded = !thinkExpanded">
        <span class="text-xs font-medium"
          :class="thinkExpanded ? 'text-primary' : 'text-muted'">
          {{ thinkExpanded ? '🔽 推理过程' : '▶ 推理过程' }}
        </span>
        <span class="text-xs text-muted-soft">{{ thinkCharCount }} 字</span>
      </div>
      <div v-if="thinkExpanded"
        class="bg-surface-soft border border-hairline rounded-xl p-4 text-xs text-muted leading-relaxed max-h-300px overflow-y-auto whitespace-pre-wrap font-mono">
        {{ thinkContent }}
      </div>
    </div>

    <!-- Main content with typing animation -->
    <div ref="contentEl" class="text-sm text-ink leading-relaxed whitespace-pre-wrap" v-html="renderedContent"></div>

    <!-- Streaming cursor -->
    <span v-if="streaming" class="inline-block w-2 h-4 bg-primary ml-0.5 align-text-bottom animate-pulse"></span>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { renderMarkdown } from '../utils/markdown.js'

const props = defineProps({
  thinkContent: { type: String, default: '' },
  content: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
})

const thinkExpanded = ref(false)
const contentEl = ref(null)

const thinkCharCount = computed(() => {
  return props.thinkContent ? props.thinkContent.length : 0
})

const renderedContent = computed(() => {
  return renderMarkdown(props.content || '')
})

// Auto-expand thinking when streaming
watch(() => props.streaming, (val) => {
  if (val && props.thinkContent) {
    thinkExpanded.value = true
  }
})

// Auto-scroll content
watch(() => props.content, () => {
  nextTick(() => {
    if (contentEl.value) {
      contentEl.value.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  })
})
</script>

<style scoped>
.thought-stream {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.animate-pulse {
  animation: blink 0.8s ease-in-out infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
