import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Messages from './views/Messages.vue'
import Automation from './views/Automation.vue'
import Settings from './views/Settings.vue'
import MapView from './views/Map.vue'
import Devices from './views/Devices.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: Dashboard },
  { path: '/messages', name: 'messages', component: Messages },
  { path: '/devices', name: 'devices', component: Devices },
  { path: '/automation', name: 'automation', component: Automation },
  { path: '/settings', name: 'settings', component: Settings },
  { path: '/map', name: 'map', component: MapView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
