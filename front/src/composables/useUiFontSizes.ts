import { computed, type ComputedRef } from 'vue'
import { useUserStore } from '../stores/user'

interface UiFontSizes {
    xs: string
    sm: string
    base: string
}

export function useUiFontSizes(): { uiFontSizes: ComputedRef<UiFontSizes> } {
    const userStore = useUserStore()

    const uiFontSizes: ComputedRef<UiFontSizes> = computed(() => {
        switch (userStore.preferences.font_size) {
            case 'small': return { xs: 'text-xs', sm: 'text-xs', base: 'text-sm' }
            case 'large': return { xs: 'text-sm', sm: 'text-base', base: 'text-lg' }
            case 'xlarge': return { xs: 'text-base', sm: 'text-lg', base: 'text-xl' }
            default: return { xs: 'text-xs', sm: 'text-sm', base: 'text-base' }
        }
    })

    return { uiFontSizes }
}
