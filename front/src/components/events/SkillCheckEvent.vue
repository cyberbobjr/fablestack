<script setup lang="ts">
import { RotateCcw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useUiFontSizes } from '../../composables/useUiFontSizes'
import type { TimelineEvent } from '../../services/api'
import { useGameDataStore } from '../../stores/gameData'

defineProps<{
    event: TimelineEvent
    isDebugMode: boolean
}>()

defineEmits<{
    (e: 'restore', timestamp: string): void
}>()

const { t } = useI18n()
const gameDataStore = useGameDataStore()
const { uiFontSizes } = useUiFontSizes()

const getSkillTranslation = (name: string): string => {
    if (!name) return ''
    return gameDataStore.translate(name)
}

const getDegreeTranslation = (degree: string): string => {
    if (!degree) return ''
    const key: string = degree.toLowerCase().replace(/ /g, '_')
    return t(`results.${key}`)
}
</script>

<template>
    <div class="w-full my-4 animate-fade-in-up">
        <div class="bg-fantasy-secondary border rounded-lg p-3 flex items-center gap-4 shadow-lg w-full"
            :class="event.metadata?.success ? 'border-green-500/30' : 'border-red-500/30'">
            <div class="text-3xl filter drop-shadow-md">{{ event.icon }}</div>
            <div class="flex-1">
                <div class="flex justify-between items-center mb-1">
                    <div class="font-bold uppercase tracking-wider"
                        :class="[event.metadata?.success ? 'text-green-500' : 'text-red-500', uiFontSizes.xs]">
                        {{ getSkillTranslation(event.metadata?.skill_name) || 'Skill Check' }}
                    </div>
                    <div class="text-fantasy-muted uppercase tracking-widest" :class="uiFontSizes.xs">
                        {{ getDegreeTranslation(event.metadata?.degree) }}
                    </div>
                </div>

                <div v-if="event.metadata" class="grid grid-cols-2 gap-x-4 gap-y-1 mt-1" :class="uiFontSizes.sm">
                    <div class="text-fantasy-muted">{{ t('results.roll') }}: <span
                            class="font-mono font-bold text-fantasy-text">{{
                                event.metadata.roll }}</span></div>
                    <div class="text-fantasy-muted text-right">{{ t('results.target') }}: <span
                            class="font-mono text-fantasy-text">{{ event.metadata.target }}</span></div>
                </div>
                <div v-else class="text-fantasy-text font-medium" :class="uiFontSizes.sm">{{ event.content }}</div>
            </div>
            <div v-if="isDebugMode" class="flex flex-col justify-center px-2">
                <button @click="$emit('restore', event.timestamp)"
                    class="text-gray-500 hover:text-red-400 p-2 rounded-full hover:bg-white/5 transition-colors"
                    title="Restore to this point">
                    <RotateCcw :size="16" />
                </button>
            </div>
        </div>
    </div>
</template>
