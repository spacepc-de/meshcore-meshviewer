<template>
  <!-- Fullscreen map under sticky header: top-16 ≈ 64px header height -->
  <!-- Map container -->
  <div ref="mapEl" class="fixed inset-0 top-16 bg-gray-200 dark:bg-gray-800"></div>

  <!-- Floating sidebar -->
  <div class="fixed left-4 top-20 w-80 max-w-[85vw] rounded-md shadow-lg border bg-white/90 backdrop-blur dark:bg-gray-900/80 dark:border-gray-700">
      <div class="px-3 py-2 border-b dark:border-gray-700 flex items-center justify-between gap-2 text-sm">
        <div class="font-medium">Devices</div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-gray-600 dark:text-gray-300" v-if="!loading">{{ devices.length }}</span>
          <button @click="refresh" :disabled="loading" class="px-2 py-1 rounded bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Refresh</button>
        </div>
      </div>
      <div class="p-2">
        <div class="relative mb-2">
          <span class="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
          <input v-model="query" type="text" placeholder="Search (name, key)" class="w-full pl-8 pr-3 py-1.5 rounded border bg-white dark:bg-gray-900 dark:border-gray-700 text-sm" />
        </div>
        <div class="max-h-[60vh] overflow-auto divide-y dark:divide-gray-700">
          <button
            v-for="d in filtered"
            :key="d.public_key"
            @click="focusDevice(d)"
            class="w-full text-left px-2 py-2 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="font-medium truncate">{{ d.name || d.adv_name || shortKey(d.public_key) }}</div>
              <div class="text-xs text-gray-500">{{ d.adv_lat?.toFixed(4) }}, {{ d.adv_lon?.toFixed(4) }}</div>
            </div>
            <div class="text-xs text-gray-500 truncate">Telemetry: {{ tsLabel(d) || '–' }}</div>
          </button>
          <div v-if="!filtered.length && !loading" class="text-sm text-gray-600 dark:text-gray-300 px-2 py-2">No devices with location found.</div>
        </div>
      </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, onBeforeUnmount, ref, computed, watch } from 'vue'

type Device = {
  name?: string
  adv_name?: string
  public_key: string
  adv_lat: number | null
  adv_lon: number | null
  telemetry_fetched_at?: string | null
}

const mapEl = ref<HTMLDivElement | null>(null)
let map: any = null
let markers: Record<string, any> = {}

const loading = ref(false)
const devices = ref<Device[]>([])
const query = ref('')

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  const base = devices.value
  if (!q) return base
  return base.filter(d =>
    (d.name || d.adv_name || '').toLowerCase().includes(q) ||
    d.public_key.toLowerCase().includes(q)
  )
})

function isValidCoord(lat: any, lon: any) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return false
  // Exclude null island / default 0.00,0.00
  const eps = 1e-6
  if (Math.abs(lat) < eps && Math.abs(lon) < eps) return false
  return true
}

function shortKey(k: string) {
  return k.length > 10 ? `${k.slice(0, 6)}…${k.slice(-4)}` : k
}

async function refresh() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/v1/contacts/latest/', { responseType: 'json' })
    const items = (data?.items || []) as any[]
    const withLoc = items
      .map(it => ({
        name: it.name,
        adv_name: it.adv_name,
        public_key: it.public_key,
        adv_lat: typeof it.adv_lat === 'string' ? parseFloat(it.adv_lat) : it.adv_lat,
        adv_lon: typeof it.adv_lon === 'string' ? parseFloat(it.adv_lon) : it.adv_lon,
        telemetry_fetched_at: it.telemetry_fetched_at ?? null,
      }))
      .filter(d => isValidCoord(d.adv_lat, d.adv_lon)) as Device[]
    devices.value = withLoc
    renderMarkers()
    fitToMarkers()
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('Failed to load devices', e)
  } finally {
    loading.value = false
  }
}

async function ensureMapReady(): Promise<void> {
  if (map) return
  while (!mapEl.value) {
    await new Promise(r => setTimeout(r, 50))
  }
  // Wait for Leaflet to be available
  let L = (window as any).L
  while (!L || typeof L.map !== 'function') {
    await new Promise(r => setTimeout(r, 50))
    L = (window as any).L
  }
  map = L.map(mapEl.value!).setView([51.1657, 10.4515], 6)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)
  // Draw any already-loaded devices
  renderMarkers()
  fitToMarkers()
}

function renderMarkers() {
  if (!map) return
  // Remove old markers that no longer exist
  for (const key of Object.keys(markers)) {
    if (!devices.value.find(d => d.public_key === key)) {
      map.removeLayer(markers[key])
      delete markers[key]
    }
  }
  // Add/update markers
  for (const d of devices.value) {
    const pos: [number, number] = [d.adv_lat as number, d.adv_lon as number]
    const label = d.name || d.adv_name || shortKey(d.public_key)
    const coord = `${pos[0].toFixed(5)}, ${pos[1].toFixed(5)}`
    const time = tsLabel(d) || '–'
    const html = `
      <div class="content">
        <div class="title">${label}</div>
        <div class="meta">Koordinaten: ${coord}</div>
        <div class="meta">Telemetrie: ${time}</div>
      </div>
    `
    const popupOpts = { closeButton: true, autoPan: true, className: 'modern-popup' }
    if (markers[d.public_key]) {
      markers[d.public_key].setLatLng(pos).bindPopup(html, popupOpts)
    } else {
      // @ts-ignore
      const m = (window as any).L.marker(pos).addTo(map).bindPopup(html, popupOpts)
      markers[d.public_key] = m
    }
  }
}

function fitToMarkers() {
  if (!map) return
  const pts = devices.value.map(d => [d.adv_lat as number, d.adv_lon as number])
  if (!pts.length) return
  // @ts-ignore
  const bounds = (window as any).L.latLngBounds(pts)
  map.fitBounds(bounds, { padding: [20, 20] })
}

function focusDevice(d: Device) {
  if (!map || !isValidCoord(d.adv_lat, d.adv_lon)) return
  map.setView([d.adv_lat as number, d.adv_lon as number], Math.max(map.getZoom(), 14))
  const m = markers[d.public_key]
  if (m) m.openPopup()
}

onMounted(async () => {
  await ensureMapReady()
  await refresh()
})

onBeforeUnmount(() => {
  // no-op; Leaflet cleans up when element is removed
})

// Re-render markers when list changes
watch(devices, () => renderMarkers())

function tsLabel(d: Device) {
  if (!d.telemetry_fetched_at) return ''
  try {
    const ts = new Date(d.telemetry_fetched_at)
    const now = new Date()
    const diffSec = Math.round((ts.getTime() - now.getTime()) / 1000)
    const absSec = Math.abs(diffSec)

    // Prefer Intl.RelativeTimeFormat for proper German phrasing
    const rtf = (Intl as any)?.RelativeTimeFormat ? new Intl.RelativeTimeFormat('en', { numeric: 'auto' }) : null
    if (rtf) {
      if (absSec < 60) return rtf.format(diffSec, 'second')
      const diffMin = Math.round(diffSec / 60)
      const absMin = Math.abs(diffMin)
      if (absMin < 60) return rtf.format(diffMin, 'minute')
      const diffHour = Math.round(diffMin / 60)
      const absHour = Math.abs(diffHour)
      if (absHour < 24) return rtf.format(diffHour, 'hour')
      const diffDay = Math.round(diffHour / 24)
      const absDay = Math.abs(diffDay)
      if (absDay < 7) return rtf.format(diffDay, 'day')
      const diffWeek = Math.round(diffDay / 7)
      const absWeek = Math.abs(diffWeek)
      if (absWeek < 5) return rtf.format(diffWeek, 'week')
      const diffMonth = Math.round(diffDay / 30)
      const absMonth = Math.abs(diffMonth)
      if (absMonth < 12) return rtf.format(diffMonth, 'month')
      const diffYear = Math.round(diffDay / 365)
      return rtf.format(diffYear, 'year')
    }

    // Fallback: absolute Datum
    return ts.toLocaleString('en-US')
  } catch {
    return String(d.telemetry_fetched_at)
  }
}
</script>

<style scoped>
/* Ensure Leaflet controls look okay on dark background */
:deep(.leaflet-control-container .leaflet-control) {
  filter: saturate(0.9) brightness(0.95);
}

/* Modern popup styling */
:deep(.leaflet-popup.modern-popup .leaflet-popup-content-wrapper) {
  border-radius: 10px;
  border: 1px solid rgb(229 231 235 / 1); /* gray-200 */
  background: white;
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

:deep(.dark .leaflet-popup.modern-popup .leaflet-popup-content-wrapper) {
  background: rgb(17 24 39 / 1); /* gray-900 */
  border-color: rgb(55 65 81 / 1); /* gray-700 */
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.5);
}

:deep(.leaflet-popup.modern-popup .leaflet-popup-tip) {
  background: white;
  border: 1px solid rgb(229 231 235 / 1);
}

:deep(.dark .leaflet-popup.modern-popup .leaflet-popup-tip) {
  background: rgb(17 24 39 / 1);
  border-color: rgb(55 65 81 / 1);
}

/* Popup content typography */
:deep(.leaflet-popup.modern-popup .leaflet-popup-content) {
  margin: 0;
}

:deep(.leaflet-popup.modern-popup .content) {
  padding: 8px 10px;
}

:deep(.leaflet-popup.modern-popup .title) {
  font-weight: 600;
  color: #111827; /* gray-900 */
}

:deep(.dark .leaflet-popup.modern-popup .title) {
  color: #F3F4F6; /* gray-100 */
}

:deep(.leaflet-popup.modern-popup .meta) {
  color: #6B7280; /* gray-500 */
  font-size: 12px;
  margin-top: 4px;
}

:deep(.dark .leaflet-popup.modern-popup .meta) {
  color: #9CA3AF; /* gray-400 */
}

/* Dim map tiles in dark mode for comfort */
:deep(.dark .leaflet-tile) {
  filter: brightness(0.72) contrast(1.05) saturate(0.9);
}
</style>
