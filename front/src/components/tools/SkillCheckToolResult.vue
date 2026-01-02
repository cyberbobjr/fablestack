<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { CheckCircle, XCircle, Dices, Target, Activity } from 'lucide-vue-next'
import { isSuccess, getRollValue, getTargetValue } from '../../utils/toolUtils'
import { useGameDataStore } from '../../stores/gameData'
import type { MessagePart } from '../../services/api'

const props = defineProps<{
    part: MessagePart
}>()

const { t } = useI18n()
const gameDataStore = useGameDataStore()

const getResultTitle = (content: any) => {
    if (!content) return t('results.result')
    if (typeof content === 'object' && 'degree' in content) {
        const key = content.degree.toLowerCase().replace(' ', '_')
        return t(`results.${key}`, content.degree)
    }
    return isSuccess(content) ? t('results.success') : t('results.failure')
}

const getStatName = (content: any) => {
    if (content && typeof content === 'object' && 'skill_name' in content) {
        return gameDataStore.translate(content.skill_name, 'skills')
    }
    return '-'
}
</script>

<template>
    <div class="relative z-10">
        <!-- Success/Failure Indicator -->
        <div class="absolute top-0 right-0 p-2 opacity-20">
            <CheckCircle v-if="isSuccess(part.content)" :size="48" class="text-green-600" />
            <XCircle v-else :size="48" class="text-red-600" />
        </div>

        <div class="flex items-center gap-2 font-bold mb-2"
            :class="isSuccess(part.content) ? 'text-green-600' : 'text-red-600'">
            <component :is="isSuccess(part.content) ? CheckCircle : XCircle" :size="18" />
            <span>{{ t('results.result') }} : {{ getResultTitle(part.content) }}</span>
        </div>

        <div class="grid grid-cols-3 gap-2 text-center text-sm">
            <div class="bg-fantasy-dark p-2 rounded border border-gray-700">
                <div class="text-fantasy-muted text-xs mb-1 flex items-center justify-center gap-1">
                    <Dices :size="12" /> {{ t('results.roll') }}
                </div>
                <div class="font-mono font-bold text-fantasy-gold">{{ getRollValue(part.content) }}</div>
            </div>
            <div class="bg-fantasy-dark p-2 rounded border border-gray-700">
                <div class="text-fantasy-muted text-xs mb-1 flex items-center justify-center gap-1">
                    <Target :size="12" /> {{ t('results.target') }}
                </div>
                <div class="font-mono font-bold text-fantasy-silver">{{ getTargetValue(part.content) }}</div>
            </div>
            <div class="bg-fantasy-dark p-2 rounded border border-gray-700">
                <div class="text-fantasy-muted text-xs mb-1 flex items-center justify-center gap-1">
                    <Activity :size="12" /> {{ t('results.stat') }}
                </div>
                <div class="font-mono font-bold text-blue-300 truncate" :title="getStatName(part.content)">
                    {{ getStatName(part.content) }}
                </div>
            </div>
        </div>
    </div>
</template>
