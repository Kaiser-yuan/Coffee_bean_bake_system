import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { isDemoMode } from '../api/http'
import { useAuthStore } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('../components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '系统总览', requiresAuth: true },
      },
      {
        path: 'green-beans',
        name: 'green-beans',
        component: () => import('../views/GreenBeanManagement.vue'),
        meta: { title: '生豆管理', requiresAuth: true },
      },
      {
        path: 'roasting',
        name: 'roasting',
        component: () => import('../views/RoastingBatchList.vue'),
        meta: { title: '烘焙分析', requiresAuth: true },
      },
      {
        path: 'curve/:batchId',
        name: 'curve-single',
        component: () => import('../views/CurveAnalysis.vue'),
        meta: { title: '曲线分析', requiresAuth: true },
      },
      {
        path: 'curve/compare/:ids',
        name: 'curve-compare',
        component: () => import('../views/CurveAnalysis.vue'),
        meta: { title: '多锅对比', requiresAuth: true },
      },
      {
        path: 'review/:batchId',
        name: 'batch-review',
        component: () => import('../views/BatchReview.vue'),
        meta: { title: '批次复盘', requiresAuth: true },
      },
      {
        path: 'evaluations',
        name: 'evaluations',
        component: () => import('../views/EvaluationManagement.vue'),
        meta: { title: '评价管理', requiresAuth: true },
      },
      {
        path: 'evaluations/:questionnaireId',
        name: 'evaluation-detail',
        component: () => import('../views/EvaluationDetail.vue'),
        meta: { title: '评价详情', requiresAuth: true },
      },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('../views/Settings.vue'),
        meta: { title: '系统设置', requiresAuth: true },
      },
    ],
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/eval/:shareCode',
    name: 'public-questionnaire',
    component: () => import('../views/PublicQuestionnaire.vue'),
    meta: { title: '咖啡评价问卷' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.name === 'login' && auth.isAuthenticated) {
    return '/dashboard'
  }

  if (!isDemoMode && to.meta.requiresAuth && !auth.isAuthenticated) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }
})

router.afterEach((to) => {
  document.title = (to.meta.title as string) || '咖啡烘焙分析系统'
})

export default router
