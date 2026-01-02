<script setup lang="ts">
import { marked } from 'marked';
import { computed, type ComputedRef } from 'vue';
import type { TimelineEvent } from '../../services/api';
import { useUserStore } from '../../stores/user';

defineProps<{
    event: TimelineEvent
}>()

const userStore = useUserStore()

const fontSizeClass: ComputedRef<string> = computed(() => {
    switch (userStore.preferences.font_size) {
        case 'small': return 'prose-sm'
        case 'large': return 'prose-lg'
        case 'xlarge': return 'prose-xl'
        default: return 'prose-base'
    }
})

const renderMarkdown = (text: string): string => {
    if (!text) return ''
    const cleanText: string = text.replace(/<<SPEAKER:[^>]+>>/g, '')
    return marked(cleanText) as string
}
</script>

<template>
    <div class="flex justify-start">
        <div class="bg-fantasy-secondary border border-gray-700/50 text-fantasy-text px-6 py-5 rounded-2xl rounded-tl-none max-w-[90%] shadow-md prose"
            :class="[fontSizeClass, { 'prose-invert': userStore.preferences.theme === 'dark' }]"
            v-html="renderMarkdown(event.content)">
        </div>
    </div>
</template>
