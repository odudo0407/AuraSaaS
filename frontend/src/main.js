import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import 'virtual:uno.css'
import App from './App.vue'
import MainLayout from './layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('./views/Landing.vue'),
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('./views/Login.vue'),
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('./views/Register.vue'),
  },
  {
    path: '/app',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/app/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('./views/Dashboard.vue'), meta: { requiresAuth: true } },
      { path: 'ai', name: 'AIAnalysis', component: () => import('./views/AIAnalysis.vue'), meta: { requiresAuth: true } },
      { path: 'reports', name: 'Reports', component: () => import('./views/Reports.vue'), meta: { requiresAuth: true } },
      { path: 'products', name: 'Products', component: () => import('./views/Products.vue'), meta: { requiresAuth: true } },
      { path: 'staff', name: 'Staff', component: () => import('./views/Staff.vue'), meta: { requiresAuth: true } },
      { path: 'stores', name: 'Stores', component: () => import('./views/Stores.vue'), meta: { requiresAuth: true } },
      { path: 'marketing', name: 'Marketing', component: () => import('./views/Marketing.vue'), meta: { requiresAuth: true } },
      { path: 'finance', name: 'Finance', component: () => import('./views/Finance.vue'), meta: { requiresAuth: true } },
      { path: 'settings', name: 'Settings', component: () => import('./views/Settings.vue'), meta: { requiresAuth: true } },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

// Navigation guard — protect auth-required routes
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

// Global listener: clear auth state and redirect to login when token expires
window.addEventListener('aurasaas:auth-expired', () => {
  router.push({ path: '/login', query: { redirect: router.currentRoute.value?.fullPath || '/app/dashboard' } })
})
