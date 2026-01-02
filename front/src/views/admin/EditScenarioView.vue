<template>
    <div class="container mx-auto px-4 py-8">
        <div class="mb-4 flex items-center justify-between">
            <div>
                <button @click="router.push({ name: 'admin', query: { tab: 'scenarios' } })"
                    class="flex items-center text-gray-400 hover:text-white transition-colors mb-2">
                    <ArrowLeft :size="20" class="mr-2" />
                    {{ t('back') }}
                </button>
                <h1 v-if="scenario" class="text-3xl font-bold text-fantasy-gold">{{ t('admin.edit_scenario') }}: {{
                    scenario.title }}</h1>
                <h1 v-else class="text-3xl font-bold text-fantasy-gold">{{ t('admin.edit_scenario') }}</h1>
            </div>
            <button @click="save" :disabled="saving"
                class="bg-fantasy-accent hover:bg-purple-600 text-white font-bold py-2 px-6 rounded shadow-lg flex items-center transition-colors disabled:opacity-50">
                <Save v-if="!saving" :size="20" class="mr-2" />
                <svg v-else class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg"
                    fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                    </path>
                </svg>
                {{ saving ? t('saved') : t('save') }}
            </button>
        </div>

        <div v-if="loading" class="flex justify-center p-12">
            <svg class="animate-spin h-10 w-10 text-fantasy-accent" xmlns="http://www.w3.org/2000/svg" fill="none"
                viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                </path>
            </svg>
        </div>

        <div v-else-if="error"
            class="bg-red-900/20 border border-red-500/50 text-red-200 p-4 rounded flex items-center">
            <AlertCircle :size="24" class="mr-3" />
            {{ error }}
        </div>

        <div v-else
            class="bg-gray-900 rounded-lg shadow-xl overflow-hidden border border-gray-700 h-[calc(100vh-200px)] flex flex-col">
            <div
                class="bg-gray-800 px-4 py-2 border-b border-gray-700 flex justify-between items-center text-sm text-gray-400">
                <span>{{ filename }}</span>
                <span class="italic">{{ t('admin.markdown_editor') }}</span>
            </div>
            <textarea v-model="content"
                class="flex-grow w-full bg-gray-950 text-gray-200 p-4 font-mono text-sm focus:outline-none resize-none"
                spellcheck="false"></textarea>
        </div>
    </div>
</template>

<script setup lang="ts">
import api from '@/services/api'; // Direct API usage to fetch content, or add fetchContent to store
import { useScenarioStore } from '@/stores/scenario';
import { AlertCircle, ArrowLeft, Save } from 'lucide-vue-next';
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const scenarioStore = useScenarioStore()

const filename = route.params.filename as string
const content = ref('')
const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const scenario = ref<any>(null)

onMounted(async () => {
    loading.value = true
    try {
        // Fetch raw content
        // using axios directly for raw content, or add method to api service to get raw text
        // api.getScenarioContent(filename) -> but we only have getScenarios (list)
        // We need a way to get content. 
        // The router has GET /api/scenarios/{filename} which returns the content string.
        // Let's use axios directly here or extend api service. use api.get(`/scenarios/${filename}`)

        // Wait, api.ts has getScenarios but not getScenario(filename).
        // I should probably add getScenario to api.ts properly, but I can use axios for now or fix api.ts.
        // Let's use fetch from api.ts if I added it? No I added delete/update/create.
        // I will use `api` instance from services/api to call get.

        // Also fetch metadata to show title? We can find it in store.
        if (scenarioStore.scenarios.length === 0) {
            await scenarioStore.fetchScenarios()
        }
        scenario.value = scenarioStore.scenarios.find(s => s.name === filename)

        // Fetch Content
        // We can use the axios instance exported or just fetch.
        // api is exported as default object, but inside api.ts 'api' var is not exported.
        // I'll resort to importing axios or using a custom call if unavoidable, 
        // OR better: add getScenario to API service.
        // For now, I'll assumme I can access it via a dirty hack or just add it to api.ts quickly.
        // Actually I can just add `api.getScenario(filename)` to `api.ts` in next step or now.
        // Let's assume I will add it.
        const res = await api.getScenario(filename) // returns content string
        content.value = res.data
    } catch (e: any) {
        error.value = e.message || 'Error loading scenario'
    } finally {
        loading.value = false
    }
})

const save = async () => {
    saving.value = true
    try {
        await scenarioStore.updateScenario(filename, content.value)
        // Success notification?
    } catch (e: any) {
        alert(e.message || 'Error saving')
    } finally {
        saving.value = false
    }
}
</script>
