<template>
  <div class="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-hairline bg-canvas p-3">
    <label class="flex items-center gap-2 text-sm font-medium text-ink">
      <input type="checkbox" class="h-4 w-4 accent-primary" :checked="allSelected" @change="$emit('toggle-all')" />
      {{ selectAllLabel }}
    </label>
    <span class="text-sm text-muted">{{ selectedLabel }}</span>
    <button
      :disabled="selectedCount === 0"
      class="rounded-lg bg-error-text px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
      @click="$emit('delete-selected')"
    >
      {{ deleteLabel }}
    </button>
    <button class="rounded-lg bg-surface-soft px-4 py-2 text-sm font-medium text-ink hover:bg-hairline" @click="$emit('cancel')">
      {{ cancelLabel }}
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  allSelected: {
    type: Boolean,
    default: false,
  },
  selectedCount: {
    type: Number,
    default: 0,
  },
  selectAllLabel: {
    type: String,
    default: 'Select all',
  },
  deleteLabel: {
    type: String,
    default: 'Delete selected',
  },
  cancelLabel: {
    type: String,
    default: 'Cancel',
  },
})

defineEmits(['toggle-all', 'delete-selected', 'cancel'])

const selectedLabel = computed(() => `${props.selectedCount} selected`)
</script>

