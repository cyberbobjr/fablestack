<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useUiFontSizes } from '../../composables/useUiFontSizes';
import type { TimelineEvent } from '../../services/api';
import { useGameDataStore } from '../../stores/gameData';

defineProps<{
    event: TimelineEvent
}>()

const { t } = useI18n()
const gameDataStore = useGameDataStore()
const { uiFontSizes } = useUiFontSizes()
</script>

<template>
    <div class="w-full my-4">
        <div class="bg-fantasy-secondary border border-blue-400/30 p-3 rounded-lg flex items-center gap-3 w-full">
            <div class="bg-blue-500/20 p-2 rounded-md">
                <span class="text-2xl">🎒</span>
            </div>
            <div>
                <div class="text-blue-400 font-bold uppercase" :class="uiFontSizes.xs">{{ t('ui.item_acquired') }}</div>
                <div class="text-fantasy-text" :class="uiFontSizes.sm">
                    {{ event.metadata?.item_id ? `${event.metadata.qty}x ${gameDataStore.translate(event.metadata.item_id, 'equipment')}` : event.content }}
                </div>
            </div>
        </div>
    </div>
</template>
