<template>
  <aside class="hidden w-280px shrink-0 border-r border-hairline bg-white p-4 lg:flex lg:flex-col">
    <button @click="$emit('newChat')" class="mb-4 h-10 rounded-lg bg-ink text-sm font-bold text-white transition hover:bg-body">
      {{ copy.newAnalysis }}
    </button>
    <div class="mb-4 rounded-lg border border-hairline bg-[#fbfaf8] p-4">
      <div class="text-xs font-bold uppercase text-muted">{{ copy.selectedStore }}</div>
      <button @click="showDropdown = !showDropdown" class="mt-3 w-full rounded-lg border border-hairline bg-white px-3 py-2 text-left text-sm font-bold text-ink">
        {{ selectedName || copy.allStores }}
      </button>
      <div v-if="showDropdown" class="mt-2 overflow-hidden rounded-lg border border-hairline bg-white">
        <button @click="$emit('selectStore', null)" class="block w-full px-3 py-2 text-left text-xs hover:bg-[#f5f4f0]">{{ copy.allStores }}</button>
        <button v-for="s in stores" :key="s.id" @click="$emit('selectStore', s)" class="block w-full px-3 py-2 text-left text-xs hover:bg-[#f5f4f0]">{{ s.name }}</button>
      </div>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto">
      <div class="mb-2 flex items-center justify-between">
        <span class="text-xs font-bold uppercase text-muted">{{ copy.traceHistory }}</span>
        <button v-if="history.length > 0" @click="$emit('clearAll')" class="text-xs text-muted hover:text-error-text">{{ copy.clearAll }}</button>
      </div>
      <div v-if="history.length === 0" class="rounded-lg border border-dashed border-hairline p-4 text-xs leading-5 text-muted">{{ copy.noHistory }}</div>
      <div v-for="chat in history" :key="chat.id" class="group relative mb-2 w-full">
        <button @click="$emit('loadChat', chat)" class="w-full rounded-lg border p-3 text-left transition pr-8" :class="currentId === chat.id ? 'border-primary bg-primary/10' : 'border-hairline bg-[#fbfaf8] hover:border-ink'">
          <div class="truncate text-sm font-bold text-ink">{{ chat.title }}</div>
          <div class="mt-1 text-xs text-muted">{{ chat.time }}</div>
        </button>
        <button @click.stop="$emit('deleteChat', chat.id)" class="absolute right-2 top-3 hidden h-6 w-6 items-center justify-center rounded text-muted hover:bg-error-text/10 hover:text-error-text group-hover:flex">
          ×
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
defineProps(['copy', 'stores', 'selectedName', 'history', 'currentId'])
defineEmits(['newChat', 'selectStore', 'loadChat', 'deleteChat', 'clearAll'])
const showDropdown = ref(false)
</script>
