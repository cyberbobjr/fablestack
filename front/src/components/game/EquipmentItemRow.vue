<script setup lang="ts">
import { Coins, Crosshair, Shield, Sword, Weight } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUiFontSizes } from '../../composables/useUiFontSizes'
import { useGameDataStore } from '../../stores/gameData'
import Accordion from '../ui/Accordion.vue'

const props = defineProps<{
    item: any // Using specific type if available would be better, but 'any' matches current loose typing
}>()

const { t } = useI18n()
const gameDataStore = useGameDataStore()
const { uiFontSizes } = useUiFontSizes()

const itemName = computed(() => {
    const translation = gameDataStore.translate(props.item.item_id, 'equipment')
    if (translation === props.item.item_id && props.item.name) {
        return props.item.name
    }
    return translation
})

const itemDescription = computed(() => {
    const details = gameDataStore.getEquipmentDetails(props.item.item_id)
    return details?.description || props.item.description || ''
})

</script>

<template>
    <Accordion>
        <template #header>
            <div class="flex items-center justify-between w-full">
                <span class="font-medium text-fantasy-text">{{ itemName }}</span>

                <!-- Main Stats Summary -->
                <div class="flex items-center gap-3 text-fantasy-muted mr-2" :class="uiFontSizes.sm">
                    <!-- Weapon Damage -->
                    <span v-if="item.damage" class="flex items-center gap-1 text-fantasy-accent">
                        <Sword :size="14" />
                        {{ item.damage }}
                    </span>
                    <!-- Armor Protection -->
                    <span v-if="item.protection" class="flex items-center gap-1 text-blue-400">
                        <Shield :size="14" />
                        {{ item.protection }}
                    </span>
                    <!-- Quantity if > 1 -->
                    <span v-if="item.quantity && item.quantity > 1"
                        class="px-1.5 py-0.5 bg-fantasy-dark rounded text-fantasy-muted" :class="uiFontSizes.xs">
                        x{{ item.quantity }}
                    </span>
                </div>
            </div>
        </template>

        <template #content>
            <div class="space-y-3">
                <!-- Description -->
                <p v-if="itemDescription" class="text-fantasy-muted italic">{{ itemDescription }}</p>

                <!-- Stats Grid -->
                <div class="grid grid-cols-2 gap-2 text-fantasy-muted" :class="uiFontSizes.xs">
                    <!-- Weight -->
                    <div v-if="item.weight" class="flex items-center gap-1">
                        <Weight :size="12" />
                        <span>{{ item.weight }} {{ t('ui.weight_unit', 'kg') }}</span>
                    </div>

                    <!-- Cost -->
                    <div v-if="item.cost_gold || item.cost_silver || item.cost_copper" class="flex items-center gap-1">
                        <Coins :size="12" />
                        <span>
                            {{ item.cost_gold ? `${item.cost_gold} PO` : '' }}
                            {{ item.cost_silver ? `${item.cost_silver} PA` : '' }}
                            {{ item.cost_copper ? `${item.cost_copper} PC` : '' }}
                        </span>
                    </div>

                    <!-- Range (Weapons) -->
                    <div v-if="item.range" class="flex items-center gap-1">
                        <Crosshair :size="12" />
                        <span>{{ item.range }}m</span>
                    </div>
                </div>
            </div>
        </template>
    </Accordion>
</template>
