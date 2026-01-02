<template>
    <div class="container mx-auto px-4 py-8">
        <div class="mb-8 flex justify-between items-center">
            <h1 class="text-3xl font-bold text-fantasy-gold">{{ t('admin.scenarios_management') }}</h1>
            <button @click="showCreateModal = true"
                class="bg-fantasy-accent hover:bg-purple-600 text-white font-bold py-2 px-4 rounded flex items-center shadow-lg transition-transform transform hover:scale-105">
                <Plus :size="20" class="mr-2" />
                {{ t('admin.create_scenario') }}
            </button>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="flex justify-center p-12">
            <svg class="animate-spin h-10 w-10 text-fantasy-accent" xmlns="http://www.w3.org/2000/svg" fill="none"
                viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                </path>
            </svg>
        </div>

        <!-- Scenario List -->
        <div v-else class="bg-fantasy-secondary border border-gray-700 rounded-lg overflow-hidden shadow-xl">
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead
                        class="bg-gray-900/50 text-fantasy-gold uppercase text-sm font-bold border-b border-gray-700">
                        <tr>
                            <th class="px-6 py-4">{{ t('admin.scenario_title') }}</th>
                            <th class="px-6 py-4">{{ t('admin.filename') }}</th>
                            <th class="px-6 py-4">{{ t('admin.status') }}</th>
                            <th class="px-6 py-4">{{ t('admin.played') }}</th>
                            <th class="px-6 py-4 text-right">{{ t('admin.actions') }}</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-700">
                        <tr v-for="scenario in scenarios" :key="scenario.id"
                            class="hover:bg-gray-800/30 transition-colors">
                            <td class="px-6 py-4 font-medium text-white">{{ scenario.title }}</td>
                            <td class="px-6 py-4 text-gray-400 font-mono text-sm">{{ scenario.name }}</td>

                            <td class="px-6 py-4">
                                <span v-if="scenario.status === 'creating'"
                                    class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-900/30 text-blue-400 border border-blue-900 animate-pulse">
                                    {{ t('admin.creating') }}...
                                </span>
                                <span v-else
                                    class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-900/30 text-green-400 border border-green-900">
                                    {{ scenario.status }}
                                </span>
                            </td>
                            <td class="px-6 py-4">
                                <span v-if="scenario.is_played" class="inline-flex items-center text-green-400"
                                    :title="t('admin.currently_played')">
                                    <PlayCircle :size="18" class="mr-1" />
                                    {{ t('yes') }}
                                </span>
                                <span v-else class="text-gray-500">{{ t('no') }}</span>
                            </td>
                            <td class="px-6 py-4 text-right flex justify-end space-x-2">
                                <router-link v-if="scenario.status !== 'creating'"
                                    :to="{ name: 'admin-scenario-edit', params: { filename: scenario.name } }"
                                    class="text-blue-400 hover:text-blue-300 transition-colors mr-2"
                                    :title="t('admin.edit')">
                                    <Edit :size="18" />
                                </router-link>
                                <span v-else class="text-gray-600 mr-2 cursor-not-allowed">
                                    <Edit :size="18" />
                                </span>

                                <router-link v-if="scenario.status !== 'creating'"
                                    :to="{ name: 'admin-scenario-preview', params: { filename: scenario.name } }"
                                    class="text-green-400 hover:text-green-300 transition-colors mr-2"
                                    :title="t('admin.preview')">
                                    <Eye :size="18" />
                                </router-link>
                                <span v-else class="text-gray-600 mr-2 cursor-not-allowed">
                                    <Eye :size="18" />
                                </span>

                                <button @click="confirmDelete(scenario)"
                                    class="text-red-500 hover:text-red-400 transition-colors"
                                    :title="t('admin.delete')">
                                    <Trash2 :size="18" />
                                </button>
                            </td>
                        </tr>
                        <tr v-if="!scenarios || scenarios.length === 0">
                            <td colspan="5" class="px-6 py-8 text-center text-gray-500 italic">
                                {{ t('admin.no_scenarios') }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Create Modal -->
        <div v-if="showCreateModal"
            class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div
                class="bg-gray-900 border border-fantasy-gold rounded-lg shadow-2xl max-w-lg w-full overflow-hidden animate-fade-in-up">
                <div class="bg-gray-800 px-6 py-4 border-b border-gray-700 flex justify-between items-center">
                    <h3 class="text-xl font-bold text-fantasy-gold">{{ t('admin.create_new_scenario') }}</h3>
                    <button @click="showCreateModal = false" class="text-gray-400 hover:text-white transition-colors">
                        <X :size="24" />
                    </button>
                </div>

                <div class="p-6 space-y-4">
                    <!-- Title Input -->


                    <!-- Description Input -->
                    <div>
                        <label class="block text-gray-300 mb-1 text-sm font-bold">{{ t('admin.scenario_description')
                        }}</label>
                        <textarea v-model="newScenario.description" rows="5"
                            class="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white focus:border-fantasy-accent focus:outline-none"
                            :placeholder="t('admin.enter_description_ai')"></textarea>
                        <p class="text-xs text-fantasy-gold mt-1 italic flex items-center">
                            <Sparkles :size="12" class="mr-1" />
                            {{ t('admin.ai_generation_hint') }}
                        </p>
                    </div>

                    <!-- Error Message -->
                    <div v-if="error"
                        class="bg-red-900/20 border border-red-500/50 text-red-200 p-3 rounded text-sm flex items-start">
                        <AlertCircle :size="16" class="mt-0.5 mr-2 flex-shrink-0" />
                        <span>{{ error }}</span>
                    </div>
                </div>

                <div class="bg-gray-800 px-6 py-4 border-t border-gray-700 flex justify-end space-x-3">
                    <button @click="showCreateModal = false"
                        class="px-4 py-2 text-gray-300 hover:text-white transition-colors">
                        {{ t('cancel') }}
                    </button>
                    <button @click="handleCreate" :disabled="creating"
                        class="bg-fantasy-accent hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2 px-6 rounded shadow-lg flex items-center transition-colors">
                        <span v-if="creating" class="flex items-center">
                            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg"
                                fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                    stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                                </path>
                            </svg>
                            {{ t('admin.generating') }}
                        </span>
                        <span v-else class="flex items-center">
                            <Sparkles :size="16" class="mr-2" />
                            {{ t('admin.generate_create') }}
                        </span>
                    </button>
                </div>
            </div>
        </div>

        <!-- Delete Confirmation -->
        <ConfirmationModal :show="showDeleteModal" :title="t('admin.delete_scenario')"
            :message="t('admin.delete_scenario_confirm')" @confirm="handleDelete" @close="showDeleteModal = false" />


    </div>
</template>

<script setup lang="ts">
import ConfirmationModal from '@/components/ConfirmationModal.vue'
import { useScenarioStore } from '@/stores/scenario'
import { AlertCircle, Edit, Eye, PlayCircle, Plus, Sparkles, Trash2, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const scenarioStore = useScenarioStore()

const scenarios = computed(() => scenarioStore.scenarios)
const loading = computed(() => scenarioStore.loading)
const error = ref<string | null>(null)

const showCreateModal = ref(false)
const generating = ref(false) // Local generating state or use store loading
const creating = computed(() => scenarioStore.loading && showCreateModal.value)

interface ScenarioCreationPayload {
    description: string
}

const newScenario = ref<ScenarioCreationPayload>({
    description: ''
})

const showDeleteModal = ref(false)
const scenarioToDelete = ref<any>(null)



// Methods
const loadScenarios = () => {
    scenarioStore.fetchScenarios()
}

const handleCreate = async () => {
    if (!newScenario.value.description) {
        error.value = t('admin.fill_all_fields')
        return
    }

    error.value = null
    try {
        await scenarioStore.createScenario(newScenario.value.description)
        showCreateModal.value = false
        newScenario.value = { description: '' }
    } catch (e: any) {
        error.value = e.response?.data?.detail || e.message || 'Error creating scenario'
    }
}

const confirmDelete = (scenario: any) => {
    scenarioToDelete.value = scenario
    showDeleteModal.value = true
}

const handleDelete = async () => {
    if (!scenarioToDelete.value) return

    try {
        await scenarioStore.deleteScenario(scenarioToDelete.value.name)
        showDeleteModal.value = false
        scenarioToDelete.value = null
    } catch (e: any) {
        console.error(e)
    }
}



onMounted(() => {
    loadScenarios()
})
</script>
