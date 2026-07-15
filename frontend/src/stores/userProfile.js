import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { request } from '../utils/request'

export const useUserProfileStore = defineStore('userProfile', () => {
  const avatarUrl = ref(localStorage.getItem('aura_avatarUrl') || '')
  const selectedStoreId = ref(localStorage.getItem('aura_selectedStoreId') || null)
  const selectedModel = ref(localStorage.getItem('aura_model') || 'deepseek-chat')

  // Persist to localStorage on change
  watch(avatarUrl, (val) => localStorage.setItem('aura_avatarUrl', val))
  watch(selectedStoreId, (val) => {
    if (val) localStorage.setItem('aura_selectedStoreId', val)
    else localStorage.removeItem('aura_selectedStoreId')
  })
  watch(selectedModel, (val) => localStorage.setItem('aura_model', val))

  function setAvatar(url) {
    avatarUrl.value = url
  }

  function setStoreId(id) {
    selectedStoreId.value = id
  }

  function setModel(model) {
    selectedModel.value = model
  }

  /**
   * Upload avatar file to backend.
   * @param {File} file - Image file
   */
  async function uploadAvatar(file) {
    const fd = new FormData()
    fd.append('file', file)
    const res = await request('/api/user/upload-avatar', {
      method: 'POST',
      body: fd,
    })
    if (res.code === 0 && res.data?.avatar_url) {
      avatarUrl.value = res.data.avatar_url
    }
    return res
  }

  /**
   * Fetch user profile from backend and sync avatar.
   */
  async function fetchProfile() {
    try {
      const res = await request('/api/user/profile')
      if (res.code === 0 && res.data) {
        avatarUrl.value = res.data.avatar_url || ''
      }
    } catch {
      // Silently ignore — user may not be logged in
    }
  }

  /**
   * Update user profile fields.
   */
  async function updateProfile(fields) {
    const res = await request('/api/user/profile', {
      method: 'PUT',
      body: JSON.stringify(fields),
    })
    return res
  }

  return {
    avatarUrl,
    selectedStoreId,
    selectedModel,
    setAvatar,
    setStoreId,
    setModel,
    uploadAvatar,
    fetchProfile,
    updateProfile,
  }
})
