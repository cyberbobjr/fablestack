<script setup lang="ts">
import { Dices } from 'lucide-vue-next'
</script>

<template>
    <div class="flex flex-col items-center justify-center p-4 gap-2">
        <div class="relative">
            <Dices :size="48" class="text-fantasy-gold animate-spin-slow" />
        </div>
        <span class="text-fantasy-muted text-sm font-medium animate-pulse">Lancer de dé en cours...</span>
    </div>
</template>

<style scoped>
.animate-spin-slow {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from {
        transform: rotate(0deg);
    }

    to {
        transform: rotate(360deg);
    }
}
</style>
