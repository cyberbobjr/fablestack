<script setup lang="ts">
import { ChevronLeft, Heart, RefreshCw, Scroll, Shield, Sword, X, Zap } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Tooltip from '../components/ui/Tooltip.vue'
import { useCharacterBonuses } from '../composables/useCharacterBonuses'
import api, { type Character } from '../services/api'
import { getApiBaseUrl } from '../config'

import { useGameDataStore } from '../stores/gameData'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const gameDataStore = useGameDataStore()
const loading = ref(true)
const character = ref<Character | null>(null)
const activeTab = ref('general')
const isRegenerating = ref(false)
const showPortraitModal = ref(false)
const showErrorModal = ref(false)
const errorMessage = ref('')
const sexBonuses = ref<Record<string, any>>({})

const handleRegeneratePortrait = async () => {
    if (!character.value || isRegenerating.value) return

    isRegenerating.value = true
    try {
        const response = await api.regeneratePortrait(character.value.id)
        // Force update image by appending timestamp to URL (if needed) or just update reference
        // Assuming backend returns full URL with /static/
        // To bypass cache issues, we can append a random query param
        let newUrl = response.data.character.portrait_url
        if (newUrl) {
            newUrl += `?t=${Date.now()}`
            character.value.portrait_url = newUrl
        }
    } catch (error: any) {
        console.error('Error regenerating portrait:', error)
        if (error.response && error.response.status === 429) {
            errorMessage.value = error.response.data.detail
            showErrorModal.value = true
        }
    } finally {
        isRegenerating.value = false
    }
}

const loadCharacter = async () => {
    const id = route.params.id as string
    if (!id) return

    try {
        const response = await api.getCharacter(id)
        character.value = response.data.character
    } catch (error) {
        console.error('Error loading character:', error)
    }
}

onMounted(async () => {
    loading.value = true
    try {
        await Promise.all([
            loadCharacter(),
            gameDataStore.fetchAllData(),
            api.getSexBonuses().then(res => sexBonuses.value = res.data).catch(e => console.error('Error fetching sex bonuses:', e))
        ])
    } finally {
        loading.value = false
    }
})

const tabs = [
    { id: 'general', label: 'Général' },
    { id: 'skills', label: 'Compétences' },
    { id: 'equipment', label: 'Équipement' }
]

const translatedSex = computed(() => {
    if (!character.value) return ''
    return t(`ui.${character.value.sex}`)
})

const apiBaseUrl = getApiBaseUrl()

// Helper to translate race/culture
// Helper to translate race/culture
const translatedRace = computed(() => {
    if (!character.value) return ''
    return gameDataStore.translate(character.value.race, 'races') || character.value.race
})

const translatedCulture = computed(() => {
    if (!character.value) return ''
    return gameDataStore.translate(character.value.culture, 'cultures') || character.value.culture
})

// Helper for stats translation
const getStatLabel = (statName: string) => {
    return gameDataStore.translate(statName, 'stats')
}

// --- Bonus Helpers (Composable) ---

// Create reactive refs mapping from character data
const raceId = computed(() => character.value?.race)
const cultureId = computed(() => character.value?.culture)
const characterSex = computed(() => character.value?.sex)
const stats = computed(() => character.value?.stats || {})

const {
    getRaceStatBonus,
    getCultureStatBonus,
    getSexStatBonus,
    getRaceSkillBonus,
    getCultureSkillBonus,
    getSexSkillBonus,
    getStatBonusForSkill
} = useCharacterBonuses(raceId, cultureId, characterSex, stats, sexBonuses)

</script>

<template>
    <div class="max-w-7xl mx-auto space-y-8">
        <div class="flex items-center gap-4">
            <router-link to="/characters" class="text-gray-400 hover:text-white">
                <ChevronLeft :size="24" />
            </router-link>
            <h1 class="text-3xl font-sans font-bold text-fantasy-gold">Fiche de Personnage</h1>
        </div>

        <div v-if="loading" class="text-center py-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-fantasy-gold mx-auto"></div>
        </div>

        <div v-else-if="character" class="bg-fantasy-secondary rounded-lg border border-gray-700 overflow-hidden">
            <!-- Header -->
            <div class="p-6 border-b border-gray-700 bg-fantasy-dark/50">
                <div class="flex flex-col md:flex-row gap-6 items-start">
                    <!-- Portrait -->
                    <div class="relative group shrink-0">
                        <div @click="character.portrait_url ? showPortraitModal = true : null"
                            class="w-32 h-32 rounded-lg border-2 border-fantasy-gold/30 overflow-hidden bg-black/40 flex items-center justify-center cursor-pointer hover:border-fantasy-gold transition-colors relative">
                            <img v-if="character.portrait_url" :src="`${apiBaseUrl}${character.portrait_url}`"
                                alt="Character Portrait" class="w-full h-full object-cover" />
                            <div v-else class="text-fantasy-muted text-xs text-center px-2">No Portrait</div>

                            <!-- Search icon overlay on hover -->
                            <div v-if="character.portrait_url"
                                class="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                <span class="text-white text-xs font-bold">Agrandir</span>
                            </div>
                        </div>
                        <button @click="handleRegeneratePortrait" :disabled="isRegenerating"
                            class="absolute bottom-1 right-1 p-1.5 rounded-full bg-black/70 text-fantasy-gold hover:text-white hover:bg-fantasy-accent transition-colors border border-fantasy-gold/50"
                            title="Regenerate Portrait">
                            <RefreshCw :size="14" :class="{ 'animate-spin': isRegenerating }" />
                        </button>
                    </div>

                    <div class="flex-grow w-full">
                        <div class="flex justify-between items-start">
                            <div>
                                <h2 class="text-2xl font-bold text-fantasy-text">{{ character.name }}</h2>
                                <p class="text-fantasy-muted">{{ translatedSex }} - {{ translatedRace }} - {{
                                    translatedCulture }}
                                </p>
                            </div>
                            <div class="px-3 py-1 rounded bg-fantasy-accent text-white font-bold">
                                Niveau {{ character.level }}
                            </div>
                        </div>

                        <!-- Description preview or other header info -->
                        <div class="mt-2 text-sm text-fantasy-text/80 line-clamp-2"
                            v-if="character.physical_description_localized || character.physical_description">
                            {{ character.physical_description_localized || character.physical_description }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="flex border-b border-gray-700">
                <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
                    class="flex-1 py-3 text-sm font-medium transition-colors cursor-pointer"
                    :class="activeTab === tab.id ? 'bg-fantasy-secondary text-fantasy-accent border-b-2 border-fantasy-accent' : 'bg-fantasy-dark text-fantasy-muted hover:text-fantasy-text'">
                    {{ tab.label }}
                </button>
            </div>

            <!-- Content -->
            <div class="p-6 min-h-[400px]">
                <!-- General Tab -->
                <div v-if="activeTab === 'general'" class="space-y-6">
                    <!-- Vitals -->
                    <div class="grid grid-cols-3 gap-4">
                        <div class="bg-fantasy-dark p-3 rounded border border-gray-700 flex flex-col items-center">
                            <Heart class="text-red-500 mb-1" :size="20" />
                            <span class="text-xs text-fantasy-muted">PV</span>
                            <span class="font-bold text-fantasy-text">{{ character.combat_stats.current_hit_points }} /
                                {{
                                    character.combat_stats.max_hit_points }}</span>
                        </div>
                        <div class="bg-fantasy-dark p-3 rounded border border-gray-700 flex flex-col items-center">
                            <Zap class="text-blue-400 mb-1" :size="20" />
                            <span class="text-xs text-fantasy-muted">PM</span>
                            <span class="font-bold text-fantasy-text">{{ character.combat_stats.current_mana_points }} /
                                {{
                                    character.combat_stats.max_mana_points }}</span>
                        </div>
                        <div class="bg-fantasy-dark p-3 rounded border border-gray-700 flex flex-col items-center">
                            <Shield class="text-gray-400 mb-1" :size="20" />
                            <span class="text-xs text-fantasy-muted">CA</span>
                            <span class="font-bold text-fantasy-text">{{ character.combat_stats.armor_class }}</span>
                        </div>
                    </div>

                    <!-- Attributes -->
                    <div>
                        <h3 class="text-lg font-bold text-fantasy-gold mb-3">Attributs</h3>
                        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                            <div v-for="(value, key) in character.stats" :key="key"
                                class="flex flex-col bg-fantasy-dark p-2 rounded border border-gray-700">
                                <div class="flex justify-between items-center mb-1">
                                    <span class="text-sm text-fantasy-muted">{{ getStatLabel(key as string) }}</span>
                                    <span class="font-bold text-fantasy-text">{{ value }}</span>
                                </div>
                                <div class="flex flex-wrap gap-1 text-[10px]">
                                    <span v-if="getRaceStatBonus(String(key)) > 0" class="text-fantasy-gold">+{{
                                        getRaceStatBonus(String(key)) }} (Race)</span>
                                    <span v-if="getCultureStatBonus(String(key)) > 0" class="text-fantasy-gold">+{{
                                        getCultureStatBonus(String(key)) }} (Cult.)</span>
                                    <span v-if="getSexStatBonus(String(key)) > 0" class="text-blue-300">+{{
                                        getSexStatBonus(String(key)) }} (Sexe)</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Description -->
                    <div v-if="character.physical_description || character.description">
                        <h3 class="text-lg font-bold text-fantasy-gold mb-3">Description</h3>
                        <div class="space-y-4 text-fantasy-text text-sm">
                            <p v-if="character.physical_description || character.physical_description_localized">
                                <strong class="text-fantasy-muted">Physique :</strong> {{
                                    character.physical_description_localized || character.physical_description }}
                            </p>
                            <p v-if="character.description || character.description_localized">
                                <strong class="text-fantasy-muted">Histoire :</strong> {{
                                    character.description_localized || character.description }}
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Skills Tab -->
                <div v-if="activeTab === 'skills'" class="space-y-6">
                    <div v-for="(categorySkills, category) in character.skills" :key="category">
                        <h3 class="text-lg font-bold text-fantasy-gold mb-3 capitalize">{{
                            gameDataStore.translate(category as string) }}</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                            <div v-for="(value, skill) in categorySkills" :key="skill"
                                class="flex flex-col bg-fantasy-dark p-2 rounded border border-gray-700">
                                <div class="flex justify-between items-center">
                                    <Tooltip :text="gameDataStore.translate(String(skill), 'skill_descriptions')">
                                        <span
                                            class="text-sm text-fantasy-text underline decoration-dashed underline-offset-4 decoration-fantasy-muted/50 cursor-help">{{
                                                gameDataStore.translate(skill as string)
                                            }}</span>
                                    </Tooltip>
                                    <span class="font-bold text-fantasy-accent">{{ value }}</span>
                                </div>
                                <div class="flex flex-wrap gap-2 text-[10px] mt-1">
                                    <span v-if="getRaceSkillBonus(String(skill)) > 0" class="text-fantasy-gold">+{{
                                        getRaceSkillBonus(String(skill)) }} (Race)</span>
                                    <span v-if="getCultureSkillBonus(String(skill)) > 0" class="text-fantasy-gold">+{{
                                        getCultureSkillBonus(String(skill)) }} (Cult.)</span>
                                    <span v-if="getSexSkillBonus(String(skill)) > 0" class="text-blue-300">+{{
                                        getSexSkillBonus(String(skill)) }} (Sexe)</span>
                                    <span v-if="getStatBonusForSkill(String(skill)) > 0" class="text-green-300">+{{
                                        getStatBonusForSkill(String(skill)) }} (Stat)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Equipment Tab -->
                <div v-if="activeTab === 'equipment'" class="space-y-6">
                    <!-- Currency -->
                    <div class="flex gap-4 mb-6">
                        <div class="flex items-center gap-2 bg-fantasy-dark px-3 py-1 rounded border border-gray-700">
                            <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
                            <span class="font-bold text-fantasy-gold">{{ character.equipment.gold || 0 }} PO</span>
                        </div>
                        <div class="flex items-center gap-2 bg-fantasy-dark px-3 py-1 rounded border border-gray-700">
                            <div class="w-3 h-3 rounded-full bg-gray-400"></div>
                            <span class="font-bold text-fantasy-silver">{{ character.equipment.silver || 0 }} PA</span>
                        </div>
                        <div class="flex items-center gap-2 bg-fantasy-dark px-3 py-1 rounded border border-gray-700">
                            <div class="w-3 h-3 rounded-full bg-orange-700"></div>
                            <span class="font-bold text-orange-700">{{ character.equipment.copper || 0 }} PC</span>
                        </div>
                    </div>

                    <!-- Weapons -->
                    <div v-if="character.equipment.weapons?.length">
                        <h3 class="text-lg font-bold text-fantasy-gold mb-3 flex items-center gap-2">
                            <Sword :size="18" /> Armes
                        </h3>
                        <div class="space-y-2">
                            <div v-for="item in character.equipment.weapons" :key="item.id"
                                class="bg-fantasy-dark p-3 rounded border border-gray-700">
                                <div class="flex justify-between">
                                    <span class="font-bold text-fantasy-text">{{ gameDataStore.translate(item.item_id,
                                        'equipment') }}</span>
                                    <span class="text-xs text-fantasy-muted">Dégâts: {{ item.damage }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Armor -->
                    <div v-if="character.equipment.armor?.length">
                        <h3 class="text-lg font-bold text-fantasy-gold mb-3 flex items-center gap-2">
                            <Shield :size="18" /> Armure
                        </h3>
                        <div class="space-y-2">
                            <div v-for="item in character.equipment.armor" :key="item.id"
                                class="bg-fantasy-dark p-3 rounded border border-gray-700">
                                <div class="flex justify-between">
                                    <span class="font-bold text-fantasy-text">{{ gameDataStore.translate(item.item_id,
                                        'equipment') }}</span>
                                    <span class="text-xs text-fantasy-muted">CA: +{{ item.defense }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Inventory -->
                    <div v-if="character.equipment.inventory?.length">
                        <h3 class="text-lg font-bold text-fantasy-gold mb-3 flex items-center gap-2">
                            <Scroll :size="18" /> Inventaire
                        </h3>
                        <div class="space-y-2">
                            <div v-for="item in character.equipment.inventory" :key="item.id"
                                class="bg-fantasy-dark p-3 rounded border border-gray-700 flex justify-between items-center">
                                <span class="text-fantasy-text">{{ gameDataStore.translate(item.item_id, 'equipment')
                                    }}</span>
                                <span class="text-xs bg-gray-700 px-2 py-1 rounded text-gray-300">x{{ item.quantity
                                }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Portrait Modal -->
    <div v-if="showPortraitModal && character?.portrait_url"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4" @click="showPortraitModal = false">

        <button @click="showPortraitModal = false"
            class="absolute top-4 right-4 text-white hover:text-fantasy-gold transition-colors bg-black/50 rounded-full p-2">
            <X :size="32" />
        </button>

        <img :src="`${apiBaseUrl}${character.portrait_url}`" alt="Character Portrait Full Size"
            class="max-w-full max-h-[90vh] object-contain rounded-lg border-2 border-fantasy-gold/50 shadow-2xl shadow-fantasy-gold/20"
            @click.stop />
    </div>

    <!-- Error Modal -->
    <div v-if="showErrorModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
        @click="showErrorModal = false">
        <div class="bg-fantasy-secondary border border-gray-700 rounded-lg p-6 max-w-md w-full shadow-xl relative"
            @click.stop>
            <button @click="showErrorModal = false"
                class="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors">
                <X :size="20" />
            </button>
            <h3 class="text-xl font-bold text-red-500 mb-4">{{ t('error.limitReachedTitle') }}</h3>
            <p class="text-fantasy-text mb-6">{{ errorMessage }}</p>
            <div class="flex justify-end">
                <button @click="showErrorModal = false"
                    class="bg-fantasy-accent hover:bg-red-600 text-white px-4 py-2 rounded transition-colors">
                    {{ t('common.close') }}
                </button>
            </div>
        </div>
    </div>
</template>
