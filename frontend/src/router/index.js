import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '案件总览' },
      },
      {
        path: '/case/create',
        name: 'CaseCreate',
        component: () => import('@/views/CaseCreateView.vue'),
        meta: { title: '新建案件' },
      },
      {
        path: '/case/:id',
        name: 'CaseDetail',
        component: () => import('@/views/CaseDetailView.vue'),
        meta: { title: '案件详情' },
      },
      {
        path: '/case/:id/edit',
        name: 'CaseEdit',
        component: () => import('@/views/CaseEditView.vue'),
        meta: { title: '编辑案件' },
      },
      {
        path: '/reminders',
        name: 'Reminders',
        component: () => import('@/views/RemindersView.vue'),
        meta: { title: '提醒中心' },
      },
      {
        path: '/tasks',
        name: 'Tasks',
        component: () => import('@/views/TasksView.vue'),
        meta: { title: '任务中心' },
      },
      {
        path: '/search',
        name: 'KnowledgeSearch',
        component: () => import('@/views/KnowledgeSearchView.vue'),
        meta: { title: '知识搜索' },
      },
      {
        path: '/ai',
        name: 'AICapabilities',
        component: () => import('@/views/AICapabilitiesView.vue'),
        meta: { title: 'AI 能力' },
      },
      {
        path: '/lawyers',
        name: 'LawyerWorkload',
        component: () => import('@/views/LawyerWorkloadView.vue'),
        meta: { title: '律师工作负载' },
      },
      {
        path: '/settings',
        name: 'Settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: '设置' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function hasAuthToken() {
  return Boolean(localStorage.getItem('auth_token'))
}

router.beforeEach((to, from, next) => {
  if (!hasAuthToken()) {
    const redirect = encodeURIComponent(to.fullPath || '/')
    window.location.replace(`/login.html?redirect=${redirect}`)
    return
  }
  next()
})

export default router
