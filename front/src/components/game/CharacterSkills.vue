<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useUiFontSizes } from '../../composables/useUiFontSizes';
import type { Character } from '../../services/api';
import { useGameDataStore } from '../../stores/gameData';

defineProps<{
    character: Character
}>()

const { t } = useI18n()
const gameDataStore = useGameDataStore()
const { uiFontSizes } = useUiFontSizes()
</script>

<template>
    <div class="space-y-4">
        <div v-for="(skills, category) in character.skills" :key="category" class="space-y-2">
            <h3 class="font-bold text-fantasy-text border-b border-gray-700 pb-1 capitalize">
                {{ gameDataStore.translate(category as unknown as string) }}
            </h3>
            <div v-if="Object.keys(skills).length > 0" class="space-y-1">
                <div v-for="(rank, skill) in skills" :key="skill" class="flex justify-between items-center"
                    :class="uiFontSizes.sm">
                    <span class="text-fantasy-muted">{{ gameDataStore.translate(skill as unknown as string) }}</span>
                    <span class="font-bold" :class="Number(rank) > 0 ? 'text-fantasy-text' : 'text-fantasy-muted'">{{
                        rank
                    }}</span>
                </div>
            </div>
            <div v-else class="text-xs text-fantasy-muted italic">{{ t('ui.no_skills') }}</div>
        </div>
    </div>
</template>
