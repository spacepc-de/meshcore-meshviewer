import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export type NodeApiResponse = {
  name: string
  fetched_at: string
  data: Record<string, any>
}

export const useNodeStore = defineStore('node', () => {
  const loading = ref(false)
  const nodeResp = ref<NodeApiResponse | null>(null)
  const intervalId = ref<number | null>(null)
  const error = ref<string | null>(null)

  async function fetchNode(force = false) {
    loading.value = true
    error.value = null
    try {
      const url = force ? '/api/v1/my-node/?max_age=0' : '/api/v1/my-node/'
      const { data } = await axios.get(url)
      nodeResp.value = data
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Unknown error'
      error.value = `Fetch failed: ${msg}`
      throw e
    } finally {
      loading.value = false
    }
  }

  function startAutoRefresh() {
    // Allow configuration via Vite env var, fallback to 60s
    const msStr = import.meta.env.VITE_NODE_REFRESH_MS as string | undefined
    const refreshMs = msStr ? Number(msStr) : 60_000
    if (!Number.isFinite(refreshMs) || refreshMs <= 0) {
      // default safety net
      // eslint-disable-next-line no-console
      console.warn('Invalid VITE_NODE_REFRESH_MS, using default 60000ms')
    }

    // Clear any previous timer
    if (intervalId.value) {
      window.clearInterval(intervalId.value)
      intervalId.value = null
    }

    // Initial fetch (non-forced)
    fetchNode(false)

    // Periodic refresh (non-forced to respect backend cache policy)
    intervalId.value = window.setInterval(() => {
      fetchNode(false)
    }, Number.isFinite(refreshMs) && refreshMs > 0 ? refreshMs : 60_000)
  }

  function stopAutoRefresh() {
    if (intervalId.value) {
      window.clearInterval(intervalId.value)
      intervalId.value = null
    }
  }

  return {
    // state
    loading,
    nodeResp,
    error,
    // actions
    fetchNode,
    startAutoRefresh,
    stopAutoRefresh,
  }
})
