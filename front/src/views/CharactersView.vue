<script setup lang="ts">
import { ChevronLeft, Edit, Eye, PlusCircle, Trash2, User } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import ConfirmationModal from '../components/ConfirmationModal.vue'
import api, { type Character } from '../services/api'

const router = useRouter()
const { t } = useI18n()
const loading = ref(true)
const characters = ref<Character[]>([])
const showDeleteModal = ref(false)
const charToDelete = ref<string | null>(null)
const deleteLoading = ref(false)

const loadCharacters = async () => {
    loading.value = true
    try {
        const response = await api.getCharacters()
        characters.value = response.data
    } catch (error) {
        console.error('Error loading characters:', error)
    } finally {
        loading.value = false
    }
}

onMounted(loadCharacters)

const viewCharacter = (id: string) => {
    router.push({ name: 'character-sheet', params: { id } })
}

const editCharacter = (id: string) => {
    router.push({ name: 'edit-character', params: { id } })
}

const createCharacter = () => {
    router.push('/create-character')
}

const openDeleteModal = (id: string) => {
    charToDelete.value = id
    showDeleteModal.value = true
}

const confirmDelete = async () => {
    if (!charToDelete.value) return

    deleteLoading.value = true
    try {
        await api.deleteCharacter(charToDelete.value)
        await loadCharacters()
        showDeleteModal.value = false
        charToDelete.value = null
    } catch (error) {
        console.error('Error deleting character:', error)
    } finally {
        deleteLoading.value = false
    }
}
</script>

<template>
    <div class="max-w-7xl mx-auto space-y-8">
        <div class="flex justify-between items-center">
            <div class="flex items-center gap-4">
                <router-link to="/" class="text-gray-400 hover:text-white">
                    <ChevronLeft :size="24" />
                </router-link>
                <h1 class="text-3xl font-sans font-bold text-fantasy-gold">Personnages</h1>
            </div>
            <button @click="createCharacter"
                class="flex items-center gap-2 bg-fantasy-accent hover:bg-red-600 text-white px-4 py-2 rounded transition-colors cursor-pointer">
                <PlusCircle :size="20" />
                Nouveau Personnage
            </button>
        </div>

        <div v-if="loading" class="text-center py-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-fantasy-gold mx-auto"></div>
            <p class="mt-4 text-fantasy-muted">Recensement des héros...</p>
        </div>

        <div v-else-if="characters.length === 0"
            class="text-center py-12 bg-fantasy-secondary rounded-lg border border-gray-700">
            <User :size="48" class="mx-auto text-gray-500 mb-4" />
            <h2 class="text-xl font-bold text-fantasy-text">Aucun personnage</h2>
            <p class="text-fantasy-muted mt-2">La taverne est vide. Créez votre premier héros !</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div v-for="char in characters" :key="char.id"
                class="bg-fantasy-secondary rounded-lg p-6 border border-gray-700 hover:border-fantasy-accent transition-all group">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h3
                            class="text-xl font-bold text-fantasy-text group-hover:text-fantasy-accent transition-colors">
                            {{
                                char.name }}</h3>
                        <p class="text-sm text-fantasy-muted capitalize">{{ char.race }} - {{ char.culture }}</p>
                    </div>
                    <div class="flex flex-col items-end gap-2">
                        <span class="px-2 py-1 rounded bg-fantasy-dark text-xs text-fantasy-gold border border-gray-700">
                            Niv. {{ char.level }}
                        </span>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase border"
                            :class="{
                                'bg-gray-700/50 text-gray-400 border-gray-600': char.status === 'draft',
                                'bg-green-900/40 text-green-400 border-green-800/50': char.status === 'active',
                                'bg-blue-900/40 text-blue-400 border-blue-800/50': char.status === 'in_game'
                            }">
                            {{ t(`character_status.${char.status}`) }}
                        </span>
                    </div>
                </div>

                <div class="space-y-2 mb-6">
                    <div class="flex justify-between text-sm">
                        <span class="text-fantasy-muted">Classe d'Armure</span>
                        <span class="text-fantasy-text font-bold">{{ char.combat_stats.armor_class }}</span>
                    </div>
                    <div class="flex justify-between text-sm">
                        <span class="text-fantasy-muted">PV</span>
                        <span class="text-fantasy-text font-bold">{{ char.combat_stats.current_hit_points }} / {{
                            char.combat_stats.max_hit_points }}</span>
                    </div>
                </div>

                <div class="pt-4 border-t border-gray-700 flex justify-end gap-2">
                    <button @click="viewCharacter(char.id)"
                        class="p-2 text-fantasy-muted hover:text-fantasy-text hover:bg-fantasy-hover rounded transition-colors cursor-pointer"
                        title="Voir la fiche">
                        <Eye :size="20" />
                    </button>

                    <button @click="editCharacter(char.id)" :disabled="char.status === 'in_game'"
                        :class="char.status === 'in_game' ? 'opacity-50 cursor-not-allowed' : 'hover:text-fantasy-text hover:bg-fantasy-hover'"
                        class="p-2 text-fantasy-muted rounded transition-colors"
                        :title="char.status === 'in_game' ? 'Impossible d\'éditer en aventure' : 'Éditer'">
                        <Edit :size="20" />
                    </button>
                    <button @click="openDeleteModal(char.id)"
                        class="p-2 text-fantasy-muted hover:text-red-500 hover:bg-fantasy-hover rounded transition-colors cursor-pointer"
                        title="Supprimer">
                        <Trash2 :size="20" />
                    </button>
                </div>
            </div>
        </div>

        <ConfirmationModal :show="showDeleteModal" title="Supprimer le personnage ?"
            message="Êtes-vous sûr de vouloir supprimer ce personnage ? Cette action est irréversible."
            confirm-text="Supprimer" :loading="deleteLoading" @close="showDeleteModal = false"
            @confirm="confirmDelete" />
    </div>
</template>
