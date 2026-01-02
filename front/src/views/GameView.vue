<script setup lang="ts">

import { computed, nextTick, onUnmounted, ref, watch, type Component } from 'vue'
import { useRoute } from 'vue-router'

import { Bug, Scroll, Send } from 'lucide-vue-next'
import api, { type Character, type ChoiceData, type PlayerInput, type TimelineEvent } from '../services/api'

import { useI18n } from 'vue-i18n'
import { useGameDataStore } from '../stores/gameData'
import { useUserStore } from '../stores/user'

import CombatEvent from '../components/events/CombatEvent.vue'
import CurrencyEvent from '../components/events/CurrencyEvent.vue'
import ItemEvent from '../components/events/ItemEvent.vue'
import NarrativeEvent from '../components/events/NarrativeEvent.vue'
import SkillCheckEvent from '../components/events/SkillCheckEvent.vue'
import SystemLogEvent from '../components/events/SystemLogEvent.vue'
import UserInputEvent from '../components/events/UserInputEvent.vue'
import CharacterSidebar from '../components/game/CharacterSidebar.vue'
import ChoiceButton from '../components/game/ChoiceButton.vue'
import ConfirmationModal from '../components/ConfirmationModal.vue'

// ...

const getEventComponent = (event: TimelineEvent): Component | null => {
  switch (event.type) {
    case 'USER_INPUT': return UserInputEvent
    case 'SKILL_CHECK': return SkillCheckEvent
    case 'COMBAT_ATTACK':
    case 'COMBAT_DAMAGE': return CombatEvent
    case 'ITEM_ADDED':
    case 'ITEM_CRAFTED': return ItemEvent
    case 'CURRENCY_CHANGE': return CurrencyEvent
    case 'SYSTEM_LOG': return SystemLogEvent
    case 'NARRATIVE': return NarrativeEvent
    default: return null
  }
}

const { t, tm } = useI18n()
const userStore = useUserStore()
const gameDataStore = useGameDataStore()
const route = useRoute()

// --- State ---
const sessionId = computed(() => route.params.sessionId as string)
const timeline = ref<TimelineEvent[]>([]) // Replaces 'messages'
const userInput = ref('')
const loading = ref(false)
const currentLoadingMessage = ref('')
const character = ref<Character | null>(null)
const characterId = ref<string | null>(null)
const chatContainer = ref<HTMLElement | null>(null)
let loadingInterval: ReturnType<typeof setInterval> | null = null

// --- UI Helpers ---


const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// ... (formatTime unchanged)
const formatTime = (timestamp: string) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return isNaN(date.getTime()) ? '' : date.toLocaleTimeString()
}

// --- Data Loading ---

const loadHistory = async () => {
  if (!sessionId.value) return
  try {
    const response = await api.getHistory(sessionId.value)
    if (response.data.history) {
      timeline.value = response.data.history as any as TimelineEvent[]
    } else {
      timeline.value = []
    }

    // Auto-start if empty
    if (timeline.value.length === 0) {
      console.log("Empty history detected. Auto-starting scenario...")
      await executeTurn({
        input_mode: 'text',
        text_content: 'Start the scenario and present the initial situation.',
        hidden: true
      })
    } else {
      // Restore speaker state if we have history
      // Use nextTick or ensure assets are loaded. 
      // Logic: assets loading is watched on sessionId. 
      // We might need to wait for assets? 
      // Let's call it, it relies on speakerAssets ref which might be empty initially but reactivity will fix it? 
      // No, logic is run once.
      // We should run this when assets are loaded OR history changed.
    }

    scrollToBottom()
  } catch (error) {
    console.error('Error loading history:', error)
  }
}

const loadCharacter = async () => {
  // ... (unchanged)
  if (!sessionId.value) return
  try {
    if (!characterId.value) {
      const sessionsRes = await api.getActiveSessions()
      const session = sessionsRes.data.sessions.find(s => s.session_id === sessionId.value)
      if (session) characterId.value = session.character_id
    }
    if (characterId.value) {
      const charRes = await api.getCharacter(characterId.value)
      character.value = charRes.data.character
    }
  } catch (error) {
    console.error('Error loading character:', error)
  }
}

// --- Interaction ---
// ... (sendText, sendChoice unchanged)
const sendText = async () => {
  if (!userInput.value.trim() || loading.value) return
  const text = userInput.value
  userInput.value = ''

  // Optimistic Update
  timeline.value.push({
    type: 'USER_INPUT',
    timestamp: new Date().toISOString(),
    content: text
  })


  await executeTurn({
    input_mode: 'text',
    text_content: text
  })
}
const sendChoice = async (choice: ChoiceData) => {
  if (loading.value) return

  // Optimistic Update? Maybe waiting for server is better for choices
  timeline.value.push({
    type: 'USER_INPUT',
    timestamp: new Date().toISOString(),
    content: choice.label
  })


  await executeTurn({
    input_mode: 'choice',
    text_content: '',
    choice_data: choice
  })
}


const executeTurn = async (input: PlayerInput) => {
  loading.value = true
  scrollToBottom()

  try {
    const reader = await api.playScenarioStream({
      session_id: sessionId.value,
      input: input
    })

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            handleStreamEvent(data)
          } catch (e) {
            console.error('Error parsing SSE:', e)
          }
        }
      }
    }

    // End of stream - flush any remaining buffer
    if (narrativeBuffer.value) {
      flushNarrativeBuffer(true)
    }

    // Refresh state after turn
    await loadCharacter()

  } catch (error) {
    console.error('Error in executeTurn:', error)
    timeline.value.push({
      type: 'SYSTEM_LOG',
      timestamp: new Date().toISOString(),
      content: 'Error communicating with the Oracle.',
      icon: '⚠️'
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const narrativeBuffer = ref('')

const flushNarrativeBuffer = (force = false) => {
  let text = narrativeBuffer.value
  if (!text) return

  // If we are not forcing, and we might be in the middle of a tag, don't flush yet
  // Tag start: "<<"
  // We wait if we see "<<" but not ">>"
  if (!force) {
    const openTag = text.lastIndexOf('<<')
    const closeTag = text.lastIndexOf('>>')
    if (openTag !== -1 && closeTag < openTag) {
      // Incomplete tag detected at the end
      // We flush everything BEFORE the <<
      if (openTag > 0) {
        const safeChunk = text.substring(0, openTag)
        appendToTimeline(safeChunk)
        narrativeBuffer.value = text.substring(openTag)
      }
      return // Wait for more data
    }
  }

  // Process text for valid tags
  // Regex global match, case insensitive, tolerant of spaces
  const tagRegex = /<<\s*SPEAKER\s*:\s*(.*?)\s*>>/gi
  let match

  while ((match = tagRegex.exec(text)) !== null) {
    const rawName = (match[1] || '').trim()
    console.log("Speaker Detected (Stream):", rawName)

    // Removed logic for updating speaker display
  }

  // Remove tags from text for display
  text = text.replace(/<<\s*SPEAKER\s*:\s*(.*?)\s*>>/gi, '')

  if (text) {
    appendToTimeline(text)
  }
  narrativeBuffer.value = ''
}


const appendToTimeline = (content: string) => {
  const lastEvent = timeline.value[timeline.value.length - 1]
  if (lastEvent && lastEvent.type === 'NARRATIVE') {
    lastEvent.content += content
  } else {
    timeline.value.push({
      type: 'NARRATIVE',
      timestamp: new Date().toISOString(),
      content: content
    })
  }
  scrollToBottom()
}

const handleStreamEvent = (data: any) => {
  if (data.type === 'token') {
    narrativeBuffer.value += data.content
    flushNarrativeBuffer()
  }
  // ... (rest unchanged)
  else if (['SKILL_CHECK', 'COMBAT_ATTACK', 'COMBAT_DAMAGE', 'COMBAT_INFO', 'COMBAT_TURN', 'ITEM_ADDED', 'ITEM_REMOVED', 'ITEM_CRAFTED', 'CURRENCY_CHANGE', 'SYSTEM_LOG'].includes(data.type)) {
    // Ensure any pending narrative is flushed before other events (though usually tokens come together)
    flushNarrativeBuffer(true)
    timeline.value.push({
      type: data.type,
      timestamp: new Date().toISOString(),
      content: data.content,
      icon: data.icon,
      metadata: data.metadata
    })
    scrollToBottom()
  }
  else if (data.type === 'system_log') { // Legacy fallback
    flushNarrativeBuffer(true)
    timeline.value.push({
      type: 'SYSTEM_LOG',
      timestamp: new Date().toISOString(),
      content: data.content,
      icon: data.icon
    })
    scrollToBottom()
  }
  else if (data.type === 'choices') {
    flushNarrativeBuffer(true)
    timeline.value.push({
      type: 'CHOICE',
      timestamp: new Date().toISOString(),
      content: data.content // Array of ChoiceData
    })
    scrollToBottom()
  }
  else if (data.type === 'error') {
    flushNarrativeBuffer(true)
    timeline.value.push({
      type: 'SYSTEM_LOG',
      timestamp: new Date().toISOString(),
      content: `Error: ${data.details || data.error}`,
      icon: '❌'
    })
  }
}

// --- Lifecycle ---
watch(sessionId, () => {
  loadHistory()
  loadCharacter()
}, { immediate: true })


const startLoadingAnimation = () => {
  // ... (unchanged)
  const messages = tm('loading_messages') as string[]
  const safeMessages = (Array.isArray(messages) && messages.length > 0) ? messages : [t('ui.loading')]

  const updateMessage = () => {
    const randomIndex = Math.floor(Math.random() * safeMessages.length)
    currentLoadingMessage.value = safeMessages[randomIndex] || t('ui.loading')
  }

  updateMessage()
  loadingInterval = setInterval(updateMessage, 3000)
}

const stopLoadingAnimation = () => {
  // ... (unchanged)
  if (loadingInterval) {
    clearInterval(loadingInterval)
    loadingInterval = null
  }
}

watch(loading, (newVal) => {
  if (newVal) {
    startLoadingAnimation()
  } else {
    stopLoadingAnimation()
  }
})

onUnmounted(() => {
  stopLoadingAnimation()
})

// --- Debug / Restore --- (Simplified for now)
const isDebugMode = ref(false)
const toggleDebugMode = () => isDebugMode.value = !isDebugMode.value



const showRestoreModal = ref(false)
const restoreTargetTimestamp = ref<string | null>(null)

const restoreFrom = (timestamp: string) => {
  restoreTargetTimestamp.value = timestamp
  showRestoreModal.value = true
}

const confirmRestore = async () => {
  if (!restoreTargetTimestamp.value) return

  try {
    loading.value = true
    await api.restoreHistory(sessionId.value, restoreTargetTimestamp.value)
    await loadHistory()
    await loadCharacter()
    showRestoreModal.value = false
    restoreTargetTimestamp.value = null
  } catch (error) {
    console.error('Error restoring history:', error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto flex h-[calc(100vh-100px)] gap-6">
    <!-- Main Area -->
    <div
      class="flex-1 flex flex-col bg-fantasy-dark relative rounded-lg border border-gray-800 overflow-hidden shadow-2xl">
      <!-- Header -->
      <div class="p-4 border-b border-gray-700 flex justify-between items-center bg-fantasy-header z-10 relative">
        <h1 class="text-xl font-bold text-fantasy-gold">{{ t('ui.game_title') }}</h1>

        <!-- Speaker Display -->

        <button @click="toggleDebugMode" class="text-fantasy-muted hover:text-fantasy-accent" title="Debug Mode">
          <Bug :size="20" />
        </button>
      </div>

      <!-- Timeline -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
        <div v-if="timeline.length === 0" class="text-center text-fantasy-muted mt-20 italic">
          {{ t('ui.no_history') }}
        </div>

        <template v-for="(event, index) in timeline" :key="index">
          <component v-if="getEventComponent(event)" :is="getEventComponent(event)" :event="event" :is-debug-mode="isDebugMode"
            @restore="restoreFrom" />
        </template>

        <!-- Choices Block (Full Width) -->
        <template v-if="timeline.length > 0 && timeline[timeline.length - 1]?.type === 'CHOICE' && !loading">
          <div class="mt-6 animate-fade-in-up">
            <h3 class="text-fantasy-gold font-serif text-lg mb-4 flex items-center gap-2">
              <span class="h-px flex-1 bg-gradient-to-r from-transparent to-fantasy-gold/30"></span>
              {{ t('ui.makeChoice') }}
              <span class="h-px flex-1 bg-gradient-to-l from-transparent to-fantasy-gold/30"></span>
            </h3>

            <!-- Choices List -->
            <div class="flex flex-col gap-3 max-w-3xl">
              <ChoiceButton v-for="choice in ((timeline[timeline.length - 1]?.content) as ChoiceData[])"
                :key="choice.id" :choice="choice" :disabled="loading" @select="sendChoice" />
            </div>
          </div>
        </template>

        <!-- Loading Indicator -->
        <div v-if="loading" class="flex justify-start">
          <div
            class="bg-fantasy-secondary px-4 py-3 rounded-2xl rounded-tl-none flex gap-2 items-center text-fantasy-muted text-sm border border-white/5">
            <Scroll :size="16" class="animate-spin-slow" />
            <span class="animate-pulse">{{ currentLoadingMessage }}</span>
          </div>
        </div>

      </div>

      <!-- Input Area -->
      <div class="p-4 bg-fantasy-header border-t border-gray-700">
        <div class="flex gap-3 max-w-6xl mx-auto">
          <input v-model="userInput" @keyup.enter="sendText" type="text" :placeholder="t('ui.placeholder')"
            class="flex-1 bg-fantasy-input border border-gray-600 rounded-xl px-5 py-3 text-fantasy-text focus:border-fantasy-accent focus:ring-1 focus:ring-fantasy-accent focus:outline-none placeholder-gray-500 shadow-inner transition-all"
            :disabled="loading">
          <button @click="sendText" :disabled="loading || !userInput.trim()"
            class="bg-fantasy-accent hover:bg-red-600 text-white p-3 rounded-xl transition-all shadow-lg hover:shadow-red-900/40 transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed">
            <Send :size="20" />
          </button>
        </div>
      </div>
    </div>

    <!-- Sidebar Character Sheet -->
    <CharacterSidebar v-if="character" :character="character" />


    <ConfirmationModal :show="showRestoreModal" title="Restaurer l'historique ?"
      message="Attention : Toutes les actions effectuées après ce point seront définitivement perdues. Voulez-vous continuer ?"
      confirm-text="Restaurer" cancel-text="Annuler" :loading="loading" @close="showRestoreModal = false"
      @confirm="confirmRestore" />
  </div>
</template>

<style scoped>
/* Custom Scrollbar for heavy fantasy feel */
.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: #4a5568;
  border-radius: 3px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: #718096;
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-spin-slow {
  animation: spin 3s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}
</style>
