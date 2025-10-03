<template>
  <section class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold tracking-tight">Devices</h2>
        <p class="text-sm text-gray-600 dark:text-gray-300">All discovered devices with search and details</p>
      </div>
      <div class="flex items-center gap-2 text-sm">
        <button @click="refresh" :disabled="loading" class="px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Refresh</button>
        <span class="text-gray-600 dark:text-gray-300">As of: <strong>{{ lastUpdatedLabel }}</strong></span>
      </div>
    </div>

    <div v-if="error" class="rounded border border-red-300 bg-red-50 dark:bg-red-900/30 dark:border-red-800 text-red-800 dark:text-red-200 px-4 py-2 text-sm">
      {{ error }}
    </div>

    <!-- Card -->
    <div class="rounded-xl border bg-white dark:bg-gray-800 dark:border-gray-700 overflow-hidden flex flex-col min-h-0">
      <div class="px-3 sm:px-4 py-2 border-b dark:border-gray-700 flex items-center justify-between gap-3">
        <div class="hidden sm:flex items-center gap-2 text-xs">
          <button
            v-for="opt in typeOptions"
            :key="opt.value"
            @click="typeFilter = opt.value"
            :class="['px-2 py-1 rounded border', typeFilter===opt.value ? 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900/30 dark:border-indigo-700' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300']"
          >{{ opt.label }}</button>
          <label class="ml-2 inline-flex items-center gap-1 px-2 py-1 rounded border border-gray-200 dark:border-gray-700">
            <input type="checkbox" v-model="onlyWithPos" class="rounded" />
            Pos
          </label>
        </div>
        <div class="text-sm text-gray-600 dark:text-gray-300">{{ filtered.length }} devices</div>
        <div class="relative w-full max-w-sm ml-auto">
          <span class="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
          <input v-model="query" type="text" placeholder="Search (name, key, …)" class="w-full pl-8 pr-3 py-2 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
        </div>
      </div>
      <div class="flex-1 min-h-0 overflow-auto divide-y dark:divide-gray-700 scroll-fade">
        <button
          v-for="d in sorted"
          :key="d.public_key"
          class="w-full text-left px-3 sm:px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-900/40 transition-colors"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-start gap-3 min-w-0">
              <div class="h-9 w-9 shrink-0 rounded-full flex items-center justify-center text-[11px] font-semibold text-white" :style="{ backgroundColor: avatarColor(d) }">
                {{ avatarInitials(d) }}
              </div>
              <div class="min-w-0">
                <div class="font-medium truncate">{{ displayName(d) }}</div>
                <div class="mt-0.5 flex flex-wrap items-center gap-1 text-[11px] text-gray-600 dark:text-gray-300">
                  <span class="inline-flex items-center px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700" :class="typeBadgeClass(d.type)">{{ typeLabel(d.type) }}</span>
                  <span v-if="d.out_path_len != null && d.out_path_len >= 0" class="inline-flex items-center px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700" :title="d.out_path || ''">{{ d.out_path_len }} Hop{{ d.out_path_len === 1 ? '' : 's' }}</span>
                  <span v-if="rssiMap.get(d.public_key) != null" class="inline-flex items-center px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700">RSSI {{ rssiMap.get(d.public_key) }} dBm</span>
                  <span v-if="snrMap.get(d.public_key) != null" class="inline-flex items-center px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700">SNR {{ snrMap.get(d.public_key) }} dB</span>
                  <span v-if="batteryLabel(d)" class="inline-flex items-center px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700">🔋 {{ batteryLabel(d) }}</span>
                </div>
                <div class="text-[11px] text-gray-500 truncate">Key: <span class="font-mono">{{ shortKey(d.public_key) }}</span></div>
                <div class="text-[11px] text-gray-500 truncate" v-if="isValidCoord(d.adv_lat, d.adv_lon)">Pos: {{ coordLabel(d) }}</div>
                <div class="mt-0.5 text-[11px] text-gray-500 truncate" v-if="d.flags != null">Flags: 0x{{ toHex(d.flags) }}</div>
                <div class="mt-0.5 text-[11px] text-gray-500 truncate" v-if="d.first_seen">First seen: {{ fmtAbs(d.first_seen) }}</div>
              </div>
            </div>
            <div class="text-[11px] text-gray-500 text-right whitespace-nowrap">
              <div v-if="d.last_advert">{{ relEpoch(d.last_advert) }}</div>
              <div v-else-if="d.telemetry_fetched_at">{{ relTime(d.telemetry_fetched_at) }}</div>
              <div v-else>—</div>
            </div>
          </div>
        </button>
        <div v-if="!sorted.length && !loading" class="px-3 sm:px-4 py-4 text-sm text-gray-600 dark:text-gray-300">No devices found.</div>
        <div v-if="loading" class="px-3 sm:px-4 py-4 text-sm text-gray-600 dark:text-gray-300">Loading…</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'

type Device = {
  name?: string
  adv_name?: string
  public_key: string
  adv_lat: number | string | null
  adv_lon: number | string | null
  first_seen?: string | null
  telemetry_fetched_at?: string | null
  last_advert?: number | string | null
  type?: number | null
  flags?: number | null
  out_path_len?: number | null
  out_path?: string | null
  battery_mv?: number | null
  battery_percent?: number | null
}

const loading = ref(false)
const error = ref<string | null>(null)
const devices = ref<Device[]>([])
const fetchedAt = ref<string | null>(null)
const query = ref('')
const typeFilter = ref<number | 'all'>('all')
const onlyWithPos = ref(false)
// Enrichment maps from /api/v1/contacts/ (raw cli)
const rssiMap = ref(new Map<string, number>())
const snrMap = ref(new Map<string, number>())

const lastUpdatedLabel = computed(() => {
  const ts = fetchedAt.value
  try { return ts ? new Date(ts).toLocaleString('en-US') : '–' } catch { return String(ts) }
})

function displayName(d: Device) {
  return d.name || d.adv_name || shortKey(d.public_key)
}

function shortKey(k: string) { return k?.length > 16 ? `${k.slice(0,8)}…${k.slice(-6)}` : k }

function isValidCoord(lat: any, lon: any) {
  const la = typeof lat === 'string' ? parseFloat(lat) : lat
  const lo = typeof lon === 'string' ? parseFloat(lon) : lon
  if (!Number.isFinite(la) || !Number.isFinite(lo)) return false
  if (Math.abs(la) > 90 || Math.abs(lo) > 180) return false
  const eps = 1e-6
  if (Math.abs(la) < eps && Math.abs(lo) < eps) return false
  return true
}

function coordLabel(d: Device) {
  const la = typeof d.adv_lat === 'string' ? parseFloat(d.adv_lat) : d.adv_lat
  const lo = typeof d.adv_lon === 'string' ? parseFloat(d.adv_lon) : d.adv_lon
  if (!isValidCoord(la, lo)) return ''
  return `${(la as number).toFixed(4)}, ${(lo as number).toFixed(4)}`
}

function relTime(ts: string) {
  try {
    const d = new Date(ts)
    const now = new Date()
    const diffSec = Math.round((d.getTime() - now.getTime()) / 1000)
    const rtf = (Intl as any)?.RelativeTimeFormat ? new Intl.RelativeTimeFormat('en', { numeric: 'auto' }) : null
    if (!rtf) return d.toLocaleString('en-US')
    if (Math.abs(diffSec) < 60) return rtf.format(diffSec, 'second')
    const m = Math.round(diffSec / 60)
    if (Math.abs(m) < 60) return rtf.format(m, 'minute')
    const h = Math.round(m / 60)
    if (Math.abs(h) < 24) return rtf.format(h, 'hour')
    const days = Math.round(h / 24)
    return rtf.format(days, 'day')
  } catch { return String(ts) }
}

function relEpoch(sec: any) {
  const n = Number(sec)
  if (!Number.isFinite(n)) return String(sec)
  const d = new Date(n * 1000)
  try {
    const now = new Date()
    const diffSec = Math.round((d.getTime() - now.getTime()) / 1000)
    const rtf = (Intl as any)?.RelativeTimeFormat ? new Intl.RelativeTimeFormat('en', { numeric: 'auto' }) : null
    if (!rtf) return d.toLocaleString('en-US')
    if (Math.abs(diffSec) < 60) return rtf.format(diffSec, 'second')
    const m = Math.round(diffSec / 60)
    if (Math.abs(m) < 60) return rtf.format(m, 'minute')
    const h = Math.round(m / 60)
    if (Math.abs(h) < 24) return rtf.format(h, 'hour')
    const days = Math.round(h / 24)
    return rtf.format(days, 'day')
  } catch {
    return d.toLocaleString('en-US')
  }
}

function fmtAbs(ts: string) {
  try {
    const d = new Date(ts)
    return d.toLocaleString()
  } catch { return String(ts) }
}

function typeLabel(t?: number | null) {
  switch (t) {
    case 2: return 'Repeater'
    case 3: return 'Room'
    case 4: return 'Sensor'
    case 0: return 'Channel'
    case 1: return 'Node'
    default: return 'Device'
  }
}

function typeBadgeClass(t?: number | null) {
  switch (t) {
    case 2: return 'bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-200'
    case 3: return 'bg-cyan-50 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-200'
    case 4: return 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200'
    case 1: return 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-200'
    default: return 'bg-gray-100 text-gray-700 dark:bg-gray-800/50 dark:text-gray-200'
  }
}

function batteryLabel(d: Device): string {
  const p = (d as any).battery_percent as number | undefined
  const mv = (d as any).battery_mv as number | undefined
  if (typeof p === 'number' && Number.isFinite(p)) {
    const v = Math.max(0, Math.min(100, p))
    return `${v.toFixed(0)}%`
  }
  if (typeof mv === 'number' && Number.isFinite(mv)) {
    return `${mv} mV`
  }
  return ''
}

function avatarInitials(d: Device) {
  const n = displayName(d)
  const words = String(n).split(/\s+/).filter(Boolean)
  const first = words[0]?.[0] || 'D'
  const second = words[1]?.[0] || ''
  return (first + second).toUpperCase()
}

function avatarColor(d: Device) {
  const base = d.public_key || displayName(d) || 'x'
  let h = 0
  for (let i = 0; i < String(base).length; i++) h = (h * 31 + String(base).charCodeAt(i)) % 360
  return `hsl(${h} 70% 45%)`
}

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  let arr = devices.value
  if (typeFilter.value !== 'all') {
    arr = arr.filter(d => (d.type ?? null) === typeFilter.value)
  }
  if (onlyWithPos.value) {
    arr = arr.filter(d => isValidCoord(d.adv_lat, d.adv_lon))
  }
  if (q) {
    arr = arr.filter(d =>
      (d.name || d.adv_name || '').toLowerCase().includes(q) ||
      (d.public_key || '').toLowerCase().includes(q)
    )
  }
  return arr
})

const sorted = computed(() => {
  const arr = [...filtered.value]
  arr.sort((a, b) => {
    const ta = a.last_advert ? Number(a.last_advert) * 1000 : (a.telemetry_fetched_at ? new Date(a.telemetry_fetched_at).getTime() : 0)
    const tb = b.last_advert ? Number(b.last_advert) * 1000 : (b.telemetry_fetched_at ? new Date(b.telemetry_fetched_at).getTime() : 0)
    if (tb !== ta) return tb - ta
    const na = (displayName(a) || '').toLowerCase()
    const nb = (displayName(b) || '').toLowerCase()
    return na.localeCompare(nb)
  })
  return arr
})

async function refresh() {
  loading.value = true
  error.value = null
  try {
    const [latest, raw] = await Promise.all([
      axios.get('/api/v1/contacts/latest/', { responseType: 'json' }),
      axios.get('/api/v1/contacts/', { responseType: 'json' }).catch(() => ({ data: { items: [] } })),
    ])
    const items = (latest.data?.items || []) as any[]
    devices.value = items.map(it => ({
      name: it.name,
      adv_name: it.adv_name,
      public_key: it.public_key,
      adv_lat: it.adv_lat,
      adv_lon: it.adv_lon,
      first_seen: it.first_seen ?? null,
      telemetry_fetched_at: it.telemetry_fetched_at ?? null,
      last_advert: it.last_advert ?? null,
      type: it.type ?? null,
      flags: it.flags ?? null,
      out_path_len: it.out_path_len ?? null,
      out_path: it.out_path ?? null,
      battery_mv: it.battery_mv ?? null,
      battery_percent: it.battery_percent ?? null,
    }))
    fetchedAt.value = latest.data?.fetched_at || new Date().toISOString()
    // Build enrichment maps from raw contacts (may contain RSSI/SNR in text mode)
    const enrichItems: any[] = (raw.data?.items || []) as any[]
    const rssi = new Map<string, number>()
    const snr = new Map<string, number>()
    for (const it of enrichItems) {
      const pk = it?.public_key
      if (!pk) continue
      if (typeof it.rssi === 'number') rssi.set(pk, it.rssi)
      if (typeof it.snr === 'number') snr.set(pk, it.snr)
    }
    rssiMap.value = rssi
    snrMap.value = snr
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Fetch failed'
  } finally {
    loading.value = false
  }
}

onMounted(refresh)

const typeOptions = [
  { label: 'All', value: 'all' as const },
  { label: 'Node', value: 1 as const },
  { label: 'Repeater', value: 2 as const },
  { label: 'Room', value: 3 as const },
  { label: 'Sensor', value: 4 as const },
]

function toHex(n: number) { try { return Math.max(0, Number(n)).toString(16) } catch { return String(n) } }
</script>

<style scoped>
</style>
