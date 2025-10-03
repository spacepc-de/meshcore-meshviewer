<template>
  <div class="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100">
    <header class="border-b border-gray-200 dark:border-gray-800/80 bg-white/70 dark:bg-gray-900/60 backdrop-blur supports-[backdrop-filter]:bg-white/60 sticky top-0 z-30">
      <div class="w-full px-4 py-3">
        <div class="flex items-center justify-between gap-3">
          <!-- Brand -->
          <div class="flex items-center gap-2">
            <img src="/logo.svg" alt="Meshviewer" class="h-8 w-8" />
            <h1 class="font-semibold tracking-tight">Meshviewer</h1>
          </div>

          <!-- Desktop nav -->
          <nav class="hidden md:flex items-center gap-1 text-sm">
            <AppLink to="/dashboard" :active="isActive('dashboard')">
              <span class="i">🏠</span>
              <span>Dashboard</span>
            </AppLink>
            <AppLink to="/map" :active="isActive('map')">
              <span class="i">🗺️</span>
              <span>Map</span>
            </AppLink>
            <AppLink to="/devices" :active="isActive('devices')">
              <span class="i">📟</span>
              <span>Devices</span>
            </AppLink>
            <AppLink to="/messages" :active="isActive('messages')">
              <span class="i">💬</span>
              <span>Messages</span>
            </AppLink>
            <AppLink to="/automation" :active="isActive('automation')">
              <span class="i">⚙️</span>
              <span>Automation</span>
            </AppLink>
            <AppLink to="/settings" :active="isActive('settings')">
              <span class="i">🛠️</span>
              <span>Settings</span>
            </AppLink>
          </nav>

          <!-- Actions -->
          <div class="flex items-center gap-2">
            <!-- Connection status indicator -->
            <div
              class="hidden md:flex items-center gap-2 px-2 py-1 rounded-md border text-xs"
              :class="isConnected ? 'border-green-300 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300' : 'border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300'"
              :title="isConnected ? 'Connected' : (conn.reconnecting ? 'Reconnecting…' : 'Disconnected')"
            >
              <span
                class="inline-block h-2 w-2 rounded-full"
                :class="isConnected ? 'bg-green-500' : (conn.reconnecting ? 'bg-yellow-500' : 'bg-red-500')"
              ></span>
              <span>Connected</span>
            </div>
            <button @click="toggleDark" class="inline-flex items-center justify-center h-8 w-8 rounded-md border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800" :title="isDark ? 'Dark mode: on' : 'Dark mode: off'">
              <span v-if="isDark">🌙</span>
              <span v-else>☀️</span>
            </button>
            <button @click="menuOpen = !menuOpen" class="md:hidden inline-flex items-center justify-center h-8 w-8 rounded-md border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800" aria-label="Toggle menu">
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
            </button>
          </div>
        </div>

        <!-- Mobile nav -->
        <nav v-if="menuOpen" class="md:hidden mt-3 grid grid-cols-2 gap-2 text-sm">
          <!-- Mobile: Connection status indicator (full-width) -->
          <div class="col-span-2 flex items-center justify-between px-3 py-2 rounded-md border" :class="isConnected ? 'border-green-300 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300' : 'border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300'">
            <div class="flex items-center gap-2">
              <span class="inline-block h-2 w-2 rounded-full" :class="isConnected ? 'bg-green-500' : (conn.reconnecting ? 'bg-yellow-500' : 'bg-red-500')"></span>
              <span class="text-xs">Connected</span>
            </div>
            <button @click="conn.attemptReconnect" class="text-xs underline opacity-80 hover:opacity-100" :disabled="conn.reconnecting || isConnected">
              {{ conn.reconnecting ? 'Reconnecting…' : (isConnected ? 'OK' : 'Reconnect') }}
            </button>
          </div>
          <AppLink to="/dashboard" :active="isActive('dashboard')" @click="menuOpen=false"><span class="i">🏠</span><span>Dashboard</span></AppLink>
          <AppLink to="/map" :active="isActive('map')" @click="menuOpen=false"><span class="i">🗺️</span><span>Map</span></AppLink>
          <AppLink to="/devices" :active="isActive('devices')" @click="menuOpen=false"><span class="i">📟</span><span>Devices</span></AppLink>
          <AppLink to="/messages" :active="isActive('messages')" @click="menuOpen=false"><span class="i">💬</span><span>Messages</span></AppLink>
          <AppLink to="/automation" :active="isActive('automation')" @click="menuOpen=false"><span class="i">⚙️</span><span>Automation</span></AppLink>
          <AppLink to="/settings" :active="isActive('settings')" @click="menuOpen=false"><span class="i">🛠️</span><span>Settings</span></AppLink>
        </nav>
      </div>
    </header>
    <main :class="mainClass">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { computed, ref, watch, onMounted, defineComponent, h } from 'vue'
import { useConnectionStore } from './stores/connection'

const menuOpen = ref(false)
const route = useRoute()
function isActive(name: string) { return route.name === name }

const isDark = ref(false)
onMounted(() => {
  const saved = localStorage.getItem('theme')
  isDark.value = saved ? saved === 'dark' : (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', isDark.value)
})
watch(isDark, (v) => {
  document.documentElement.classList.toggle('dark', v)
})

function toggleDark() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  document.documentElement.classList.toggle('dark', isDark.value)
}

// Small wrapper component for consistent nav links
const AppLink = defineComponent({
  props: { to: { type: String, required: true }, active: { type: Boolean, default: false } },
  emits: ['click'],
  setup(props, { slots, emit }) {
    return () => h(
      RouterLink,
      {
        to: props.to,
        class: [
          'inline-flex items-center gap-2 px-3 py-2 rounded-md border text-sm transition-colors',
          props.active
            ? 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900/30 dark:border-indigo-800 dark:text-indigo-200'
            : 'border-transparent hover:border-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 dark:hover:border-gray-700'
        ],
        onClick: () => emit('click')
      },
      slots.default ? { default: () => slots.default!() } : undefined
    )
  }
})

// Full-bleed layout for specific routes
const mainClass = computed(() => {
  if (route.name === 'messages') return 'px-0 py-0'
  if (route.name === 'dashboard') return 'px-4 py-8'
  return 'max-w-6xl mx-auto px-4 py-8'
})

// Connection status
const conn = useConnectionStore()
const isConnected = computed(() => conn.connected === true)
</script>

<style scoped>
.i { display: inline-flex; width: 1rem; justify-content: center; }
</style>
