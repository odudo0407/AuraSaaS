import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '../utils/request'

export const useDashboardStore = defineStore('dashboard', () => {
  const overview = ref(null)
  const trends = ref(null)
  const topSkus = ref([])
  const stores = ref([])
  const currentStoreId = ref(null) // null = all stores
  const loading = ref(false)

  async function fetchStores() {
    const res = await request('/api/dashboard/stores')
    stores.value = res.data
  }

  async function fetchOverview() {
    const qs = currentStoreId.value ? `?store_id=${currentStoreId.value}` : ''
    const res = await request(`/api/dashboard/overview${qs}`)
    overview.value = res.data
  }

  async function fetchTrends(days = 30) {
    const params = [`days=${days}`]
    if (currentStoreId.value) params.push(`store_id=${currentStoreId.value}`)
    const res = await request(`/api/dashboard/trends?${params.join('&')}`)
    trends.value = res.data
  }

  async function fetchTopSkus(limit = 5, days = 7) {
    const params = [`limit=${limit}`, `days=${days}`]
    if (currentStoreId.value) params.push(`store_id=${currentStoreId.value}`)
    const res = await request(`/api/dashboard/top-skus?${params.join('&')}`)
    topSkus.value = res.data
  }

  function setStore(storeId) {
    currentStoreId.value = storeId
    fetchAll()
  }

  async function fetchAll() {
    loading.value = true
    try {
      await Promise.all([fetchOverview(), fetchTrends(), fetchTopSkus()])
    } finally {
      loading.value = false
    }
  }

  return { overview, trends, topSkus, stores, currentStoreId, loading, fetchAll, fetchStores, setStore, fetchOverview, fetchTrends, fetchTopSkus }
})
