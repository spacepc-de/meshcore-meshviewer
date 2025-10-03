<template>
  <section class="space-y-6">
    <h2 class="text-xl font-semibold">Settings</h2>

    <div class="rounded border bg-white dark:bg-gray-800 dark:border-gray-700 p-4 space-y-4">
      <div>
        <div class="font-medium">Telemetry Collector</div>
        <p class="text-sm text-gray-600 dark:text-gray-300">Interval (seconds) for background contact_info fetches per contact.</p>
        <div class="mt-2 rounded border border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200 p-3 text-xs leading-relaxed">
          <div class="font-medium mb-1">Important (Telemetry Collector behavior)</div>
          <p>
            Fetching telemetry/status can block message reception on the device/CLI and thus delay messages.
            By default, only the node info is fetched (~1 second per device).
            When you enable <em>Telemetry</em> and <em>Status</em>, each device can take up to ~15 seconds on timeouts.
            With many devices, this may result in not receiving messages for several minutes.
          </p>
          <p class="mt-1">
            In addition, telemetry/status requests frequently fail at the moment; it's unclear whether the root cause
            is the device firmware or the meshcore-cli.
          </p>
        </div>
      </div>

      <form @submit.prevent="save" class="space-y-3">
        <div class="flex items-center gap-3">
          <input v-model.number="interval" type="number" min="0" step="1" class="w-40 px-3 py-2 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
          <span class="text-sm text-gray-600 dark:text-gray-300">Aktuell: <strong>{{ currentText }}</strong></span>
        </div>
        <label class="inline-flex items-start gap-2 text-sm">
          <input v-model="enableTelemetry" type="checkbox" class="mt-0.5 rounded border-gray-300" />
          <span>
            Request telemetry from contacts (optional)
            <div class="text-xs text-gray-600 dark:text-gray-300 mt-1">
              Note: Telemetry requests may currently fail and can also impact message reception. Use with caution.
            </div>
          </span>
        </label>
        <label class="inline-flex items-start gap-2 text-sm">
          <input v-model="enableStatus" type="checkbox" class="mt-0.5 rounded border-gray-300" />
          <span>
            Request status from contacts (optional)
            <div class="text-xs text-gray-600 dark:text-gray-300 mt-1">
              Tip: Disable if queries take long (offline nodes can cause long waits).
            </div>
          </span>
        </label>
        <div class="flex items-center gap-2">
          <button :disabled="saving" class="px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Save</button>
          <div v-if="error" class="text-sm text-red-700 dark:text-red-300">{{ error }}</div>
          <div v-if="ok" class="text-sm text-green-700 dark:text-green-300">Saved.</div>
        </div>
      </form>
    </div>

    <div class="rounded border bg-white dark:bg-gray-800 dark:border-gray-700 p-4 space-y-4">
      <div>
        <div class="font-medium">MQTT</div>
        <p class="text-sm text-gray-600 dark:text-gray-300">Server, port, credentials, optional TLS (MQTTS), and a default community.</p>
      </div>

      <form @submit.prevent="saveMQTT" class="space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="space-y-1">
            <label class="text-sm">Server</label>
            <input v-model="mqtt.server" type="text" placeholder="broker.example.com" class="w-full px-3 py-2 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
          </div>
          <div class="space-y-1">
            <label class="text-sm">Port</label>
            <input v-model.number="mqtt.port" type="number" min="1" max="65535" step="1" class="w-full px-3 py-2 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
          </div>
          <div class="space-y-1">
            <label class="text-sm">Username</label>
            <input v-model="mqtt.username" type="text" class="w-full px-3 py-2 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
          </div>
          <div class="space-y-1">
            <label class="text-sm">Password</label>
            <input v-model="passwordInput" type="password" autocomplete="new-password" class="w-full px-3 py-2 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
            <div class="text-xs text-gray-600 dark:text-gray-300">
              <span v-if="passwordSet">A password is set.</span>
              <button type="button" class="ml-2 underline hover:no-underline" @click="clearPassword = !clearPassword">{{ clearPassword ? 'Do not clear' : 'Clear password' }}</button>
            </div>
          </div>
          <div class="space-y-1">
            <label class="text-sm">Default Community</label>
            <input v-model="mqtt.default_community" type="text" placeholder="e.g. main" class="w-full px-3 py-2 rounded border bg-white dark:bg-gray-800 dark:border-gray-700 text-sm" />
          </div>
          <div class="flex items-end gap-2">
            <label class="inline-flex items-center gap-2 text-sm">
              <input v-model="mqtt.use_tls" type="checkbox" class="rounded border-gray-300" />
              <span>Use MQTTS (TLS)</span>
            </label>
          </div>
        </div>

        <div class="flex items-center gap-3 flex-wrap">
          <button :disabled="mqttSaving || mqttTesting" class="px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Save</button>
          <button type="button" @click="testMQTT" :disabled="mqttSaving || mqttTesting" class="px-3 py-1.5 rounded bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-50">Test connection</button>
          <div v-if="mqttTesting" class="text-sm text-gray-700 dark:text-gray-300">Testing…</div>
          <div v-if="mqttTestError" class="text-sm text-red-700 dark:text-red-300">Error: {{ mqttTestError }}</div>
          <div v-if="mqttTestOk" class="text-sm text-green-700 dark:text-green-300">Connection successful.</div>
          <div v-if="mqttError" class="text-sm text-red-700 dark:text-red-300">{{ mqttError }}</div>
          <div v-if="mqttOk" class="text-sm text-green-700 dark:text-green-300">Saved.</div>
        </div>
      </form>
    </div>

    <div class="rounded border bg-white dark:bg-gray-800 dark:border-gray-700 p-4 space-y-2">
      <div class="font-medium">About</div>
      <ul class="text-sm text-gray-700 dark:text-gray-300 space-y-1">
        <li>
          GitHub:
          <a href="https://github.com/spacepc-de" target="_blank" rel="noopener noreferrer" class="text-indigo-600 dark:text-indigo-400 hover:underline">github.com/spacepc-de</a>
        </li>
        <li>
          Website:
          <a href="https://spacepc.de" target="_blank" rel="noopener noreferrer" class="text-indigo-600 dark:text-indigo-400 hover:underline">spacepc.de</a>
        </li>
        <li>
          Kontakt:
          <a href="mailto:kontakt@spacepc.de" class="text-indigo-600 dark:text-indigo-400 hover:underline">kontakt@spacepc.de</a>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'

const interval = ref<number>(300)
const enableTelemetry = ref<boolean>(false)
const enableStatus = ref<boolean>(true)
const saving = ref(false)
const error = ref<string | null>(null)
const ok = ref(false)

const currentText = computed(() => `${interval.value}s`)

async function load() {
  try {
    const { data } = await axios.get('/api/v1/settings/collector/')
    if (typeof data?.interval_seconds === 'number') interval.value = data.interval_seconds
    enableTelemetry.value = !!data?.enable_req_telemetry
    if (typeof data?.enable_req_status !== 'undefined') enableStatus.value = !!data.enable_req_status
  } catch (e: any) {
    // eslint-disable-next-line no-console
    console.warn('Failed to load settings', e)
  }
}

async function save() {
  saving.value = true
  error.value = null
  ok.value = false
  try {
    const { data } = await axios.put('/api/v1/settings/collector/', { interval_seconds: interval.value, enable_req_telemetry: enableTelemetry.value, enable_req_status: enableStatus.value })
    interval.value = data?.interval_seconds ?? interval.value
    enableTelemetry.value = !!data?.enable_req_telemetry
    if (typeof data?.enable_req_status !== 'undefined') enableStatus.value = !!data.enable_req_status
    ok.value = true
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Failed to save'
  } finally {
    saving.value = false
  }
}

onMounted(load)

// MQTT state
const mqtt = ref<{ server: string; port: number; username: string; use_tls: boolean; default_community: string }>({
  server: '',
  port: 1883,
  username: '',
  use_tls: false,
  default_community: '',
})
const passwordInput = ref<string>('')
const passwordSet = ref<boolean>(false)
const clearPassword = ref<boolean>(false)
const mqttSaving = ref(false)
const mqttError = ref<string | null>(null)
const mqttOk = ref(false)
const mqttTesting = ref(false)
const mqttTestError = ref<string | null>(null)
const mqttTestOk = ref(false)

async function loadMQTT() {
  try {
    const { data } = await axios.get('/api/v1/settings/mqtt/')
    mqtt.value.server = data?.server ?? ''
    mqtt.value.port = typeof data?.port === 'number' ? data.port : 1883
    mqtt.value.username = data?.username ?? ''
    mqtt.value.use_tls = !!data?.use_tls
    mqtt.value.default_community = data?.default_community ?? ''
    passwordSet.value = !!data?.password_set
    passwordInput.value = ''
    clearPassword.value = false
  } catch (e: any) {
    // eslint-disable-next-line no-console
    console.warn('Failed to load MQTT settings', e)
  }
}

async function saveMQTT() {
  mqttSaving.value = true
  mqttError.value = null
  mqttOk.value = false
  try {
    const payload: any = {
      server: mqtt.value.server,
      port: mqtt.value.port,
      username: mqtt.value.username,
      use_tls: mqtt.value.use_tls,
      default_community: mqtt.value.default_community,
    }
    if (clearPassword.value || (passwordInput.value && passwordInput.value.length > 0)) {
      payload.password = clearPassword.value ? '' : passwordInput.value
    }
    const { data } = await axios.put('/api/v1/settings/mqtt/', payload)
    mqtt.value.server = data?.server ?? mqtt.value.server
    mqtt.value.port = typeof data?.port === 'number' ? data.port : mqtt.value.port
    mqtt.value.username = data?.username ?? mqtt.value.username
    mqtt.value.use_tls = !!data?.use_tls
    mqtt.value.default_community = data?.default_community ?? mqtt.value.default_community
    passwordSet.value = !!data?.password_set
    passwordInput.value = ''
    clearPassword.value = false
    mqttOk.value = true
  } catch (e: any) {
    mqttError.value = e?.response?.data?.detail || e?.message || 'Failed to save'
  } finally {
    mqttSaving.value = false
  }
}

onMounted(loadMQTT)

async function testMQTT() {
  mqttTesting.value = true
  mqttTestError.value = null
  mqttTestOk.value = false
  try {
    const payload: any = {
      server: mqtt.value.server,
      port: mqtt.value.port,
      username: mqtt.value.username,
      use_tls: mqtt.value.use_tls,
    }
    // send password if user entered one, or they want to clear (to test without pw)
    if (clearPassword.value || (passwordInput.value && passwordInput.value.length > 0)) {
      payload.password = clearPassword.value ? '' : passwordInput.value
    }
    const { data } = await axios.post('/api/v1/settings/mqtt/test/', payload)
    if (data?.ok) {
      mqttTestOk.value = true
    } else {
      mqttTestError.value = data?.detail || 'Test fehlgeschlagen'
    }
  } catch (e: any) {
    mqttTestError.value = e?.response?.data?.detail || e?.message || 'Test failed'
  } finally {
    mqttTesting.value = false
  }
}
</script>
