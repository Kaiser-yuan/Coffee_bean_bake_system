import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

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
        meta: { title: '系统总览' },
      },
      {
        path: 'green-beans',
        name: 'green-beans',
        component: () => import('../views/GreenBeanManagement.vue'),
        meta: { title: '生豆管理' },
      },
      {
        path: 'roasting',
        name: 'roasting',
        component: () => import('../views/RoastingBatchList.vue'),
        meta: { title: '烘焙分析' },
      },
      {
        path: 'curve/:batchId',
        name: 'curve-single',
        component: () => import('../views/CurveAnalysis.vue'),
        meta: { title: '曲线分析' },
      },
      {
        path: 'curve/compare/:ids',
        name: 'curve-compare',
        component: () => import('../views/CurveAnalysis.vue'),
        meta: { title: '多锅对比' },
      },
      {
        path: 'review/:batchId',
        name: 'batch-review',
        component: () => import('../views/BatchReview.vue'),
        meta: { title: '批次复盘' },
      },
      {
        path: 'evaluations',
        name: 'evaluations',
        component: () => import('../views/EvaluationManagement.vue'),
        meta: { title: '评价管理' },
      },
      {
        path: 'evaluations/:questionnaireId',
        name: 'evaluation-detail',
        component: () => import('../views/EvaluationDetail.vue'),
        meta: { title: '评价详情' },
      },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('../views/Settings.vue'),
        meta: { title: '系统设置' },
      },
    ],
  },
  {
    path: '/eval/:shareCode',
    name: 'public-questionnaire',
    component: () => import('../views/PublicQuestionnaire.vue'),
    meta: { title: '咖啡评价问卷' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = (to.meta.title as string) || '咖啡烘焙分析系统'
})

export default router
