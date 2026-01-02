<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUiFontSizes } from '../../composables/useUiFontSizes'
import { getApiBaseUrl } from '../../config'
import type { Character } from '../../services/api'
import { useGameDataStore } from '../../stores/gameData'
import CharacterAttributes from './CharacterAttributes.vue'
import CharacterEquipment from './CharacterEquipment.vue'
import CharacterSkills from './CharacterSkills.vue'

defineProps<{
    character: Character
}>()

const { t } = useI18n()
const gameDataStore = useGameDataStore()
const { uiFontSizes } = useUiFontSizes()
const activeTab = ref('general')

const getPortraitUrl = (url: string): string => {
    if (!url) return ''
    if (url.startsWith('http')) return url
    return `${getApiBaseUrl()}${url}`
}
</script>

<template>
    <div
        class="w-96 bg-fantasy-secondary rounded-lg border border-gray-800 p-0 overflow-hidden shadow-2xl flex flex-col">
        <!-- Header -->
        <div class="p-6 bg-fantasy-header border-b border-gray-700 text-center relative overflow-hidden">
            <div class="absolute inset-0 bg-gradient-to-b from-fantasy-gold/5 to-transparent pointer-events-none"></div>

            <!-- Portrait -->
            <div class="relative inline-block mb-4 group">
                <div
                    class="absolute -inset-0.5 bg-gradient-to-r from-fantasy-gold to-fantasy-accent rounded-full opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200 animate-tilt">
                </div>
                <div class="relative">
                    <img v-if="character.portrait_url" :src="getPortraitUrl(character.portrait_url)"
                        :alt="character.name"
                        class="w-32 h-32 rounded-full border-4 border-fantasy-gold shadow-lg object-cover mx-auto bg-gray-900" />
                    <div v-else
                        class="w-32 h-32 rounded-full border-4 border-fantasy-muted bg-gray-800 flex items-center justify-center mx-auto shadow-lg text-4xl select-none">
                        👤
                    </div>
                </div>
            </div>

            <h2 class="text-2xl font-serif font-bold text-fantasy-gold tracking-wide">{{ character.name }}</h2>
            <p class="text-fantasy-muted mt-1 uppercase tracking-widest" :class="uiFontSizes.xs">{{
                gameDataStore.translate(character.race,
                    'races') }} • {{ gameDataStore.translate(character.culture, 'cultures') }}</p>
            <div
                class="mt-4 inline-flex items-center gap-2 bg-fantasy-dark px-3 py-1 rounded-full border border-fantasy-gold/20 shadow-inner">
                <span class="text-fantasy-muted font-bold" :class="uiFontSizes.xs">LEVEL {{ character.level }}</span>
            </div>
        </div>

        <!-- Tabs -->
        <div class="flex border-b border-gray-700 bg-fantasy-header/50">
            <button v-for="tab in ['general', 'skills', 'equipment']" :key="tab" @click="activeTab = tab"
                class="flex-1 py-3 text-sm font-medium transition-colors border-b-2"
                :class="[activeTab === tab ? 'border-fantasy-gold text-fantasy-gold bg-fantasy-gold/5' : 'border-transparent text-fantasy-muted hover:text-fantasy-text hover:bg-white/5', uiFontSizes.sm]">
                {{ t(`ui.${tab}`) }}
            </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin">
            <div v-if="activeTab === 'general'">
                <CharacterAttributes :character="character" />
            </div>
            <div v-if="activeTab === 'skills'">
                <CharacterSkills :character="character" />
            </div>
            <div v-if="activeTab === 'equipment'">
                <CharacterEquipment :character="character" />
            </div>
        </div>
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
</style>
