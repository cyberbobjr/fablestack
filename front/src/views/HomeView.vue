<script setup lang="ts">
import { Play, ScrollText, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ConfirmationModal from '../components/ConfirmationModal.vue'
import api, { type ActiveSession } from '../services/api'

const sessions = ref<ActiveSession[]>([])
const loading = ref(true)
const router = useRouter()

// Modal state
const showDeleteModal = ref(false)
const sessionToDelete = ref<string | null>(null)
const deleteLoading = ref(false)

const loadSessions = async () => {
  loading.value = true
  try {
    const response = await api.getActiveSessions()
    sessions.value = response.data.sessions
  } catch (error) {
    console.error('Error loading sessions:', error)
  } finally {
    loading.value = false
  }
}

onMounted(loadSessions)

const continueSession = (sessionId: string) => {
  router.push({ name: 'game', params: { sessionId } })
}

const openDeleteModal = (sessionId: string) => {
  sessionToDelete.value = sessionId
  showDeleteModal.value = true
}

const confirmDelete = async () => {
  if (!sessionToDelete.value) return

  deleteLoading.value = true
  try {
    await api.deleteSession(sessionToDelete.value)
    await loadSessions()
    showDeleteModal.value = false
    sessionToDelete.value = null
  } catch (error) {
    console.error('Error deleting session:', error)
    alert('Erreur lors de la suppression de la session.')
  } finally {
    deleteLoading.value = false
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-8 min-h-screen pb-12">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-sans font-bold text-fantasy-gold">Vos Aventures</h1>
    </div>

    <div v-if="loading" class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-fantasy-gold mx-auto"></div>
      <p class="mt-4 text-gray-400">Chargement des parchemins...</p>
    </div>

    <div v-else-if="sessions.length === 0"
      class="text-center py-12 bg-fantasy-secondary rounded-lg border border-gray-700">
      <ScrollText :size="48" class="mx-auto text-gray-500 mb-4" />
      <h2 class="text-xl font-bold text-fantasy-text">Aucune aventure en cours</h2>
      <p class="text-fantasy-muted mt-2">Le monde attend ses héros. Commencez une nouvelle quête !</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="session in sessions" :key="session.session_id"
        class="bg-fantasy-secondary rounded-lg p-6 border border-gray-700 hover:border-fantasy-accent transition-all cursor-pointer group"
        @click="continueSession(session.session_id)">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h3 class="text-xl font-bold text-fantasy-text group-hover:text-fantasy-accent transition-colors">{{
              session.character_name }}</h3>
            <p class="text-sm text-fantasy-muted">{{ session.scenario_name }}</p>
          </div>
          <Play :size="24" class="text-fantasy-gold opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <div class="mt-4 pt-4 border-t border-gray-700 flex justify-between items-center text-sm text-fantasy-muted">
          <span>ID: {{ session.session_id.slice(0, 8) }}...</span>
          <div class="flex items-center gap-3">
            <button @click.stop="openDeleteModal(session.session_id)"
              class="text-gray-500 hover:text-red-500 transition-colors p-1 cursor-pointer"
              title="Supprimer la session">
              <Trash2 :size="16" />
            </button>
            <span class="text-fantasy-accent group-hover:underline">Continuer</span>
          </div>
        </div>
      </div>
    </div>

    <ConfirmationModal :show="showDeleteModal" title="Supprimer la session ?"
      message="Êtes-vous sûr de vouloir supprimer cette session ? Cette action est irréversible et le personnage sera réinitialisé."
      confirm-text="Supprimer" :loading="deleteLoading" @close="showDeleteModal = false" @confirm="confirmDelete" />
  </div>
</template>
