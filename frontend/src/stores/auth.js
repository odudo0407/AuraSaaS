import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { request } from '../utils/request'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(data) {
    token.value = data.access_token
    user.value = { username: data.username, email: data.email }
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(user.value))
  }

  function clearAuth() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function register(username, email, password) {
    const res = await request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password }),
    })
    setAuth(res.data)
    return res
  }

  async function login(email, password) {
    const res = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setAuth(res.data)
    return res
  }

  async function logout() {
    try {
      await request('/api/auth/logout', { method: 'POST' })
    } catch {
      // ignore — clear locally either way
    }
    clearAuth()
  }

  async function deleteAccount() {
    await request('/api/auth/account', { method: 'DELETE' })
    clearAuth()
  }

  async function fetchMe() {
    try {
      const res = await request('/api/auth/me')
      user.value = res.data
      localStorage.setItem('user', JSON.stringify(res.data))
    } catch {
      clearAuth()
    }
  }

  return { token, user, isLoggedIn, setAuth, clearAuth, register, login, logout, deleteAccount, fetchMe }
})
