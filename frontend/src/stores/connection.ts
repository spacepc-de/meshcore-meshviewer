import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useConnectionStore = defineStore('connection', () => {
  const connected = ref<boolean | null>(null)
  const checking = ref(false)
  const reconnecting = ref(false)
  const lastError = ref<string | null>(null)
  const statusTimer = ref<number | null>(null)
  const retryTimer = ref<number | null>(null)

  async function checkStatus() {
    checking.value = true
    try {
      const { data } = await axios.get('/api/v1/connection/status/')
      connected.value = !!data?.connected
      lastError.value = null
    } catch (e: any) {
      connected.value = false
      lastError.value = e?.response?.data?.detail || e?.message || 'Status check failed'
    } finally {
      checking.value = false
    }
  }

  async function attemptReconnect() {
    if (reconnecting.value) return
    reconnecting.value = true
    try {
      const { data } = await axios.post('/api/v1/connection/reconnect/', {})
      connected.value = !!data?.connected
      if (!connected.value) {
        lastError.value = data?.detail || null
      } else {
        lastError.value = null
      }
    } catch (e: any) {
      connected.value = false
      lastError.value = e?.response?.data?.detail || e?.message || 'Reconnect failed'
    } finally {
      reconnecting.value = false
    }
  }

  function startAuto() {
    // Read polling intervals from Vite env, with sensible defaults
    const pollStr = import.meta.env.VITE_CONN_POLL_MS as string | undefined
    const retryStr = import.meta.env.VITE_CONN_RETRY_MS as string | undefined
    const pollMs = pollStr ? Number(pollStr) : 15_000
    const retryMs = retryStr ? Number(retryStr) : 8_000

    // Clear existing timers
    if (statusTimer.value) {
      window.clearInterval(statusTimer.value)
      statusTimer.value = null
    }
    if (retryTimer.value) {
      window.clearInterval(retryTimer.value)
      retryTimer.value = null
    }

    // Initial status check
    checkStatus()

    // Periodic status polling
    statusTimer.value = window.setInterval(() => {
      checkStatus()
    }, Number.isFinite(pollMs) && pollMs > 0 ? pollMs : 15_000)

    // Periodic reconnect attempts when disconnected
    retryTimer.value = window.setInterval(() => {
      if (connected.value === false && !reconnecting.value) {
        attemptReconnect()
      }
    }, Number.isFinite(retryMs) && retryMs > 0 ? retryMs : 8_000)
  }

  function stopAuto() {
    if (statusTimer.value) {
      window.clearInterval(statusTimer.value)
      statusTimer.value = null
    }
    if (retryTimer.value) {
      window.clearInterval(retryTimer.value)
      retryTimer.value = null
    }
  }

  return {
    // state
    connected,
    checking,
    reconnecting,
    lastError,
    // actions
    checkStatus,
    attemptReconnect,
    startAuto,
    stopAuto,
  }
})

