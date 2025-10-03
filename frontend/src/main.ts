import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './styles.css'
import { useNodeStore } from './stores/node'
import { useConnectionStore } from './stores/connection'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia).use(router)

// Initialize node refresh on app start
const nodeStore = useNodeStore(pinia)
nodeStore.startAutoRefresh()

// Initialize connection status polling + auto-reconnect
const connStore = useConnectionStore(pinia)
connStore.startAuto()

app.mount('#app')
