import { createRouter, createWebHashHistory } from 'vue-router';
import DashboardView from '../views/DashboardView.vue';
import SettingsView from '../views/SettingsView.vue';
import OptInView from '../views/OptInView.vue';
import WelcomeView from '../views/WelcomeView.vue';

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: DashboardView,
  },
  {
    path: '/welcome',
    name: 'welcome',
    component: WelcomeView,
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
  },
  {
    path: '/opt-in',
    name: 'opt-in',
    component: OptInView,
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

// Redirect first-time visitors to the welcome / onboarding page.
// Once the user completes or skips the flow, WelcomeView writes
// 'topas_onboarding_done' to localStorage and this guard stops firing.
router.beforeEach((to) => {
  if (to.name === 'dashboard' && !localStorage.getItem('topas_onboarding_done')) {
    return { name: 'welcome' };
  }
});

export default router;
