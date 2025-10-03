<template>
  <section class="h-[calc(100vh-64px)] md:h-[calc(100vh-72px)] flex flex-col">
    <!-- Page header -->
    <div class="px-3 sm:px-4 md:px-6 pt-3 pb-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold flex items-center gap-2">
          <span>💬</span>
          <span>Messages</span>
        </h2>
      </div>
      <div class="flex items-center gap-2 text-sm">
        <label class="inline-flex items-center gap-2 px-2 py-1.5 rounded-md border text-xs border-gray-200 dark:border-gray-700">
          <input type="checkbox" v-model="onlyUnread" class="rounded" />
          Only unread
        </label>
      </div>
    </div>

    <div v-if="error" class="mx-3 sm:mx-4 md:mx-6 rounded border border-red-300 bg-red-50 dark:bg-red-900/30 dark:border-red-800 text-red-800 dark:text-red-200 px-4 py-2 text-sm">
      {{ error }}
    </div>

    <div class="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-12 gap-4 px-3 sm:px-4 md:px-6 pb-4">
      <!-- Left: Contacts list -->
      <div class="md:col-span-4 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 overflow-hidden flex flex-col min-h-0">
        <div class="border-b px-3 py-2 dark:border-gray-700 flex items-center gap-2 sticky top-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur z-10">
          <div class="relative flex-1">
            <span class="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
          <input v-model="query" type="text" placeholder="Search (name, key, …)" class="w-full pl-8 pr-3 py-2 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
          </div>
          <span class="text-xs text-gray-600 dark:text-gray-300 whitespace-nowrap">{{ filteredItems.length }} contacts</span>
        </div>
        <div class="flex-1 min-h-0 overflow-auto divide-y dark:divide-gray-700 scroll-fade" @scroll="onContactsScroll">
          <button
            v-for="(c, idx) in sortedFilteredItems"
            :key="cKey(c, idx)"
            @click="select(c)"
            :class="['w-full text-left px-3 py-3 hover:bg-gray-50 dark:hover:bg-gray-900/40 transition-colors', selectedKey === c.public_key ? 'bg-indigo-50 dark:bg-indigo-900/20' : '']"
          >
            <div class="flex items-start gap-3">
              <div class="shrink-0 h-9 w-9 rounded-full flex items-center justify-center text-xs font-semibold text-white" :style="{ backgroundColor: avatarColor(c) }">
                {{ avatarInitials(c) }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between gap-2">
                  <div class="font-medium truncate flex items-center gap-2">
                    <span class="truncate">{{ displayName(c) }}</span>
                    <span v-if="isUnread(c)" class="inline-flex items-center justify-center text-[10px] px-1.5 py-0.5 rounded-full bg-red-600 text-white">New</span>
                  </div>
                  <div class="text-[11px] text-gray-500" v-if="latestTs(c)">{{ shortTime(latestTs(c)) }}</div>
                </div>
                <div class="text-[11px] text-gray-600 dark:text-gray-300 truncate" v-if="latestPreview(c)">{{ latestPreview(c) }}</div>
                <div class="text-[11px] text-gray-500" v-else-if="c.public_key">{{ shortKey(c.public_key) }}</div>
                <div class="text-[11px] text-gray-500" v-if="c.adv_lat !== undefined && c.adv_lon !== undefined">{{ c.adv_lat }}, {{ c.adv_lon }}</div>
              </div>
            </div>
          </button>
          <div v-if="!filteredItems.length && !loading" class="px-3 py-4 text-gray-500 dark:text-gray-400">No contacts found.</div>
          <div v-if="loading" class="px-3 py-4 text-gray-500 dark:text-gray-400">Loading…</div>
        </div>
      </div>

      <!-- Right: Chat/detail panel -->
      <div class="md:col-span-8 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 flex flex-col min-h-0">
        <div class="border-b px-4 py-3 dark:border-gray-700 flex items-center justify-between" v-if="selected">
          <div class="flex items-center gap-3">
            <div class="h-8 w-8 rounded-full flex items-center justify-center text-[11px] font-semibold text-white" :style="{ backgroundColor: avatarColor(selected) }">{{ avatarInitials(selected) }}</div>
            <div>
              <div class="font-semibold">{{ displayName(selected) }}</div>
              <div class="text-xs text-gray-600 dark:text-gray-300" v-if="selected.public_key">Key: <span class="font-mono">{{ shortKey(selected.public_key) }}</span></div>
            </div>
          </div>
          <div class="text-xs text-gray-500 space-x-3">
            <span v-if="selected.last_advert">Last advert: {{ formatEpoch(selected.last_advert) }}</span>
            <span v-if="selected.adv_lat !== undefined && selected.adv_lon !== undefined">Pos: {{ selected.adv_lat }}, {{ selected.adv_lon }}</span>
          </div>
        </div>

        <div v-if="!selected" class="flex-1 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 p-6">
          Select a contact on the left.
        </div>

        <div v-else class="flex-1 min-h-0 flex flex-col">
          <!-- Messages area -->
          <div ref="messagesBox" class="p-4 space-y-2 overflow-auto scroll-fade min-h-0 flex-1">
            <div v-if="!messagesForSelected.length" class="text-sm text-gray-500 dark:text-gray-400">No messages yet.</div>
            <template v-for="(m, i) in messagesForSelected" :key="(m.id || (m.ts + '-' + i))">
              <div v-if="isNewDay(i)" class="text-center my-3">
                <span class="inline-flex items-center text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-900/40 text-gray-600 dark:text-gray-300">{{ dayLabel(m.ts) }}</span>
              </div>
              <div :class="['group max-w-[85%] px-3 py-2 rounded-2xl text-sm shadow-sm', m.dir === 'out' ? 'ml-auto text-white bg-gradient-to-br from-indigo-600 to-violet-600' : 'bg-gray-100 dark:bg-gray-900/40 dark:text-gray-100']">
                <div class="whitespace-pre-wrap break-words">{{ m.text }}</div>
                <div class="flex items-center justify-end gap-2 text-[10px] opacity-80 mt-1">
                  <span class="text-right">{{ new Date(m.ts).toLocaleTimeString() }}</span>
                  <template v-if="m.dir === 'out'">
                    <span v-if="m.status === 'sending'" title="Sending…">⏳</span>
                    <span v-else-if="m.status === 'sent'" title="Sent">✓</span>
                    <span v-else-if="m.status === 'delivered'" title="Delivered">✓✓</span>
                    <span v-else-if="m.status === 'failed'" class="cursor-pointer" :title="m.statusText || 'Send failed'" @click="resendMessage(m)">⚠️</span>
                  </template>
                </div>
                <div v-if="m.statusText && m.dir==='out'" class="text-[10px] opacity-70 mt-0.5 text-right hidden group-hover:block">{{ m.statusText }}</div>
              </div>
            </template>
          </div>

          <!-- Composer -->
          <form @submit.prevent="sendDraft" class="border-t dark:border-gray-700 p-3">
            <div class="flex items-end gap-2">
              <textarea v-model="draft" rows="1" @keydown.enter.exact.prevent="sendDraft" @keydown.enter.shift.stop class="flex-1 px-3 py-2 rounded-md border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm resize-none" placeholder="Write a message…"></textarea>
              <button :disabled="!draft.trim()" class="px-3 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Send</button>
            </div>
            <div class="text-[11px] text-gray-500 mt-1">Enter: send · Shift+Enter: newline</div>
          </form>
        </div>
      </div>
    </div>
  </section>
  
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'

type Contact = any
type ContactsResponse = { fetched_at: string; items: Contact[] }

const loading = ref(false)
const error = ref<string | null>(null)
const contactsResp = ref<ContactsResponse | null>(null)
const query = ref('')
const selectedKey = ref<string | null>(null)
const draft = ref('')
const onlyUnread = ref(false)
type ChatMessage = { text: string; ts: number; dir: 'in' | 'out'; id?: string; status?: 'sending' | 'sent' | 'failed' | 'delivered'; statusText?: string; local?: boolean }
const chatByKey = ref<Record<string, ChatMessage[]>>({})
type LatestMeta = { ts: number; dir: 'in' | 'out'; text?: string }
const latestMetaById = ref<Record<string, LatestMeta | undefined>>({})
const lastReadById = ref<Record<string, number>>({})
const messagesBox = ref<HTMLElement | null>(null)
const pollId = ref<number | null>(null)
const pollLatestId = ref<number | null>(null)

// removed lastUpdatedLabel (live view)

function pretty(obj: any) {
  return JSON.stringify(obj, null, 2)
}

function displayName(c: Contact) {
  if (typeof c === 'string') return c
  return c.name || c.display_name || c.label || c.value || (c.public_key ? shortKey(c.public_key) : 'Contact')
}

function shortKey(k: string) {
  if (!k) return ''
  return k.length > 16 ? `${k.slice(0,8)}…${k.slice(-8)}` : k
}

function formatTs(ts: any) {
  try { return new Date(ts).toLocaleString() } catch { return String(ts) }
}

function formatEpoch(sec: any) {
  const n = Number(sec)
  if (!Number.isFinite(n)) return String(sec)
  return new Date(n * 1000).toLocaleString()
}

const items = computed(() => contactsResp.value?.items || [])
const filteredItems = computed(() => {
  const q = query.value.trim().toLowerCase()
  let arr = items.value
  if (q) arr = arr.filter(c => JSON.stringify(c).toLowerCase().includes(q))
  if (onlyUnread.value) arr = arr.filter(c => isUnread(c))
  return arr
})

const sortedFilteredItems = computed(() => {
  const arr = [...filteredItems.value]
  arr.sort((a: any, b: any) => {
    const ta = latestTs(a)
    const tb = latestTs(b)
    const hasA = ta != null
    const hasB = tb != null
    // Priority: contacts WITH messages first
    if (hasA !== hasB) return hasA ? -1 : 1
    // If both have messages, sort by newest message desc
    if (hasA && hasB && (ta as number) !== (tb as number)) return (tb as number) - (ta as number)
    // Otherwise, fall back to name sorting for stability
    const na = (displayName(a) || '').toLowerCase()
    const nb = (displayName(b) || '').toLowerCase()
    return na.localeCompare(nb)
  })
  return arr
})

const selected = computed<any>(() => {
  const key = selectedKey.value
  if (!key) return sortedFilteredItems.value[0]
  return sortedFilteredItems.value.find((c: any) => c.public_key === key) || sortedFilteredItems.value[0]
})

const messagesForSelected = computed<ChatMessage[]>(() => {
  const key = selected.value?.public_key
  const name = selected.value?.name || selected.value?.adv_name
  const id = key || (name ? `name:${name}` : '')
  if (!id) return []
  return chatByKey.value[id] || []
})

// View order: oldest -> newest (newest at bottom)

async function fetchContacts() {
  loading.value = true
  error.value = null
  try {
    const { data } = await axios.get('/api/v1/contacts/latest/', { responseType: 'json' })

    // Accept multiple shapes for resilience:
    // - { fetched_at, items: [...] }
    // - [ ... ]
    // - string with one contact per line
    const nowIso = new Date().toISOString()
    if (data && typeof data === 'object' && Array.isArray((data as any).items)) {
      contactsResp.value = {
        fetched_at: (data as any).fetched_at || nowIso,
        items: (data as any).items,
      }
    } else if (Array.isArray(data)) {
      contactsResp.value = {
        fetched_at: nowIso,
        items: data,
      }
    } else if (typeof data === 'string') {
      const items = data
        .replace(/\r/g, '')
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean)
        .map(name => ({ name }))
      contactsResp.value = {
        fetched_at: nowIso,
        items,
      }
    } else {
      // Unknown shape
      contactsResp.value = {
        fetched_at: nowIso,
        items: [],
      }
    }
    // After contacts load, fetch latest message meta so times show immediately
    try {
      const count = contactsResp.value.items?.length || 0
      await refreshLatestForContacts(Math.min(50, count || 0))
    } catch {}
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || 'Unknown error'
    error.value = `Fetch failed: ${msg}`
  } finally {
    loading.value = false
  }
}

// removed manual refresh (live view)

function cKey(c: Contact, idx: number) {
  if (typeof c === 'string') return `${c}-${idx}`
  return c.public_key || c.id || c.name || c.value || idx
}

onMounted(() => fetchContacts())
onMounted(() => startPolling())
onUnmounted(() => stopPolling())

function select(c: any) {
  if (c?.public_key) selectedKey.value = c.public_key
  const id = contactId(c)
  if (id) {
    lastReadById.value[id] = Date.now()
    persistLastRead()
  }
}

function shortTime(ts: any) {
  try { return new Date(ts).toLocaleTimeString() } catch { return '' }
}

function scrollToBottom() {
  const el = messagesBox.value
  if (el) el.scrollTop = el.scrollHeight
}

async function sendDraft() {
  const text = draft.value.trim()
  if (!text || !selected.value) return
  const name = selected.value.name || selected.value.adv_name || ''
  const public_key = selected.value.public_key || ''
  const convId = public_key || `name:${name}`
  const arr = chatByKey.value[convId] || (chatByKey.value[convId] = [])
  const tmpId = `tmp-${Date.now()}-${Math.random().toString(36).slice(2)}`
  const now = Date.now()
  const msg: ChatMessage = { id: tmpId, text, ts: now, dir: 'out', status: 'sending', local: true }
  arr.push(msg)
  draft.value = ''
  await nextTick(); scrollToBottom()
  latestMetaById.value[convId] = { ts: now, dir: 'out', text }
  try {
    const { data } = await axios.post('/api/v1/messages/send/', { name, public_key, text, client_id: tmpId })
    msg.statusText = (data && (data.status || data.detail)) || 'Sent'
    const st = String(msg.statusText || '').toLowerCase()
    msg.status = st.includes('deliver') || st.includes('ack') ? 'delivered' : 'sent'
    msg.local = true
  } catch (e: any) {
    msg.status = 'failed'
    msg.statusText = e?.response?.data?.error || e?.message || 'Send failed'
  }
}

async function resendMessage(m: ChatMessage) {
  if (!selected.value || !m || !m.text) return
  if (m.status === 'sending') return
  const name = selected.value.name || selected.value.adv_name || ''
  const public_key = selected.value.public_key || ''
  m.status = 'sending'
  m.statusText = 'Sending…'
  try {
    const { data } = await axios.post('/api/v1/messages/send/', { name, public_key, text: m.text, client_id: m.id || undefined })
    m.statusText = (data && (data.status || data.detail)) || 'Sent'
    const st = String(m.statusText || '').toLowerCase()
    m.status = st.includes('deliver') || st.includes('ack') ? 'delivered' : 'sent'
  } catch (e: any) {
    m.status = 'failed'
    m.statusText = e?.response?.data?.error || e?.message || 'Send failed'
  }
}

async function loadMessagesForSelected(opts?: { forceScroll?: boolean }) {
  const wasNearBottom = (() => {
    const el = messagesBox.value
    if (!el) return true
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight
    return distance < 48
  })()
  const key = selected.value?.public_key
  const name = selected.value?.name || selected.value?.adv_name
  if (!key && !name) return
  try {
    const { data } = await axios.get('/api/v1/messages/', { params: { public_key: key, name, limit: 100 } })
    const fetched = (data?.items || []).map((m: any) => ({
      text: m.text,
      ts: new Date(m.ts).getTime(),
      dir: m.direction === 'out' ? 'out' : 'in',
      id: m.client_id || String(m.id || ''),
      status: m.status || undefined,
    })) as ChatMessage[]
    const id = key || `name:${name}`
    // Merge ephemeral local messages (sending/failed) that aren't confirmed yet
    const existing = chatByKey.value[id] || []
    const ephemeral = existing.filter(m => m.local)
    const fetchedOldestFirst = fetched.reverse()
    const merged: ChatMessage[] = []
    for (const fm of fetchedOldestFirst) {
      merged.push(fm)
    }
    for (const em of ephemeral) {
      const dup = merged.some(fm => fm.dir === 'out' && fm.text === em.text && Math.abs(fm.ts - (em.ts || 0)) < 15000)
      if (!dup) merged.push(em)
    }
    merged.sort((a,b) => a.ts - b.ts)
    chatByKey.value[id] = merged
    // compute latest meta
    const latest = chatByKey.value[id].length ? chatByKey.value[id][chatByKey.value[id].length - 1] : undefined
    if (latest) latestMetaById.value[id] = { ts: latest.ts, dir: latest.dir, text: latest.text }
    await nextTick()
    if (opts?.forceScroll || wasNearBottom) {
      scrollToBottom()
    }
    // mark as read when viewing
    lastReadById.value[id] = Date.now()
    persistLastRead()
  } catch (e) {
    // ignore
  }
}

watch(selected, () => { loadMessagesForSelected({ forceScroll: true }) })

function startPolling() {
  stopPolling()
  pollId.value = window.setInterval(() => {
    loadMessagesForSelected({ forceScroll: false })
  }, 5000)
}

function stopPolling() {
  if (pollId.value) {
    window.clearInterval(pollId.value)
    pollId.value = null
  }
}

// Helpers for IDs and unread/sorting
function contactId(c: any): string {
  if (!c) return ''
  return c.public_key || (c.name ? `name:${c.name}` : (c.adv_name ? `name:${c.adv_name}` : ''))
}

function latestTs(c: any): number | null {
  const id = contactId(c)
  const meta = id ? latestMetaById.value[id] : undefined
  return meta?.ts || null
}

function isUnread(c: any): boolean {
  const id = contactId(c)
  if (!id) return false
  const meta = latestMetaById.value[id]
  const lastRead = lastReadById.value[id] || 0
  if (!meta) return false
  return meta.dir === 'in' && meta.ts > lastRead
}

// Poll latest metadata for visible contacts
async function refreshLatestForContacts(limit = 25) {
  const list = sortedFilteredItems.value.slice(0, limit)
  await Promise.all(
    list.map(async (c: any) => {
      const id = contactId(c)
      if (!id) return
      try {
        const params: any = {}
        if (c.public_key) params.public_key = c.public_key
        const name = c.name || c.adv_name
        if (name) params.name = name
        params.limit = 1
        const { data } = await axios.get('/api/v1/messages/', { params })
        const m = (data?.items || [])[0]
        if (m) {
          const ts = new Date(m.ts).getTime()
          const dir = m.direction === 'out' ? 'out' as const : 'in' as const
          latestMetaById.value[id] = { ts, dir, text: m.text }
        }
      } catch (e) {
        // ignore per-contact errors
      }
    })
  )
}

function startPollingLatest() {
  stopPollingLatest()
  // initial kick
  refreshLatestForContacts().catch(() => {})
  pollLatestId.value = window.setInterval(() => {
    refreshLatestForContacts().catch(() => {})
  }, 10000)
}

function stopPollingLatest() {
  if (pollLatestId.value) {
    window.clearInterval(pollLatestId.value)
    pollLatestId.value = null
  }
}

function persistLastRead() {
  try { localStorage.setItem('lastReadById', JSON.stringify(lastReadById.value)) } catch {}
}

function loadLastRead() {
  try {
    const s = localStorage.getItem('lastReadById')
    if (s) lastReadById.value = JSON.parse(s)
  } catch {}
}

function onMessagesScroll() { /* reserved for dynamic fades if needed */ }
function onContactsScroll() { /* reserved for dynamic fades if needed */ }

onMounted(() => {
  loadLastRead()
  startPollingLatest()
})
onUnmounted(() => stopPollingLatest())

// UI helpers
function latestPreview(c: any): string | null {
  const id = contactId(c)
  const meta = id ? latestMetaById.value[id] : undefined
  if (!meta?.text) return null
  const t = meta.text.trim()
  return t.length > 80 ? t.slice(0, 80) + '…' : t
}

function avatarInitials(c: any): string {
  const n = displayName(c) || ''
  const words = String(n).split(/\s+/).filter(Boolean)
  const first = words[0]?.[0] || 'U'
  const second = words[1]?.[0] || ''
  return (first + second).toUpperCase()
}

function avatarColor(c: any): string {
  const base = c?.public_key || displayName(c) || 'x'
  let h = 0
  for (let i = 0; i < String(base).length; i++) h = (h * 31 + String(base).charCodeAt(i)) % 360
  return `hsl(${h} 70% 45%)`
}

function isNewDay(i: number): boolean {
  if (i === 0) return true
  const cur = new Date(messagesForSelected.value[i].ts)
  const prev = new Date(messagesForSelected.value[i - 1].ts)
  return cur.toDateString() !== prev.toDateString()
}

function dayLabel(ts: number): string {
  const d = new Date(ts)
  const today = new Date()
  const yd = new Date(Date.now() - 24 * 3600 * 1000)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yd.toDateString()) return 'Yesterday'
  return d.toLocaleDateString()
}
</script>
