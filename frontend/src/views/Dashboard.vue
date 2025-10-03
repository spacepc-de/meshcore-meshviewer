<template>
  <section class="space-y-6">
    <!-- Header + actions -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">Dashboard</h2>
        <p class="text-sm text-gray-600 dark:text-gray-300">Overview of network, contacts, and activity</p>
      </div>
      <div class="flex items-center gap-2 text-sm">
        <button @click="refreshAll" :disabled="busy" class="px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Refresh</button>
        <span class="text-gray-600 dark:text-gray-300">As of: <strong>{{ lastUpdatedLabel }}</strong></span>
      </div>
    </div>

    <div v-if="globalError" class="rounded border border-red-300 bg-red-50 dark:bg-red-900/30 dark:border-red-800 text-red-800 dark:text-red-200 px-4 py-2 text-sm">
      {{ globalError }}
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-2 md:grid-cols-7 gap-3">
      <div class="rounded-xl border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 p-4">
        <div class="text-xs text-gray-500">Contacts</div>
        <div class="mt-1 flex items-baseline gap-2">
          <div class="text-2xl font-semibold">{{ kpis.contacts }}</div>
          <div class="text-xs text-gray-500">total</div>
        </div>
      </div>
      <div class="rounded-xl border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 p-4">
        <div class="text-xs text-gray-500">With location</div>
        <div class="mt-1 flex items-baseline gap-2">
          <div class="text-2xl font-semibold">{{ kpis.withLocation }}</div>
          <div class="text-xs text-gray-500">markers</div>
        </div>
      </div>
      <div class="rounded-xl border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 p-4">
        <div class="text-xs text-gray-500">Messages (24h)</div>
        <div class="mt-1 flex items-baseline gap-2">
          <div class="text-2xl font-semibold">{{ kpis.msg24h }}</div>
          <div class="text-xs text-gray-500">total</div>
        </div>
      </div>
      <div class="rounded-xl border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 p-4">
        <div class="text-xs text-gray-500">Node</div>
        <div class="mt-1 flex items-baseline gap-2">
          <div class="text-2xl font-semibold">{{ nodeName || '–' }}</div>
        </div>
      </div>
      <div class="rounded-xl border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 p-4">
        <div class="text-xs text-gray-500">Avg RSSI</div>
        <div class="mt-1 flex items-baseline gap-2">
          <div class="text-2xl font-semibold">{{ kpis.avgRssiLabel }}</div>
          <div class="text-xs text-gray-500">dBm</div>
        </div>
      </div>
      <div class="rounded-xl border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 p-4">
        <div class="text-xs text-gray-500">Avg SNR</div>
        <div class="mt-1 flex items-baseline gap-2">
          <div class="text-2xl font-semibold">{{ kpis.avgSnrLabel }}</div>
          <div class="text-xs text-gray-500">dB</div>
        </div>
      </div>
      <div class="rounded-xl border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 p-4">
        <div class="text-xs text-gray-500">Avg battery</div>
        <div class="mt-1 flex items-baseline gap-2">
          <div class="text-2xl font-semibold" :class="batteryClass(kpis.avgBatt)">{{ kpis.avgBattLabel }}</div>
          <div class="text-xs text-gray-500">%</div>
        </div>
      </div>
    </div>

    <!-- Map + Contacts split -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <!-- Map card -->
      <div class="lg:col-span-7 rounded-xl overflow-hidden border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 flex flex-col min-h-0">
        <div class="px-4 py-2 border-b dark:border-gray-700 flex items-center justify-between shrink-0">
          <div class="font-medium">Map</div>
          <div class="text-xs text-gray-500">{{ devices.length }} devices</div>
        </div>
        <div class="relative flex-1 min-h-[280px]">
          <div ref="mapEl" class="absolute inset-0 w-full h-full bg-gray-200 dark:bg-gray-900"></div>
          <div v-if="busyDevices" class="absolute inset-0 grid place-items-center text-sm text-gray-600 dark:text-gray-300 bg-white/20 dark:bg-black/10 backdrop-blur-[2px]">Loading positions…</div>
        </div>
        <div class="px-4 py-2 text-xs text-gray-500 shrink-0">Tip: open the full view under “Map”.</div>
      </div>

      <!-- Contacts card -->
      <div class="lg:col-span-5 rounded-xl overflow-hidden border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700 flex flex-col">
        <div class="px-4 py-2 border-b dark:border-gray-700 flex items-center justify-between gap-2">
          <div class="font-medium">Contacts</div>
          <div class="text-xs text-gray-500">{{ contacts.length }} total</div>
        </div>
        <div class="p-3">
          <div class="relative">
            <span class="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
            <input v-model="query" type="text" placeholder="Search (name, key)" class="w-full pl-8 pr-3 py-2 rounded-md border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
          </div>
        </div>
        <div class="max-h-96 overflow-y-auto divide-y dark:divide-gray-700">
          <button
            v-for="c in visibleContacts"
            :key="c.public_key || c.name"
            class="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-900/40"
            @click="goToContact(c)"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="min-w-0">
                <div class="font-medium truncate">{{ c.name || c.adv_name || shortKey(c.public_key) }}</div>
                
                <div class="text-xs text-gray-500 truncate" v-if="c.first_seen">First seen: {{ fmtAbs(c.first_seen) }}</div>
              </div>
              <div class="text-xs text-gray-500 whitespace-nowrap" v-if="isValidCoord(c.adv_lat, c.adv_lon)">
                {{ Number(c.adv_lat).toFixed(3) }}, {{ Number(c.adv_lon).toFixed(3) }}
              </div>
            </div>
          </button>
          <div v-if="!visibleContacts.length && !busyContacts" class="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">No results.</div>
          <div v-if="busyContacts" class="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">Loading…</div>
        </div>
        <div class="px-4 py-2 border-t dark:border-gray-700 text-xs text-gray-600 dark:text-gray-300 flex items-center justify-between">
          <RouterLink to="/messages" class="text-indigo-600 hover:underline">Go to Messages →</RouterLink>
          <RouterLink to="/map" class="text-indigo-600 hover:underline">Open Map →</RouterLink>
        </div>
      </div>
    </div>

    <!-- Node details (compact + expandable) -->
    <div class="rounded-xl border shadow-sm bg-white dark:bg-gray-800 dark:border-gray-700">
      <div class="px-4 py-2 border-b dark:border-gray-700 flex items-center justify-between">
        <div class="font-medium">My Node</div>
        <div class="flex items-center gap-3 text-xs text-gray-500">
          <span>As of: {{ lastUpdatedLabel }}</span>
          <button @click="showNodeDetails = !showNodeDetails" class="px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
            <span v-if="showNodeDetails">Less</span>
            <span v-else>Details</span>
          </button>
        </div>
      </div>
      <div class="p-4 text-sm">
        <template v-if="!showNodeDetails">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <!-- Device / Version -->
            <div>
              <div class="text-gray-500 dark:text-gray-400">Device</div>
              <div class="mt-1 font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <span>{{ deviceModel || 'Unknown' }}</span>
                <span v-if="deviceVersion" class="inline-flex items-center px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-200 border border-indigo-200 dark:border-indigo-800">{{ deviceVersion }}</span>
              </div>
              <div v-if="deviceBuild" class="text-xs text-gray-500 dark:text-gray-400 mt-1">Build: {{ deviceBuild }}</div>
            </div>
            <!-- Self Telemetry Chips -->
            <div>
              <div class="text-gray-500 dark:text-gray-400">Self Telemetry</div>
              <div class="mt-1 flex flex-wrap gap-2">
                <template v-if="selfTelemetryChips.length">
                  <span v-for="(chip, i) in selfTelemetryChips" :key="chip.k + '-' + i" class="inline-flex items-center px-2 py-0.5 rounded border text-xs" :class="chip.cls">
                    <span class="mr-1">{{ chip.icon }}</span>{{ chip.label }}
                  </span>
                </template>
                <span v-else class="text-gray-500 dark:text-gray-400">No readings</span>
              </div>
            </div>
            <!-- Key/Name -->
            <div>
              <div class="text-gray-500 dark:text-gray-400">Key</div>
              <div class="mt-1 font-mono break-all text-gray-900 dark:text-gray-100">
                <span v-if="selfPubkey">{{ selfPubkey }}</span>
                <span v-else class="text-gray-500 dark:text-gray-400">–</span>
              </div>
              <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Name: {{ nodeName || '–' }}</div>
            </div>
          </div>
          <div v-if="!deviceModel && !deviceVersion && !selfTelemetryChips.length && !busyNode" class="text-gray-500 dark:text-gray-400">No data available.</div>
          <div v-if="busyNode" class="text-gray-500 dark:text-gray-400">Loading…</div>
        </template>
        <template v-else>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-for="([key, val], idx) in nodeEntries" :key="key + '-' + idx" class="flex items-start justify-between gap-3">
              <div class="text-gray-600 dark:text-gray-300">{{ key }}</div>
              <div class="font-mono break-all">{{ val }}</div>
            </div>
          </div>
        </template>
      </div>
      <div class="px-4 py-2 text-xs text-gray-500">Backend usually refreshes hourly. Force with <code>?max_age=0</code>.</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter, RouterLink } from 'vue-router'
import { useNodeStore } from '../stores/node'

type Contact = {
  name?: string
  adv_name?: string
  public_key: string
  adv_lat: number | string | null
  adv_lon: number | string | null
  first_seen?: string | null
  telemetry_fetched_at?: string | null
}

// Node store
const nodeStore = useNodeStore()
const { nodeResp, loading: nodeLoading, error: nodeError } = storeToRefs(nodeStore)

// Local state
const busy = computed(() => nodeLoading.value || busyContacts.value || busyDevices.value || busyMsgs.value)
const busyNode = nodeLoading
const globalError = ref<string | null>(null)

const router = useRouter()

const mapEl = ref<HTMLDivElement | null>(null)
let map: any = null
let markers: Record<string, any> = {}

const contacts = ref<Contact[]>([])
const devices = ref<Contact[]>([])
const messages = ref<any[]>([])

const query = ref('')

const busyContacts = ref(false)
const busyDevices = ref(false)
const busyMsgs = ref(false)

const kpis = computed(() => {
  const total = contacts.value.length
  const withLoc = devices.value.length
  const dayAgo = Date.now() - 24 * 3600 * 1000
  const msg24 = messages.value.filter(m => {
    const t = new Date(m.ts).getTime()
    return Number.isFinite(t) && t >= dayAgo
  }).length
  const rssis = contacts.value.map((c:any) => c.rssi).filter((v:any) => typeof v === 'number' && Number.isFinite(v)) as number[]
  const snrs = contacts.value.map((c:any) => c.snr).filter((v:any) => typeof v === 'number' && Number.isFinite(v)) as number[]
  const avg = (arr: number[]) => arr.length ? Math.round((arr.reduce((a,b)=>a+b,0)/arr.length)) : null
  const avgRssi = avg(rssis)
  const avgSnr = arrMean(snrs)
  const batts = contacts.value.map((c:any) => c.battery_percent).filter((v:any) => typeof v === 'number' && Number.isFinite(v)) as number[]
  const avgBatt = batts.length ? (batts.reduce((a,b)=>a+b,0)/batts.length) : null
  return {
    contacts: total,
    withLocation: withLoc,
    msg24h: msg24,
    avgRssi,
    avgSnr,
    avgBatt,
    avgRssiLabel: avgRssi==null? '–' : String(avgRssi),
    avgSnrLabel: avgSnr==null? '–' : avgSnr.toFixed(1),
    avgBattLabel: avgBatt==null? '–' : Math.round(avgBatt).toString(),
  }
})

function arrMean(arr: number[]) { return arr.length ? (arr.reduce((a,b)=>a+b,0)/arr.length) : null }

function batteryClass(pct: number | null) {
  if (pct == null) return ''
  if (pct < 20) return 'text-red-600'
  if (pct < 40) return 'text-amber-600'
  if (pct > 80) return 'text-emerald-600'
  return ''
}

const nodeName = computed(() => nodeResp.value?.name || '')

const lastUpdatedLabel = computed(() => {
  // Prefer contacts timestamp, fallback to node
  const ts = nodeResp.value?.fetched_at || null
  try { return ts ? new Date(ts).toLocaleString() : '–' } catch { return String(ts) }
})

const flatData = computed(() => nodeResp.value?.data || {})
const nodeEntries = computed<[string, any][]>(() => Object.entries(flatData.value || {}))
const nodeEntriesShort = computed<[string, any][]>(() => nodeEntries.value.slice(0, 6))
const showNodeDetails = ref(false)

function shortKey(k: string) {
  return k && k.length > 10 ? `${k.slice(0, 6)}…${k.slice(-4)}` : k
}

function isValidCoord(lat: any, lon: any) {
  const nlat = typeof lat === 'string' ? parseFloat(lat) : lat
  const nlon = typeof lon === 'string' ? parseFloat(lon) : lon
  if (!Number.isFinite(nlat) || !Number.isFinite(nlon)) return false
  if (Math.abs(nlat) > 90 || Math.abs(nlon) > 180) return false
  const eps = 1e-6
  if (Math.abs(nlat) < eps && Math.abs(nlon) < eps) return false
  return true
}

// Device info and Self Telemetry (from backend-enriched MyNode)
const deviceInfo = computed(() => flatData.value?.device_info || null)
const deviceModel = computed(() => deviceInfo.value?.model || '')
const deviceVersion = computed(() => deviceInfo.value?.ver || deviceInfo.value?.['fw ver'] || '')
const deviceBuild = computed(() => deviceInfo.value?.fw_build || '')

const selfTelemetry = computed(() => flatData.value?.self_telemetry || null)
const selfPubkey = computed(() => selfTelemetry.value?.pubkey_pre || selfTelemetry.value?.public_key || '')

type Chip = { k: string; label: string; cls: string; icon: string }
function fmtNum(val: any, digits = 2) {
  const n = typeof val === 'string' ? Number(val) : val
  if (!Number.isFinite(n)) return String(val)
  return n.toFixed(digits)
}
function chipForLppEntry(e: any): Chip | null {
  if (!e || typeof e !== 'object') return null
  const t = (e.type || '').toString().toLowerCase()
  const v = e.value
  switch (t) {
    case 'voltage': return { k: 'voltage', label: `${fmtNum(v)} V`, cls: 'border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-200 bg-amber-50 dark:bg-amber-900/20', icon: '🔋' }
    case 'temperature': return { k: 'temp', label: `${fmtNum(v)} °C`, cls: 'border-red-200 dark:border-red-800 text-red-700 dark:text-red-200 bg-red-50 dark:bg-red-900/20', icon: '🌡️' }
    case 'humidity': return { k: 'hum', label: `${fmtNum(v)} %`, cls: 'border-cyan-200 dark:border-cyan-800 text-cyan-700 dark:text-cyan-200 bg-cyan-50 dark:bg-cyan-900/20', icon: '💧' }
    case 'pressure': return { k: 'press', label: `${fmtNum(v, 0)} hPa`, cls: 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-slate-800/30', icon: '⛰️' }
    case 'battery': return { k: 'battery', label: `${fmtNum(v, 0)} %`, cls: 'border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-200 bg-emerald-50 dark:bg-emerald-900/20', icon: '🔌' }
    default: {
      const label = `${t || 'value'}: ${fmtNum(v)}`
      return { k: t || 'val', label, cls: 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-gray-800/30', icon: '📈' }
    }
  }
}
const selfTelemetryChips = computed<Chip[]>(() => {
  const lpp = (selfTelemetry.value?.lpp || []) as any[]
  const chips = lpp.map(chipForLppEntry).filter(Boolean) as Chip[]
  return chips.slice(0, 6)
})

// telemetry relative time removed from UI

function fmtAbs(ts: string) {
  try {
    const d = new Date(ts)
    return d.toLocaleString()
  } catch { return String(ts) }
}

const filteredContacts = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return contacts.value
  return contacts.value.filter(c =>
    (c.name || c.adv_name || '').toLowerCase().includes(q) ||
    (c.public_key || '').toLowerCase().includes(q)
  )
})
const visibleContacts = computed(() => filteredContacts.value)

async function refreshContacts() {
  busyContacts.value = true
  globalError.value = null
  try {
    const { data } = await axios.get('/api/v1/contacts/latest/', { responseType: 'json' })
    const items = (data?.items || []) as any[]
    const mapped = items.map(it => ({
      name: it.name,
      adv_name: it.adv_name,
      public_key: it.public_key,
      adv_lat: it.adv_lat,
      adv_lon: it.adv_lon,
      first_seen: it.first_seen ?? null,
      telemetry_fetched_at: it.telemetry_fetched_at ?? null,
      rssi: it.rssi ?? null,
      snr: it.snr ?? null,
      battery_percent: it.battery_percent ?? null,
      battery_mv: it.battery_mv ?? null,
    })) as Contact[]
    contacts.value = mapped
  } catch (e: any) {
    globalError.value = e?.message || 'Failed to load contacts.'
  } finally {
    busyContacts.value = false
  }
}

async function refreshMessages() {
  busyMsgs.value = true
  try {
    const { data } = await axios.get('/api/v1/messages/', { params: { limit: 100 } })
    messages.value = data?.items || []
  } catch {/* ignore */}
  finally { busyMsgs.value = false }
}

async function ensureMap() {
  if (map) return
  while (!mapEl.value) { await new Promise(r => setTimeout(r, 50)) }
  // Wait for Leaflet global
  let L = (window as any).L
  while (!L || typeof L.map !== 'function') { await new Promise(r => setTimeout(r, 50)); L = (window as any).L }
  map = L.map(mapEl.value!).setView([51.1657, 10.4515], 6)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)
  // Ensure correct sizing after first paint
  setTimeout(() => { try { map.invalidateSize() } catch {} }, 0)
}

function renderMarkers() {
  if (!map) return
  const L = (window as any).L
  // remove stale
  for (const key of Object.keys(markers)) {
    if (!devices.value.find(d => d.public_key === key)) {
      map.removeLayer(markers[key]); delete markers[key]
    }
  }
  for (const d of devices.value) {
    const lat = typeof d.adv_lat === 'string' ? parseFloat(d.adv_lat) : d.adv_lat
    const lon = typeof d.adv_lon === 'string' ? parseFloat(d.adv_lon) : d.adv_lon
    if (!isValidCoord(lat, lon)) continue
    const pos: [number, number] = [lat as number, lon as number]
    const label = d.name || d.adv_name || shortKey(d.public_key)
    if (markers[d.public_key]) {
      markers[d.public_key].setLatLng(pos).bindPopup(`<strong>${label}</strong><br/>${pos[0].toFixed(5)}, ${pos[1].toFixed(5)}`)
    } else {
      markers[d.public_key] = L.marker(pos).addTo(map).bindPopup(`<strong>${label}</strong><br/>${pos[0].toFixed(5)}, ${pos[1].toFixed(5)}`)
    }
  }
  // Fit once on initial render
  fitToMarkers()
}

function fitToMarkers() {
  if (!map) return
  const pts = devices.value
    .map(d => [typeof d.adv_lat === 'string' ? parseFloat(d.adv_lat) : d.adv_lat, typeof d.adv_lon === 'string' ? parseFloat(d.adv_lon) : d.adv_lon])
    .filter(([a, b]) => isValidCoord(a, b)) as [number, number][]
  if (!pts.length) return
  const L = (window as any).L
  const bounds = L.latLngBounds(pts)
  map.fitBounds(bounds, { padding: [16, 16], maxZoom: 10 })
}

async function refreshDevicesOnMap() {
  busyDevices.value = true
  try {
    // Derive from contacts to keep calls minimal
    devices.value = contacts.value.filter(c => isValidCoord(c.adv_lat, c.adv_lon))
    await ensureMap()
    renderMarkers()
  } finally {
    busyDevices.value = false
  }
}

function goToContact(c: Contact) {
  // Prefer messages view for contact interactions
  router.push({ name: 'messages' })
}

async function refreshAll() {
  await Promise.all([
    nodeStore.fetchNode(true).catch(() => {}),
    refreshContacts(),
    refreshMessages(),
  ])
  await refreshDevicesOnMap()
}

watch(contacts, () => refreshDevicesOnMap())

onMounted(async () => {
  // initial data
  try { await nodeStore.fetchNode(false) } catch {}
  await refreshContacts()
  await refreshMessages()
  await ensureMap(); await refreshDevicesOnMap()
})
</script>

<style scoped>
</style>
