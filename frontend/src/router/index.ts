import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import LandingPage from '@/views/LandingPage.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'LandingPage',
    component: LandingPage
  },
  {
    path: '/analytics/users',
    name: 'UserAnalytics',
    component: () => import('@/views/UserAnalytics.vue')
  },
  {
    path: '/reports/sales',
    name: 'SalesReports',
    component: () => import('@/views/SalesReports.vue')
  },
  {
    path: '/logs/system',
    name: 'SystemLogs',
    component: () => import('@/views/SystemLogs.vue')
  },
  {
    path: '/metrics/performance',
    name: 'PerformanceMetrics',
    component: () => import('@/views/PerformanceMetrics.vue')
  },
  {
    path: '/explorer',
    name: 'DataExplorer',
    component: () => import('@/views/DataExplorer.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
