<script setup lang="ts">
import { Dices, Hexagon } from 'lucide-vue-next';
import { computed } from 'vue';
import { useGameDataStore } from '../../stores/gameData';

import type { ChoiceData } from '../../services/api';
import { useUserStore } from '../../stores/user';

const props = defineProps<{
    choice: ChoiceData;
    disabled?: boolean;
}>();

const emit = defineEmits<{
    (e: 'select', choice: ChoiceData): void;
}>();

const gameDataStore = useGameDataStore();
const userStore = useUserStore();
const hasSkillCheck = computed(() => !!props.choice.skill_check);

const difficultyColorClass = computed(() => {
    switch (props.choice.difficulty) {
        case 'unfavorable': return 'bg-red-900/10 hover:bg-red-900/20 border-red-500/20 hover:border-red-500/40 text-red-200';
        case 'favorable': return 'bg-green-900/10 hover:bg-green-900/20 border-green-500/20 hover:border-green-500/40 text-green-200';
        default: return 'bg-fantasy-secondary hover:bg-fantasy-hover border-white/5 hover:border-fantasy-accent/30';
    }
});

const indicatorClass = computed(() => {
    switch (props.choice.difficulty) {
        case 'unfavorable': return 'bg-gradient-to-b from-red-600 to-transparent';
        case 'favorable': return 'bg-gradient-to-b from-green-600 to-transparent';
        default: return null;
    }
});

const iconContainerClass = computed(() => {
    switch (props.choice.difficulty) {
        case 'unfavorable': return 'bg-red-500/10 border-red-500/30 text-red-400 group-hover:bg-red-500/20 group-hover:text-red-300 group-hover:border-red-500/50';
        case 'favorable': return 'bg-green-500/10 border-green-500/30 text-green-400 group-hover:bg-green-500/20 group-hover:text-green-300 group-hover:border-green-500/50';
        default: return 'bg-fantasy-dark border-white/5 text-fantasy-gold group-hover:bg-fantasy-accent group-hover:text-white group-hover:border-fantasy-accent';
    }
});

const badgeClass = computed(() => {
    switch (props.choice.difficulty) {
        case 'unfavorable': return 'bg-red-900/40 border-red-500/30 text-red-300';
        case 'favorable': return 'bg-green-900/40 border-green-500/30 text-green-200';
        default: return 'bg-amber-900/40 border-amber-500/30 text-amber-200';
    }
});

const fontSizeClass = computed(() => {
    switch (userStore.preferences.font_size) {
        case 'small': return 'text-xs'
        case 'large': return 'text-base'
        case 'xlarge': return 'text-lg'
        default: return 'text-sm'
    }
})
</script>

<template>
    <button @click="emit('select', props.choice)" :disabled="props.disabled"
        class="group w-full text-left transition-all duration-300 transform hover:-translate-y-1 relative overflow-hidden rounded-xl border p-0"
        :class="difficultyColorClass">

        <!-- Difficulty indicator strip -->
        <div v-if="indicatorClass" class="absolute left-0 top-0 bottom-0 w-1 opacity-50" :class="indicatorClass"></div>

        <div class="p-3 flex gap-3 items-center">
            <!-- Icon Container -->
            <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border transition-colors duration-300"
                :class="iconContainerClass">
                <Dices v-if="hasSkillCheck" :size="16" />
                <Hexagon v-else :size="16" />
            </div>

            <!-- Text Content -->
            <div class="flex-1 min-w-0 flex items-center gap-3"> <!-- min-w-0 ensures truncation works if needed -->

                <!-- Skill Badge (Moved inline with title or just above) -->
                <span v-if="hasSkillCheck"
                    class="shrink-0 inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider border"
                    :class="badgeClass">
                    {{ gameDataStore.translate(choice.skill_check!) }}
                </span>


                <!-- Main Description -->
                <p class="text-fantasy-text leading-snug font-medium line-clamp-1" :class="fontSizeClass">
                    {{ choice.label }}
                </p>
            </div>

            <!-- Arrow/Interaction Hint -->
            <div
                class="text-fantasy-muted opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 transform duration-300">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24"
                    stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
            </div>
        </div>
    </button>
</template>
