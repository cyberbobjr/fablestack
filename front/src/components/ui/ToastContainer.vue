<script setup lang="ts">
import { useToastStore } from '../../stores/toast'
import ToastNotification from './ToastNotification.vue'

const store = useToastStore()
</script>

<template>
    <div class="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        <transition-group name="toast">
            <ToastNotification v-for="toast in store.toasts" :key="toast.id" :toast="toast" />
        </transition-group>
    </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
    transition: all 0.3s ease;
}

.toast-enter-from {
    opacity: 0;
    transform: translateX(100%);
}

.toast-leave-to {
    opacity: 0;
    transform: translateX(100%);
}
</style>
