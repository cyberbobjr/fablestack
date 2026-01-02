<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { X, Info, CheckCircle, AlertTriangle, AlertCircle } from 'lucide-vue-next'
import type { Toast, ToastType } from '../../stores/toast'
import { useToastStore } from '../../stores/toast'

const props = defineProps<{
    toast: Toast
}>()

const store = useToastStore()

const remove = () => {
    store.removeToast(props.toast.id)
}

const icon = computed(() => {
    switch (props.toast.type) {
        case 'success': return CheckCircle
        case 'warning': return AlertTriangle
        case 'error': return AlertCircle
        default: return Info
    }
})

const bgClass = computed(() => {
    switch (props.toast.type) {
        case 'success': return 'bg-green-600 border-green-500'
        case 'warning': return 'bg-yellow-600 border-yellow-500'
        case 'error': return 'bg-red-600 border-red-500'
        default: return 'bg-blue-600 border-blue-500'
    }
})

</script>

<template>
    <div class="flex items-center gap-3 p-4 rounded shadow-lg border text-white transform transition-all duration-300 ease-in-out hover:scale-105 pointer-events-auto min-w-[300px]"
        :class="bgClass" role="alert">
        <component :is="icon" class="flex-shrink-0" :size="20" />
        <div class="flex-1 text-sm font-medium">
            {{ toast.message }}
        </div>
        <button @click="remove" class="text-white/80 hover:text-white transition-colors">
            <X :size="18" />
        </button>
    </div>
</template>
