<script setup lang="ts">
import { RotateCcw } from 'lucide-vue-next';
import { useUiFontSizes } from '../../composables/useUiFontSizes';
import type { TimelineEvent } from '../../services/api';

defineProps<{
    event: TimelineEvent
    isDebugMode: boolean
}>()

defineEmits<{
    (e: 'restore', timestamp: string): void
}>()

const { uiFontSizes } = useUiFontSizes()

const formatTime = (timestamp: string): string => {
    if (!timestamp) return ''
    const date: Date = new Date(timestamp)
    return isNaN(date.getTime()) ? '' : date.toLocaleTimeString()
}
</script>

<template>
    <div class="flex justify-end">
        <div class="bg-fantasy-accent text-white px-5 py-3 rounded-2xl rounded-tr-none max-w-[90%] shadow-lg">
            <p :class="uiFontSizes.base">{{ event.content }}</p>
            <div class="flex items-center justify-end gap-2 mt-1">
                <span class="text-xs opacity-70">{{ formatTime(event.timestamp) }}</span>
                <button v-if="isDebugMode" @click="$emit('restore', event.timestamp)"
                    class="text-xs text-white/50 hover:text-white bg-black/20 hover:bg-black/40 p-1 rounded transition-colors"
                    title="Restore to this point">
                    <RotateCcw :size="12" />
                </button>
            </div>
        </div>
    </div>
</template>
