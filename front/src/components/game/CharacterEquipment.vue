```
<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useUiFontSizes } from '../../composables/useUiFontSizes';
import type { Character } from '../../services/api';
import EquipmentItemRow from './EquipmentItemRow.vue';

defineProps<{
    character: Character
}>()

const { t } = useI18n()
const { uiFontSizes } = useUiFontSizes()
</script>

<template>
    <div class="space-y-4">
        <!-- Weapons -->
        <div class="space-y-2">
            <h3 class="font-bold text-fantasy-text border-b border-gray-700 pb-1 flex items-center gap-2">
                {{ t('ui.weapons') }}
            </h3>
            <div v-if="character.equipment.weapons.length > 0" class="space-y-1">
                <EquipmentItemRow v-for="weapon in character.equipment.weapons" :key="weapon.id" :item="weapon" />
            </div>
            <div v-else class="text-fantasy-muted italic" :class="uiFontSizes.xs">{{ t('ui.no_weapons') }}</div>
        </div>

        <!-- Armor -->
        <div class="space-y-2">
            <h3 class="font-bold text-fantasy-text border-b border-gray-700 pb-1">{{ t('ui.armor') }}</h3>
            <div v-if="character.equipment.armor.length > 0" class="space-y-1">
                <EquipmentItemRow v-for="armor in character.equipment.armor" :key="armor.id" :item="armor" />
            </div>
            <div v-else class="text-fantasy-muted italic" :class="uiFontSizes.xs">{{ t('ui.no_armor') }}</div>
        </div>

        <!-- Inventory -->
        <div class="space-y-2">
            <h3 class="font-bold text-fantasy-text border-b border-gray-700 pb-1">{{ t('ui.inventory') }}</h3>
            <div v-if="character.equipment.consumables.length > 0 || character.equipment.accessories.length > 0"
                class="space-y-1">
                <EquipmentItemRow
                    v-for="(item, index) in [...character.equipment.consumables, ...character.equipment.accessories]"
                    :key="index" :item="item" />
            </div>
            <div v-else class="text-fantasy-muted italic" :class="uiFontSizes.xs">{{ t('ui.empty_inventory') }}</div>
        </div>

        <!-- Currency -->
        <div class="pt-4 border-t border-gray-700 grid grid-cols-3 gap-2 text-center" :class="uiFontSizes.sm">
            <div class="flex flex-col items-center">
                <div class="text-fantasy-gold font-bold flex items-center gap-1">
                    <div class="w-3 h-3 rounded-full bg-yellow-500 border border-yellow-300"></div>
                    {{ character.equipment.gold }} {{ t('ui.gold') }}
                </div>
            </div>
            <div class="flex flex-col items-center">
                <div class="text-fantasy-silver font-bold flex items-center gap-1">
                    <div class="w-3 h-3 rounded-full bg-gray-400 border border-gray-300"></div>
                    {{ character.equipment.silver || 0 }} {{ t('ui.silver') }}
                </div>
            </div>
            <div class="flex flex-col items-center">
                <div class="text-orange-400 font-bold flex items-center gap-1">
                    <div class="w-3 h-3 rounded-full bg-orange-600 border border-orange-400"></div>
                    {{ character.equipment.copper || 0 }} {{ t('ui.copper') }}
                </div>
            </div>
        </div>
    </div>
</template>
```
