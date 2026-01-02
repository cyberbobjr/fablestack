<script setup lang="ts">
import { X } from 'lucide-vue-next'

defineProps<{
    show: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    loading?: boolean
}>()

defineEmits(['close', 'confirm'])
</script>

<template>
    <div v-if="show" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
        <div class="bg-fantasy-secondary border border-gray-700 rounded-lg p-6 w-96 shadow-xl relative animate-fade-in">
            <button @click="$emit('close')"
                class="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors cursor-pointer">
                <X :size="20" />
            </button>

            <h2 class="text-xl font-sans font-bold text-fantasy-gold mb-4">{{ title }}</h2>

            <p class="text-fantasy-text mb-8">{{ message }}</p>

            <div class="flex justify-end gap-3">
                <button @click="$emit('close')"
                    class="px-4 py-2 rounded text-fantasy-muted hover:text-fantasy-text hover:bg-fantasy-hover transition-colors cursor-pointer">
                    {{ cancelText || 'Annuler' }}
                </button>
                <button @click="$emit('confirm')" :disabled="loading"
                    class="bg-fantasy-accent hover:bg-red-600 text-white px-4 py-2 rounded transition-colors disabled:opacity-50 font-medium cursor-pointer flex items-center gap-2">
                    <span v-if="loading"
                        class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                    {{ confirmText || 'Confirmer' }}
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.animate-fade-in {
    animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: scale(0.95);
    }

    to {
        opacity: 1;
        transform: scale(1);
    }
}
</style>
