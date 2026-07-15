<template>
  <div class="flex items-center gap-2">
    <span class="text-xs text-muted-soft">{{ copy.storeLabel }}</span>
    <div class="relative">
      <select v-model="selected" @change="onChange"
        class="bg-surface-soft border border-hairline rounded-lg px-3 py-1.5 text-sm text-ink outline-none appearance-none pr-8 cursor-pointer">
        <option :value="null">{{ copy.allStores }}</option>
        <option v-for="s in storeList" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <span class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-soft pointer-events-none">▼</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { request } from '../utils/request'
import { useLanguage } from '../utils/language'

const emit = defineEmits(['change'])
const { language } = useLanguage()
const selected = ref(null)
const storeList = ref([])
const copy = computed(() => translations[language.value])

const translations = {
  zh: {
    storeLabel: '门店',
    allStores: '全国门店',
  },
  en: {
    storeLabel: 'Store',
    allStores: 'All stores',
  },
}

async function loadStores() {
  try {
    const res = await request('/api/dashboard/stores')
    storeList.value = res.data || []
  } catch { storeList.value = [] }
}

function onChange() {
  emit('change', selected.value)
}

onMounted(loadStores)
</script>
