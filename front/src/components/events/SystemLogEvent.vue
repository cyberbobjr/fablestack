<script setup lang="ts">
import { useUiFontSizes } from '../../composables/useUiFontSizes';
import type { TimelineEvent } from '../../services/api';

defineProps<{
    event: TimelineEvent
    isDebugMode: boolean
}>()

const { uiFontSizes } = useUiFontSizes()
</script>

<template>
    <div v-if="isDebugMode" class="flex justify-center my-2">
        <div class="flex items-center gap-3 bg-gray-900/50 border border-gray-700/50 text-gray-300 px-4 py-2 font-mono shadow-sm hover:border-fantasy-gold/30 w-full transition-colors"
            :class="uiFontSizes.sm">
            <span class="text-lg">{{ event.icon || '⚙️' }}</span>
            <span>{{ event.content }}</span>
        </div>
    </div>
</template>
