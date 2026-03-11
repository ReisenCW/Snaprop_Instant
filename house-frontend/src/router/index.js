import { createRouter, createWebHistory } from 'vue-router'
import IndexView from '../views/IndexView.vue'
import HomeView from '../views/HomeView.vue'
import HistoryView from '../views/HistoryView.vue'
import ReportDetailView from '../views/ReportDetailView.vue'
import StepOne from '../views/home/StepOne.vue'
import StepTwo from '../views/home/StepTwo.vue'
import StepThree from '../views/home/StepThree.vue'
import LoginView from '../views/LoginView.vue'
import { houseStore } from '../store'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'index',
      component: IndexView,
    },
    {
      path: '/home',
      component: HomeView,
      children: [
        {
          path: '',
          redirect: '/home/step1'
        },
        {
          path: 'step1',
          name: 'step1',
          component: StepOne,
        },
        {
          path: 'step2',
          name: 'step2',
          component: StepTwo,
        },
        {
          path: 'step3',
          name: 'step3',
          component: StepThree,
        }
      ]
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView,
    },
    {
      path: '/report/:id',
      name: 'report-detail',
      component: ReportDetailView,
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminView.vue')
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
  ],
})

router.beforeEach((to, from, next) => {
  const publicPages = ['/', '/login']
  const authRequired = !publicPages.includes(to.path)
  const loggedIn = houseStore.isAuthenticated

  if (authRequired && !loggedIn) {
    return next('/login')
  }

  next()
})

export default router
