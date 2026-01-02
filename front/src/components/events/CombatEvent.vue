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

const getCombatMessage = (event: TimelineEvent): string => {
    if (!event.metadata || !event.metadata.attack_details) {
        return event.content
    }

    const d = event.metadata.attack_details

    const params: Record<string, string | number> = {
        attacker: d.attacker_name,
        target: d.target_name,
        weapon: gameDataStore.translate(d.weapon_name, 'weapons'),
        roll: d.attack_roll,
        ac: d.target_ac,
        damage: d.damage
    }

    let resultMsg: string = ''
    if (d.is_crit) {
        resultMsg = t('ui.log.crit', params)
    } else if (d.is_hit) {
        resultMsg = t('ui.log.hit', params)
    } else {
        resultMsg = t('ui.log.miss', params)
    }

    let damageMsg: string = ''
    if (d.is_hit && d.damage > 0) {
        damageMsg = t('ui.log.damage', params)
    }

    let defeatMsg: string = ''
    if (d.is_fatal) {
        defeatMsg = t('ui.log.defeated', params)
    }

    if (event.type === 'COMBAT_ATTACK') {
        if (d.is_hit) {
            return `${resultMsg} ${damageMsg} ${defeatMsg}`.trim()
        } else {
            return resultMsg
        }
    } else if (event.type === 'COMBAT_DAMAGE') {
        return damageMsg || event.content
    }

    return event.content
}
</script>

<template>
    <div class="flex justify-center my-2">
        <div class="bg-fantasy-secondary border border-red-500/30 text-fantasy-text px-4 py-2 rounded-lg font-mono flex items-center gap-3"
            :class="uiFontSizes.sm">
            <span class="text-lg">{{ event.icon }}</span>
            <span>{{ getCombatMessage(event) }}</span>
        </div>
    </div>
</template>
