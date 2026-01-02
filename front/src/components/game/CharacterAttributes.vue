<script setup lang="ts">
import { Shield } from 'lucide-vue-next';
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
    <div class="space-y-6">
        <!-- Vitals -->
        <div class="grid grid-cols-2 gap-4">
            <div class="bg-black/20 p-3 rounded text-center">
                <div class="text-fantasy-muted uppercase" :class="uiFontSizes.xs">{{ t('ui.hp') }}</div>
                <div class="text-xl font-bold text-red-400">
                    {{ character.combat_stats.current_hit_points }}/{{ character.combat_stats.max_hit_points }}
                </div>
            </div>
            <div class="bg-black/20 p-3 rounded text-center">
                <div class="text-fantasy-muted uppercase" :class="uiFontSizes.xs">{{ t('ui.mp') }}</div>
                <div class="text-xl font-bold text-blue-400">
                    {{ character.combat_stats.current_mana_points }}/{{ character.combat_stats.max_mana_points }}
                </div>
            </div>
        </div>

        <!-- Combat Stats -->
        <div class="bg-fantasy-dark p-4 rounded border border-gray-700 space-y-3">
            <h3 class="font-bold text-fantasy-text flex items-center gap-2">
                <Shield :size="16" /> {{ t('ui.combat') }}
            </h3>
            <div class="flex justify-between" :class="uiFontSizes.sm">
                <span class="text-fantasy-muted">{{ t('ui.armor_class') }}</span>
                <span class="font-bold text-fantasy-text">{{ character.combat_stats.armor_class }}</span>
            </div>
            <div class="flex justify-between" :class="uiFontSizes.sm">
                <span class="text-fantasy-muted">{{ t('ui.attack_bonus') }}</span>
                <span class="font-bold text-fantasy-text">+{{ character.combat_stats.attack_bonus }}</span>
            </div>
        </div>

        <!-- Attributes -->
        <div class="space-y-2">
            <h3 class="font-bold text-fantasy-text border-b border-gray-700 pb-1">{{ t('ui.attributes') }}</h3>
            <div v-for="(value, stat) in character.stats" :key="stat" class="flex justify-between items-center"
                :class="uiFontSizes.sm">
                <span class="capitalize text-fantasy-muted">{{ gameDataStore.translate(String(stat), 'stats') }}</span>
                <span class="font-bold text-fantasy-gold">{{ value }}</span>
            </div>
        </div>
    </div>
</template>
