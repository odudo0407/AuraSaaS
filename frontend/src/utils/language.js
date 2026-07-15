import { computed, ref, watch } from 'vue'

const language = ref(localStorage.getItem('aurasaas_lang') || 'zh')

watch(language, (value) => {
  localStorage.setItem('aurasaas_lang', value)
})

export function useLanguage() {
  const isZh = computed(() => language.value === 'zh')

  function setLanguage(value) {
    language.value = value === 'en' ? 'en' : 'zh'
  }

  return { language, isZh, setLanguage }
}
