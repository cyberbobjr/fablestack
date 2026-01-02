<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { CheckCircle, XCircle, Dices, Target, Activity, Loader } from 'lucide-vue-next'
import { isSuccess, getRollValue, getTargetValue } from '../../utils/toolUtils'
import { useGameDataStore } from '../../stores/gameData'
import type { MessagePart } from '../../services/api'
import { ref, onMounted, computed, watch } from 'vue'
import DiceSpinner from '../DiceSpinner.vue'

const props = defineProps<{
    callPart: MessagePart
    resultPart?: MessagePart
}>()

const emit = defineEmits(['animation-start', 'animation-end'])

const { t } = useI18n()
const gameDataStore = useGameDataStore()

const isAnimating = ref(false)
const showResult = ref(false)

// Logic:
// 1. If tool call is recent (< 10s), start animation for 3s.
// 2. If result arrives during animation, wait until animation finishes.
// 3. If result arrives after animation, show immediately.
// 4. If tool call is old, show result immediately (no animation).

const checkShouldAnimate = () => {
    if (!props.callPart.timestamp) return false
    const callTime = new Date(props.callPart.timestamp).getTime()
    const now = new Date().getTime()
    return (now - callTime) < 10000
}

const handleResultDisplay = () => {
    showResult.value = true
    // Post-result delay before ensuring stream resumes
    setTimeout(() => {
        emit('animation-end')
    }, 1500)
}

onMounted(() => {
    const shouldAnimate = checkShouldAnimate()

    if (shouldAnimate) {
        isAnimating.value = true
        showResult.value = false
        emit('animation-start')

        setTimeout(() => {
            isAnimating.value = false
            // If result is already available, show it now and schedule end
            if (props.resultPart) {
                handleResultDisplay()
            }
        }, 3000)
    } else {
        // No animation for history/old messages
        isAnimating.value = false
        showResult.value = true
    }
})

// Watch for result arrival
watch(() => props.resultPart, (newVal) => {
    if (newVal && !isAnimating.value && !showResult.value) {
        // Result arrived after animation finished (slow backend)
        // AND we haven't shown result yet.
        // We need to check if we SHOULD have animated to know if we need to emit end
        // But simpler: if !showResult and !isAnimating, it means we were waiting in "loading" state
        // which only happens if shouldAnimate was true.
        handleResultDisplay()
    }
})

// --- Call Logic ---
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

// --- Result Logic ---
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
    <div
        class="w-full bg-fantasy-secondary border border-gray-600 rounded-lg p-3 my-2 shadow-lg relative overflow-hidden transition-all duration-500">

        <!-- Header: Tool Name -->
        <div class="flex items-center gap-2 text-fantasy-gold font-bold border-b border-gray-700 pb-2 mb-2">
            <Dices :size="18" />
            <span>{{ formatToolName(callPart.tool_name) }}</span>
        </div>

        <!-- Call Parameters (Inputs) -->
        <div class="bg-fantasy-dark p-2 rounded space-y-1 mb-3">
            <div v-for="(value, key) in getFormattedArgs(callPart.args)" :key="key"
                class="flex justify-between text-sm">
                <span class="text-fantasy-muted">{{ t(`args.${key}`, key) }} :</span>
                <span class="font-medium text-fantasy-text">{{ value }}</span>
            </div>
        </div>

        <!-- Animation State -->
        <div v-if="isAnimating" class="py-4 border-t border-gray-700 fade-in">
            <DiceSpinner />
        </div>

        <!-- Result Section (if available AND not animating) -->
        <div v-if="resultPart && showResult" class="relative z-10 pt-2 border-t border-gray-700 fade-in"
            :class="isSuccess(resultPart.content) ? 'animate-bounce-in' : 'animate-shake'">
            <!-- Success/Failure Indicator (Background Icon) -->
            <div class="absolute top-2 right-0 p-2 opacity-10 pointer-events-none">
                <CheckCircle v-if="isSuccess(resultPart.content)" :size="64" class="text-green-600" />
                <XCircle v-else :size="64" class="text-red-600" />
            </div>

            <div class="flex items-center gap-2 font-bold mb-2"
                :class="isSuccess(resultPart.content) ? 'text-green-600' : 'text-red-600'">
                <component :is="isSuccess(resultPart.content) ? CheckCircle : XCircle" :size="18" />
                <span>{{ t('results.result') }} : {{ getResultTitle(resultPart.content) }}</span>
            </div>

            <div class="grid grid-cols-3 gap-2 text-center text-sm">
                <div class="bg-fantasy-dark p-2 rounded border border-gray-700">
                    <div class="text-fantasy-muted text-xs mb-1 flex items-center justify-center gap-1">
                        <Dices :size="12" /> {{ t('results.roll') }}
                    </div>
                    <div class="font-mono font-bold text-fantasy-gold">{{ getRollValue(resultPart.content) }}</div>
                </div>
                <div class="bg-fantasy-dark p-2 rounded border border-gray-700">
                    <div class="text-fantasy-muted text-xs mb-1 flex items-center justify-center gap-1">
                        <Target :size="12" /> {{ t('results.target') }}
                    </div>
                    <div class="font-mono font-bold text-fantasy-silver">{{ getTargetValue(resultPart.content) }}</div>
                </div>
                <div class="bg-fantasy-dark p-2 rounded border border-gray-700">
                    <div class="text-fantasy-muted text-xs mb-1 flex items-center justify-center gap-1">
                        <Activity :size="12" /> {{ t('results.stat') }}
                    </div>
                    <div class="font-mono font-bold text-blue-300 truncate" :title="getStatName(resultPart.content)">
                        {{ getStatName(resultPart.content) }}
                    </div>
                </div>
            </div>
        </div>

        <!-- Waiting for result but NOT animating (e.g. backend slow, >3s) -->
        <div v-else
            class="flex items-center justify-center p-4 text-fantasy-muted animate-pulse border-t border-gray-700">
            <Loader :size="20" class="animate-spin mr-2" />
            <span>{{ t('ui.waiting_result') || 'En attente du résultat...' }}</span>
        </div>

    </div>
</template>

<style scoped>
.fade-in {
    animation: fadeIn 0.5s ease-in-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
    }

    to {
        opacity: 1;
    }
}

.animate-bounce-in {
    animation: bounceIn 0.8s cubic-bezier(0.215, 0.61, 0.355, 1);
}

@keyframes bounceIn {
    0% {
        opacity: 0;
        transform: scale(0.3);
    }

    20% {
        transform: scale(1.1);
    }

    40% {
        transform: scale(0.9);
    }

    60% {
        opacity: 1;
        transform: scale(1.03);
    }

    80% {
        transform: scale(0.97);
    }

    100% {
        opacity: 1;
        transform: scale(1);
    }
}

.animate-shake {
    animation: shake 0.5s cubic-bezier(.36, .07, .19, .97) both;
}

@keyframes shake {

    10%,
    90% {
        transform: translate3d(-1px, 0, 0);
    }

    20%,
    80% {
        transform: translate3d(2px, 0, 0);
    }

    30%,
    50%,
    70% {
        transform: translate3d(-4px, 0, 0);
    }

    40%,
    60% {
        transform: translate3d(4px, 0, 0);
    }
}
</style>
