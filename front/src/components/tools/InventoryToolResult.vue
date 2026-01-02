<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { CheckCircle, MinusCircle, Sword, Shield, Zap, Loader, XCircle } from 'lucide-vue-next'
import { useGameDataStore } from '../../stores/gameData'
import { getParsedArgs, isSuccess } from '../../utils/toolUtils'
import type { MessagePart } from '../../services/api'
import { computed } from 'vue'

const props = defineProps<{
    part: MessagePart
    resultPart?: MessagePart
}>()

const { t } = useI18n()
const gameDataStore = useGameDataStore()

const getEquipmentItem = (id: string) => {
    return gameDataStore.getItemById(id)
}

const itemData = computed(() => {
    // Prioritize args (from tool-call) as they are reliable
    if (props.part.args) {
        return getParsedArgs(props.part.args)
    }
    // Fallback to content (from tool-return) if available
    if (props.part.content) {
        return getParsedArgs(props.part.content)
    }
    return {}
})

const resultContent = computed(() => {
    if (props.resultPart?.content) {
        return getParsedArgs(props.resultPart.content)
    }
    return null
})
</script>

<template>
    <div
        class="w-full bg-fantasy-secondary border border-gray-600 rounded-lg p-3 my-2 shadow-lg relative overflow-hidden">
        <div class="flex items-center gap-2 font-bold mb-2 text-fantasy-gold border-b border-gray-700 pb-2">
            <component :is="part.tool_name === 'inventory_add_item' ? CheckCircle : MinusCircle" :size="18" />
            <span>{{ part.tool_name === 'inventory_add_item' ? t('ui.item_added') : t('ui.item_removed') }}</span>
        </div>

        <div class="bg-fantasy-dark p-3 rounded flex items-start gap-3">
            <div
                class="w-10 h-10 rounded bg-fantasy-secondary flex items-center justify-center border border-gray-600 shrink-0">
                <Sword v-if="getEquipmentItem(itemData?.item_id)?.category === 'weapon'" :size="20"
                    class="text-fantasy-gold" />
                <Shield v-else-if="getEquipmentItem(itemData?.item_id)?.category === 'armor'" :size="20"
                    class="text-fantasy-silver" />
                <Zap v-else :size="20" class="text-blue-400" />
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex justify-between items-start">
                    <div class="text-fantasy-text font-bold truncate pr-2">
                        {{ itemData?.item_id ? gameDataStore.translate(itemData.item_id, 'equipment') : 'Unknown Item'
                        }}
                    </div>
                    <div
                        class="text-xs text-fantasy-muted whitespace-nowrap bg-fantasy-secondary px-2 py-0.5 rounded border border-gray-700">
                        x{{ itemData?.qty || 1 }}</div>
                </div>

                <div v-if="gameDataStore.getEquipmentDetails(itemData?.item_id)?.description || getEquipmentItem(itemData?.item_id)?.description"
                    class="text-xs text-fantasy-muted mt-1 italic line-clamp-2">
                    {{ gameDataStore.getEquipmentDetails(itemData?.item_id)?.description ||
                        getEquipmentItem(itemData?.item_id)?.description }}
                </div>
            </div>
        </div>

        <!-- Result Section -->
        <div v-if="resultPart && part.tool_name !== 'inventory_add_item'" class="mt-2 pt-2 border-t border-gray-700">
            <div class="flex items-center gap-2 text-sm">
                <span v-if="isSuccess(resultContent)" class="text-green-400 flex items-center gap-1 font-bold">
                    <CheckCircle :size="14" /> {{ t('ui.success') }}
                </span>
                <span v-else class="text-red-400 flex items-center gap-1 font-bold">
                    <XCircle :size="14" /> {{ t('ui.failure') }}
                </span>
                <span v-if="resultContent?.message" class="text-fantasy-muted ml-2 italic">
                    {{ resultContent.message }}
                </span>
            </div>
        </div>
        <div v-else-if="!resultPart"
            class="mt-2 pt-2 border-t border-gray-700 flex items-center gap-2 text-fantasy-muted text-sm animate-pulse">
            <Loader :size="14" class="animate-spin" />
            <span>{{ t('ui.processing') }}...</span>
        </div>
    </div>
</template>
