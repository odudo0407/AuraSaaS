import { computed, ref } from 'vue'

export function useBatchSelection(itemsRef, getId = (item) => item.id) {
  const isBatchMode = ref(false)
  const selectedIds = ref([])

  const itemIds = computed(() => (itemsRef.value || []).map(getId).filter((id) => id !== undefined && id !== null))
  const selectedCount = computed(() => selectedIds.value.length)
  const allSelected = computed(() => itemIds.value.length > 0 && itemIds.value.every((id) => selectedIds.value.includes(id)))

  function enterBatchMode() {
    isBatchMode.value = true
    selectedIds.value = []
  }

  function exitBatchMode() {
    isBatchMode.value = false
    selectedIds.value = []
  }

  function toggleBatchMode() {
    if (isBatchMode.value) exitBatchMode()
    else enterBatchMode()
  }

  function isSelected(id) {
    return selectedIds.value.includes(id)
  }

  function toggleItem(id) {
    if (isSelected(id)) {
      selectedIds.value = selectedIds.value.filter((selectedId) => selectedId !== id)
    } else {
      selectedIds.value = [...selectedIds.value, id]
    }
  }

  function toggleAll() {
    selectedIds.value = allSelected.value ? [] : [...itemIds.value]
  }

  return {
    isBatchMode,
    selectedIds,
    selectedCount,
    allSelected,
    enterBatchMode,
    exitBatchMode,
    toggleBatchMode,
    isSelected,
    toggleItem,
    toggleAll,
  }
}
