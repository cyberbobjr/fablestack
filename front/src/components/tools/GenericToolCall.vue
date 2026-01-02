<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Dices } from 'lucide-vue-next'
import { useGameDataStore } from '../../stores/gameData'
import type { MessagePart } from '../../services/api'

const props = defineProps<{
    part: MessagePart
}>()

const { t } = useI18n()
const gameDataStore = useGameDataStore()

const formatToolName = (name?: string) => {
    if (!name) return t('results.action')
    return t(`tools.${name}`, name)
}

const getFormattedArgs = (args: any) => {
    if (!args) return {}

    let parsedArgs = args
    if (typeof args === 'string') {
        try {
            parsedArgs = JSON.parse(args)
        } catch (e) {
            return { 'value': args }
        }
    }

    if (typeof parsedArgs !== 'object') return {}

    const formatted: Record<string, string> = {}

    for (const [key, value] of Object.entries(parsedArgs)) {
        if (key === 'skill_name') {
            formatted[key] = gameDataStore.translate(value as string, 'skills')
        } else if (key === 'difficulty_name') {
            formatted[key] = t(`difficulties.${value}`, value as string)
        } else if (typeof value === 'string' || typeof value === 'number') {
            formatted[key] = String(value)
        } else {
            formatted[key] = JSON.stringify(value)
        }
    }

    return formatted
}
</script>

<template>
    <div class="w-full bg-fantasy-secondary border border-gray-600 rounded-lg p-3 my-2 shadow-lg">
        <div class="flex items-center gap-2 text-fantasy-gold font-bold border-b border-gray-700 pb-2 mb-2">
            <Dices :size="18" />
            <span>{{ formatToolName(part.tool_name) }}</span>
        </div>

        <!-- Formatted Arguments -->
        <div class="bg-fantasy-dark p-2 rounded space-y-1">
            <div v-for="(value, key) in getFormattedArgs(part.args)" :key="key" class="flex justify-between text-sm">
                <span class="text-fantasy-muted">{{ t(`args.${key}`, key) }} :</span>
                <span class="font-medium text-fantasy-text">{{ value }}</span>
            </div>
            <div v-if="Object.keys(part.args || {}).length === 0" class="text-fantasy-muted text-xs italic">
                Aucun paramètre
            </div>
        </div>
    </div>
</template>
