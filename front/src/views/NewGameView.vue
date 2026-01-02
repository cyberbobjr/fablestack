<script setup lang="ts">
import { ChevronLeft, Play, Scroll, User } from 'lucide-vue-next'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import api, { type ActiveSession, type Character, type Scenario } from '../services/api'
import { useGameDataStore } from '../stores/gameData'
import { useToastStore } from '../stores/toast'

const router = useRouter()
const { t, tm } = useI18n()
const gameDataStore = useGameDataStore()
const toastStore = useToastStore()
const loading = ref(true)
const scenarios = ref<Scenario[]>([])
const characters = ref<Character[]>([])
const activeSessions = ref<ActiveSession[]>([])
const selectedScenario = ref('')
const selectedCharacter = ref('')

const currentMessageIndex = ref(0)
const messages = computed(() => tm('loading_messages') as string[])
const currentMessage = computed(() => {
  if (!messages.value || messages.value.length === 0) return t('ui.loading')
  return messages.value[currentMessageIndex.value % messages.value.length]
})

let messageInterval: ReturnType<typeof setInterval> | null = null

const startMessageCycling = () => {
  if (messageInterval) return
  // Pick a random start index
  currentMessageIndex.value = Math.floor(Math.random() * (messages.value?.length || 1))
  messageInterval = setInterval(() => {
    currentMessageIndex.value++
  }, 3000)
}

const stopMessageCycling = () => {
  if (messageInterval) {
    clearInterval(messageInterval)
    messageInterval = null
  }
}

watch(loading, (newValue) => {
  if (newValue) {
    startMessageCycling()
  } else {
    stopMessageCycling()
  }
}, { immediate: true })

onUnmounted(() => {
  stopMessageCycling()
})

onMounted(async () => {
  try {
    const [scenariosRes, charactersRes, activeSessionsRes] = await Promise.all([
      api.getScenarios(),
      api.getCharacters(),
      api.getActiveSessions()
    ])
    scenarios.value = scenariosRes.data.scenarios
    characters.value = charactersRes.data
    activeSessions.value = activeSessionsRes.data.sessions
  } catch (error) {
    console.error('Error loading new game data:', error)
    toastStore.addToast('Erreur lors du chargement des données', 'error')
  } finally {
    loading.value = false
  }
})

const isScenarioActive = (scenarioId: string | undefined) => {
  if (!scenarioId) return false
  return activeSessions.value.some(session => session.scenario_id === scenarioId)
}

const isCharacterActive = (characterId: string) => {
  return activeSessions.value.some(session => session.character_id === characterId)
}

const startGame = async () => {
  if (!selectedScenario.value || !selectedCharacter.value) return

  loading.value = true
  try {
    const response = await api.startScenario({
      scenario_name: selectedScenario.value,
      character_id: selectedCharacter.value
    })
    router.push({ name: 'game', params: { sessionId: response.data.session_id } })
  } catch (error: any) {
    console.error('Error starting game:', error)
    if (error.response?.status === 409) {
      toastStore.addToast(error.response.data.detail || "Une partie est déjà en cours avec ce personnage ou ce scénario.", 'error')
    } else {
      toastStore.addToast("Erreur lors du démarrage de la partie", 'error')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-8">
    <div class="flex items-center gap-4">
      <router-link to="/" class="text-gray-400 hover:text-white">
        <ChevronLeft :size="24" />
      </router-link>
      <h1 class="text-3xl font-sans font-bold text-fantasy-gold">Nouvelle Partie</h1>
    </div>

    <div v-if="loading" class="text-center py-12 space-y-4">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-fantasy-gold mx-auto"></div>
      <p class="text-fantasy-gold text-lg animate-pulse">{{ currentMessage }}</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-8">
      <!-- Scenario Selection -->
      <div class="space-y-4">
        <h2 class="text-xl font-bold text-fantasy-text flex items-center gap-2">
          <Scroll class="text-fantasy-accent" />
          Choisir un Scénario
        </h2>
        <div class="space-y-3">
          <div v-for="scenario in scenarios" :key="scenario.id || scenario.name"
            class="p-4 rounded border transition-all relative overflow-hidden" :class="[
              isScenarioActive(scenario.id) ? 'opacity-60 cursor-not-allowed bg-fantasy-dark border-fantasy-muted/50 grayscale' :
                selectedScenario === scenario.name ? 'bg-fantasy-secondary border-fantasy-accent ring-1 ring-fantasy-accent cursor-pointer' :
                  'bg-fantasy-secondary border-gray-700 hover:border-gray-500 cursor-pointer'
            ]" @click="!isScenarioActive(scenario.id) && (selectedScenario = scenario.name)">

            <div v-if="isScenarioActive(scenario.id)"
              class="absolute top-2 right-2 bg-red-900/80 text-red-200 text-xs px-2 py-1 rounded">
              En cours
            </div>

            <h3 class="font-bold text-fantasy-text">{{ scenario.title || scenario.name }}</h3>
            <span class="text-xs px-2 py-1 rounded bg-fantasy-dark text-fantasy-muted mt-2 inline-block">{{
              t(`scenario_status.${scenario.status}`)
              }}</span>
          </div>
        </div>
      </div>

      <!-- Character Selection -->
      <div class="space-y-4">
        <div class="flex justify-between items-center">
          <h2 class="text-xl font-bold text-fantasy-text flex items-center gap-2">
            <User class="text-fantasy-accent" />
            Choisir un Héros
          </h2>
          <router-link to="/create-character" class="text-sm text-fantasy-accent hover:text-red-400 font-bold">
            + Créer
          </router-link>
        </div>

        <div class="space-y-3 max-h-[500px] overflow-y-auto pr-2">
          <div v-for="char in characters" :key="char.id"
            class="p-4 rounded border transition-all relative overflow-hidden" :class="[
              isCharacterActive(char.id) ? 'opacity-60 cursor-not-allowed bg-fantasy-dark border-fantasy-muted/50 grayscale' :
                selectedCharacter === char.id ? 'bg-fantasy-secondary border-fantasy-accent ring-1 ring-fantasy-accent cursor-pointer' :
                  'bg-fantasy-secondary border-gray-700 hover:border-gray-500 cursor-pointer'
            ]" @click="!isCharacterActive(char.id) && (selectedCharacter = char.id)">

            <div v-if="isCharacterActive(char.id)"
              class="absolute top-2 right-2 bg-red-900/80 text-red-200 text-xs px-2 py-1 rounded">
              En cours
            </div>

            <div class="flex justify-between items-center">
              <h3 class="font-bold text-fantasy-text">{{ char.name }}</h3>
              <span class="text-sm text-fantasy-muted">Niv. {{ char.level }}</span>
            </div>
            <p class="text-sm text-fantasy-muted capitalize">{{ gameDataStore.translate(char.race, 'races') }} - {{
              gameDataStore.translate(char.culture, 'cultures') }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="flex justify-end pt-6 border-t border-gray-700">
      <button @click="startGame" :disabled="!selectedScenario || !selectedCharacter || loading"
        class="bg-fantasy-accent hover:bg-red-600 text-white font-bold py-3 px-8 rounded flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
        <Play :size="20" />
        Commencer l'Aventure
      </button>
    </div>
  </div>
</template>
