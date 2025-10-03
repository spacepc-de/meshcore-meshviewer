<template>
  <section class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold">Automations</h2>
      <button @click="newRule" class="px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-500">New rule</button>
    </div>

    <div class="grid md:grid-cols-2 gap-6">
      <!-- Rules list -->
      <div class="rounded border bg-white dark:bg-gray-900/40 dark:border-gray-800 overflow-hidden">
          <div class="px-4 py-2 border-b dark:border-gray-800 flex items-center justify-between">
          <div class="font-medium">Rules</div>
          <div class="text-xs text-gray-500">{{ rules.length }} entries</div>
        </div>
        <div class="divide-y dark:divide-gray-800">
          <div v-for="r in rules" :key="r.id" class="px-4 py-3 flex items-start gap-3 hover:bg-gray-50/70 dark:hover:bg-gray-800/50 cursor-pointer" @click="editRule(r)">
            <input type="checkbox" class="mt-0.5" :checked="r.enabled" @click.stop="toggleEnabled(r)" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <div class="font-medium truncate">{{ r.name }}</div>
                <span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">{{ r.match_type }}: "{{ r.pattern }}"</span>
              </div>
              <div class="text-xs text-gray-600 dark:text-gray-400 mt-0.5 truncate">
                Action: <span class="font-medium">{{ r.action_type }}</span>
                <template v-if="r.action_type==='autoresponse'"> → "{{ truncate(r.response_text, 40) }}"</template>
                <template v-else> → {{ r.mqtt_topic || '-' }}</template>
              </div>
            </div>
            <div class="text-xs text-gray-500 whitespace-nowrap">Prio {{ r.priority }}</div>
          </div>
          <div v-if="!rules.length" class="px-4 py-6 text-sm text-gray-500">No rules defined yet.</div>
        </div>
      </div>

      <!-- Right column: Test -->
      <div class="space-y-6">
        <!-- Test -->
        <div class="rounded border bg-white dark:bg-gray-900/40 dark:border-gray-800">
          <div class="px-4 py-2 border-b dark:border-gray-800 font-medium">Test</div>
          <div class="p-4 space-y-3 text-sm">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs mb-1">Contact name (optional)</label>
                <input v-model="testName" type="text" class="w-full input" placeholder="e.g. Alice" />
              </div>
              <div>
                <label class="block text-xs mb-1">Public Key (optional)</label>
                <input v-model="testKey" type="text" class="w-full input" />
              </div>
            </div>
            <div>
              <label class="block text-xs mb-1">Message text</label>
              <input v-model="testText" type="text" class="w-full input" placeholder="e.g. ping" />
            </div>
            <div class="flex items-center gap-2">
              <button @click="runTest(true)" class="px-3 py-1.5 rounded bg-gray-700 text-white hover:bg-gray-600">Preview</button>
              <button @click="runTest(false)" class="px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-500">Run</button>
            </div>
            <div v-if="testResults" class="mt-2 space-y-2">
              <div v-for="(r, i) in testResults.results" :key="i" class="p-2 rounded bg-gray-50 dark:bg-gray-800/60">
                <div class="text-xs text-gray-500">Rule #{{ r.rule_id }} — {{ r.name }}</div>
                <div v-if="r.skipped" class="text-xs text-yellow-700 dark:text-yellow-300">Skipped: {{ r.reason }}</div>
                <div v-else class="text-sm">
                  <template v-if="r.action?.type === 'autoresponse'">
                    Autoresponse → "{{ r.action.text }}"
                  </template>
                  <template v-else-if="r.action?.type === 'mqtt'">
                    MQTT → <span class="font-mono">{{ r.action.topic }}</span>
                    <span class="text-gray-500"> | </span>
                    <span class="font-mono">{{ r.action.payload }}</span>
                  </template>
                  <template v-else>
                    {{ r.action?.type }}
                  </template>
                  <span v-if="r.action?.executed" class="ml-2 text-xs text-green-700 dark:text-green-300">(executed)</span>
                  <span v-if="r.action?.error" class="ml-2 text-xs text-red-700 dark:text-red-300">Error: {{ r.action.error }}</span>
                </div>
              </div>
              <div v-if="!testResults.results?.length" class="text-sm text-gray-500">No rule matched.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Modal: Create/Edit Rule -->
    <div v-if="modalOpen" class="fixed inset-0 z-50">
      <div class="absolute inset-0 bg-black/50" @click="closeModal"></div>
      <div class="absolute inset-0 p-4 flex items-center justify-center">
        <div class="w-full max-w-5xl bg-white dark:bg-gray-900 rounded-lg shadow-xl overflow-hidden">
          <div class="flex items-center justify-between px-4 py-3 border-b dark:border-gray-800">
            <div class="font-medium">{{ form.id ? 'Edit Rule' : 'Create Rule' }}</div>
            <button @click="closeModal" class="text-xl leading-none">×</button>
          </div>
          <div class="grid md:grid-cols-2 gap-0">
            <!-- Form -->
            <div class="p-4 space-y-3 text-sm">
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs mb-1">Name</label>
                  <input v-model="form.name" type="text" class="w-full input" placeholder="e.g. Ping-Pong" />
                </div>
                <div class="flex items-end gap-3">
                  <label class="inline-flex items-center gap-2 text-xs">
                    <input type="checkbox" v-model="form.enabled" /> Active
                  </label>
                  <label class="inline-flex items-center gap-2 text-xs">
                    <input type="checkbox" v-model="form.only_incoming" /> Incoming only
                  </label>
                </div>
              </div>
              <div>
                <label class="block text-xs mb-1">Description</label>
                <textarea v-model="form.description" rows="2" class="w-full input" placeholder="Optional details about this rule"></textarea>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs mb-1">Match type</label>
                  <select v-model="form.match_type" class="w-full input">
                    <option value="equals">equals</option>
                    <option value="prefix">prefix</option>
                    <option value="contains">contains</option>
                    <option value="regex">regex</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs mb-1">Pattern</label>
                  <input v-model="form.pattern" type="text" class="w-full input" placeholder="e.g. ping" />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <label class="inline-flex items-center gap-2 text-xs">
                  <input type="checkbox" v-model="form.case_sensitive" /> Case-sensitive
                </label>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs mb-1">From name (optional)</label>
                    <input v-model="form.from_name" type="text" class="w-full input" placeholder="Contact name" />
                  </div>
                  <div>
                    <label class="block text-xs mb-1">From public key (optional)</label>
                    <input v-model="form.from_public_key" type="text" class="w-full input" placeholder="…" />
                  </div>
                </div>
              </div>
              <div class="grid grid-cols-3 gap-3 items-end">
                <div>
                  <label class="block text-xs mb-1">Action</label>
                  <select v-model="form.action_type" class="w-full input">
                    <option value="autoresponse">autoresponse</option>
                    <option value="mqtt">mqtt</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs mb-1">Priority</label>
                  <input v-model.number="form.priority" type="number" class="w-full input" />
                </div>
                <label class="inline-flex items-center gap-2 text-xs">
                  <input type="checkbox" v-model="form.stop_processing" /> Stop after match
                </label>
              </div>

              <div v-if="form.action_type==='autoresponse'">
                <label class="block text-xs mb-1">Response text</label>
                <textarea v-model="form.response_text" rows="2" class="w-full input" placeholder="e.g. pong"></textarea>
                <p class="text-xs text-gray-500 mt-1">Placeholders: {name}, {text}, {1}, {2}, …</p>
              </div>

              <div v-else>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs mb-1">MQTT topic</label>
                    <input v-model="form.mqtt_topic" type="text" class="w-full input" placeholder="e.g. mesh/command" />
                  </div>
                  <div>
                    <label class="block text-xs mb-1">Payload</label>
                    <input v-model="form.mqtt_payload" type="text" class="w-full input" placeholder='e.g. {name}:{text}' />
                  </div>
                </div>
                <p class="text-xs text-gray-500 mt-1">Placeholders: {name}, {text}, {1}, {2}, …</p>
              </div>

              <div class="grid grid-cols-3 gap-3 items-end">
                <div>
                  <label class="block text-xs mb-1">Cooldown (sec)</label>
                  <input v-model.number="form.cooldown_seconds" type="number" class="w-full input" />
                </div>
                <div class="col-span-2 flex gap-2 justify-end">
                  <button @click="saveRule" :disabled="saving" class="px-3 py-1.5 rounded bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">{{ form.id ? 'Save' : 'Create' }}</button>
                  <button v-if="form.id" @click="removeRule" :disabled="saving" class="px-3 py-1.5 rounded bg-red-600 text-white hover:bg-red-500 disabled:opacity-50">Delete</button>
                  <button @click="closeModal" class="px-3 py-1.5 rounded bg-gray-200 dark:bg-gray-800 hover:bg-gray-300 dark:hover:bg-gray-700">Close</button>
                </div>
              </div>
            </div>

            <!-- Explanations -->
            <div class="p-4 border-t md:border-t-0 md:border-l dark:border-gray-800 text-sm space-y-3 bg-gray-50 dark:bg-gray-900/40">
              <div class="font-medium">How automations work</div>
              <p>
                Automations inspect incoming messages and optional sender info. When a rule
                matches your configured pattern, the selected action executes.
              </p>
              <div>
                <div class="font-medium text-xs uppercase tracking-wide text-gray-500">Matching</div>
                <ul class="list-disc ml-5 mt-1 space-y-1">
                  <li><span class="font-medium">Match type</span>: choose <em>equals</em>, <em>prefix</em>, <em>contains</em>, or <em>regex</em>.</li>
                  <li><span class="font-medium">Pattern</span>: the text or regex to match on message content.</li>
                  <li><span class="font-medium">Case-sensitive</span>: toggle case sensitivity for text matches.</li>
                  <li><span class="font-medium">From filters</span>: limit by contact name or public key.</li>
                </ul>
              </div>
              <div>
                <div class="font-medium text-xs uppercase tracking-wide text-gray-500">Actions</div>
                <ul class="list-disc ml-5 mt-1 space-y-1">
                  <li><span class="font-medium">Autoresponse</span>: sends a reply message. Supports placeholders like {name}, {text}, {1}…</li>
                  <li><span class="font-medium">MQTT</span>: publishes to a topic with a payload. Placeholders are supported.</li>
                </ul>
              </div>
              <div>
                <div class="font-medium text-xs uppercase tracking-wide text-gray-500">Processing</div>
                <ul class="list-disc ml-5 mt-1 space-y-1">
                  <li><span class="font-medium">Priority</span>: lower numbers run first.</li>
                  <li><span class="font-medium">Stop after match</span>: stop evaluating later rules once this one runs.</li>
                  <li><span class="font-medium">Cooldown</span>: minimum seconds between executions per rule.</li>
                  <li><span class="font-medium">Incoming only</span>: restrict to incoming messages.</li>
                </ul>
              </div>
              <p class="text-xs text-gray-500">Tip: Use the Test panel to simulate messages before enabling rules.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

type Rule = {
  id?: number
  enabled: boolean
  name: string
  description: string
  match_type: 'equals'|'prefix'|'contains'|'regex'
  pattern: string
  case_sensitive: boolean
  only_incoming: boolean
  from_name: string
  from_public_key: string
  action_type: 'autoresponse'|'mqtt'
  response_text: string
  mqtt_topic: string
  mqtt_payload: string
  priority: number
  stop_processing: boolean
  cooldown_seconds: number
}

const rules = ref<Rule[]>([])
const saving = ref(false)
const modalOpen = ref(false)

function defaultRule(): Rule {
  return {
    enabled: true,
    name: '',
    description: '',
    match_type: 'prefix',
    pattern: '',
    case_sensitive: false,
    only_incoming: true,
    from_name: '',
    from_public_key: '',
    action_type: 'autoresponse',
    response_text: 'pong',
    mqtt_topic: '',
    mqtt_payload: '',
    priority: 0,
    stop_processing: true,
    cooldown_seconds: 0,
  }
}
const form = ref<Rule>(defaultRule())

function truncate(s: string, n: number) { return s.length > n ? s.slice(0, n) + '…' : s }

async function loadRules() {
  const { data } = await axios.get('/api/v1/automations/')
  rules.value = data?.items || []
}

function newRule() {
  form.value = defaultRule()
  modalOpen.value = true
}

function editRule(r: Rule) {
  form.value = JSON.parse(JSON.stringify(r))
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
}

async function toggleEnabled(r: Rule) {
  try {
    await axios.patch(`/api/v1/automations/${r.id}/`, { enabled: !r.enabled })
    await loadRules()
  } catch (_) {}
}

async function saveRule() {
  saving.value = true
  try {
    if (form.value.id) {
      const { data } = await axios.put(`/api/v1/automations/${form.value.id}/`, form.value)
      form.value = data
    } else {
      const { data } = await axios.post('/api/v1/automations/', form.value)
      form.value = data
    }
    await loadRules()
    // Auto-close on successful save
    modalOpen.value = false
  } catch (e) {
    console.warn('Save failed', e)
  } finally {
    saving.value = false
  }
}

async function removeRule() {
  if (!form.value.id) return
  saving.value = true
  try {
    await axios.delete(`/api/v1/automations/${form.value.id}/`)
    form.value = defaultRule()
    modalOpen.value = false
    await loadRules()
  } catch (e) {
    console.warn('Delete failed', e)
  } finally {
    saving.value = false
  }
}

const testName = ref('')
const testKey = ref('')
const testText = ref('ping')
const testResults = ref<any | null>(null)
async function runTest(dry: boolean) {
  const { data } = await axios.post('/api/v1/automations/test/', { name: testName.value, public_key: testKey.value, text: testText.value, dry_run: dry })
  testResults.value = data
}

onMounted(loadRules)
</script>

<style scoped>
.input { @apply rounded border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-indigo-500; }
</style>
