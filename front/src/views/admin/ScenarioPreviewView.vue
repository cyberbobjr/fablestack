<template>
    <div class="container mx-auto px-4 py-8">
        <div class="mb-4 flex items-center justify-between">
            <button @click="router.push({ name: 'admin', query: { tab: 'scenarios' } })"
                class="flex items-center text-gray-400 hover:text-white transition-colors mb-2">
                <ArrowLeft :size="20" class="mr-2" />
                {{ t('back') }}
            </button>
            <h1 class="text-3xl font-bold text-fantasy-gold">{{ scenario?.title || filename }}</h1>
            <router-link :to="{ name: 'admin-scenario-edit', params: { filename: filename } }"
                class="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded shadow flex items-center transition-colors">
                <Edit :size="20" class="mr-2" />
                {{ t('admin.edit') }}
            </router-link>
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

        <div v-else class="bg-gray-900 p-8 rounded-lg shadow-xl border border-gray-700">
            <!-- Markdown Content -->
            <div class="prose prose-invert prose-lg max-w-none prose-img:rounded-lg prose-img:shadow-md prose-headings:text-fantasy-gold"
                v-html="parsedContent"></div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { getApiBaseUrl } from '@/config'
import api from '@/services/api'
import { useScenarioStore } from '@/stores/scenario'
import { AlertCircle, ArrowLeft, Edit } from 'lucide-vue-next'
import { marked } from 'marked'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'


const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const scenarioStore = useScenarioStore()

const filename = route.params.filename as string
const rawContent = ref('')
const loading = ref(true)
const error = ref<string | null>(null)
const scenario = ref<any>(null)

const parsedContent = computed(() => {
    // Basic renderer needed? marked v4+ extension is better, but renderer override works for simple cases.
    const renderer = new marked.Renderer()
    const originalImage = renderer.image.bind(renderer)

    renderer.image = ({ href, title, text }: any) => {
        if (href && href.startsWith('/static')) {
            // Prepend API Base URL
            href = `${getApiBaseUrl()}${href}`
        }
        return originalImage({ href, title, text } as any)
    }

    return marked(rawContent.value, { renderer })
})

onMounted(async () => {
    loading.value = true
    try {
        if (scenarioStore.scenarios.length === 0) {
            await scenarioStore.fetchScenarios()
        }
        scenario.value = scenarioStore.scenarios.find(s => s.name === filename)

        const res = await api.getScenario(filename)
        rawContent.value = res.data
    } catch (e: any) {
        error.value = e.message || 'Error loading scenario'
    } finally {
        loading.value = false
    }
})
</script>
