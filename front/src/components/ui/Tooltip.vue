<script setup lang="ts">
import { ref } from 'vue';

defineProps<{
    text: string
}>()

const isVisible = ref(false)
const trigger = ref<HTMLElement | null>(null)
const tooltipPosition = ref({ top: 0, left: 0 })

const show = () => {
    if (!trigger.value) return
    const rect = trigger.value.getBoundingClientRect()
    tooltipPosition.value = {
        top: rect.top - 8, // 8px spacing
        left: rect.left + rect.width / 2
    }
    isVisible.value = true
}

const hide = () => {
    isVisible.value = false
}
</script>

<template>
    <div ref="trigger" class="inline-block" @mouseenter="show" @mouseleave="hide">
        <slot></slot>

        <Teleport to="body">
            <div v-if="isVisible && text"
                class="fixed z-[9999] px-3 py-2 text-sm text-white bg-gray-900 rounded-lg shadow-lg pointer-events-none transform -translate-x-1/2 -translate-y-full w-64"
                :style="{ top: `${tooltipPosition.top}px`, left: `${tooltipPosition.left}px` }">
                {{ text }}
                <!-- Arrow -->
                <div
                    class="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2 border-4 border-transparent border-t-gray-900">
                </div>
            </div>
        </Teleport>
    </div>
</template>
