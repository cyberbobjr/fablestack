<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useUiFontSizes } from '../../composables/useUiFontSizes';
import type { TimelineEvent } from '../../services/api';

defineProps<{
    event: TimelineEvent
}>()

const { t } = useI18n()
const { uiFontSizes } = useUiFontSizes()

const parseCurrencyContent = (content: string): string => {
    if (!content) return content

    const isRemoved: boolean = content.includes('Removed')
    const isAdded: boolean = content.includes('Added')

    if (!isRemoved && !isAdded) return content

    const goldMatch: RegExpMatchArray | null = content.match(/(\d+)G/)
    const silverMatch: RegExpMatchArray | null = content.match(/(\d+)S/)
    const copperMatch: RegExpMatchArray | null = content.match(/(\d+)C/)

    const parts: string[] = []
    if (goldMatch) parts.push(`${goldMatch[1]} ${t('ui.currency.gold', 'Or')}`)
    if (silverMatch) parts.push(`${silverMatch[1]} ${t('ui.currency.silver', 'Argent')}`)
    if (copperMatch) parts.push(`${copperMatch[1]} ${t('ui.currency.copper', 'Cuivre')}`)

    const currencyStr: string = parts.join(', ')

    if (isRemoved) {
        return t('ui.currency_removed', { amount: currencyStr })
    } else {
        return t('ui.currency_added', { amount: currencyStr })
    }
}
</script>

<template>
    <div class="w-full my-2">
        <div class="bg-fantasy-secondary border border-yellow-500/30 text-fantasy-gold px-4 py-2 rounded-lg font-bold tracking-wide flex items-center gap-2 w-full"
            :class="uiFontSizes.sm">
            <span>💰</span>
            <span>{{ parseCurrencyContent(event.content) }}</span>
        </div>
    </div>
</template>
