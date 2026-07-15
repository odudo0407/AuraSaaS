<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-200 flex items-center justify-center bg-black/40">
        <div class="w-90 rounded-2xl bg-white p-6 shadow-xl">
          <h3 class="mb-2 text-base font-semibold text-ink">确认批量删除</h3>
          <p class="mb-6 text-sm leading-6 text-muted">
            将永久删除已勾选的 {{ count }} 条{{ entityName }}记录，此操作不可撤销。
          </p>
          <div class="flex justify-end gap-3">
            <button
              @click="$emit('cancel')"
              class="rounded-lg bg-surface-soft px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-hairline"
            >
              取消
            </button>
            <button
              @click="$emit('confirm')"
              :disabled="loading"
              class="rounded-lg bg-error-text px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {{ loading ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  open: { type: Boolean, default: false },
  count: { type: Number, default: 0 },
  entityName: { type: String, default: '数据' },
  loading: { type: Boolean, default: false },
})

defineEmits(['confirm', 'cancel'])
</script>

<style scoped>
.fade-enter-active { animation: fadeIn 0.2s ease; }
.fade-leave-active { animation: fadeIn 0.15s ease reverse; }
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
