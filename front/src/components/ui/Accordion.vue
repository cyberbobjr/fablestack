<script setup lang="ts">
import { ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

const props = defineProps<{
    isDefaultOpen?: boolean
}>()

const isOpen = ref(props.isDefaultOpen || false)

const toggle = () => {
    isOpen.value = !isOpen.value
}
</script>

<template>
    <div class="border border-gray-700 rounded bg-fantasy-dark overflow-hidden transition-all duration-200">
        <!-- Header -->
        <div @click="toggle"
            class="cursor-pointer p-2 flex items-center justify-between hover:bg-white/5 transition-colors">
            <div class="flex-1">
                <slot name="header" :isOpen="isOpen" :toggle="toggle"></slot>
            </div>
            <div class="ml-2 text-fantasy-muted transition-transform duration-200" :class="{ 'rotate-180': isOpen }">
                <ChevronDown :size="16" />
            </div>
        </div>

        <!-- Content -->
        <div v-show="isOpen" class="border-t border-gray-700 bg-black/20 p-3 text-sm text-fantasy-text">
            <slot name="content"></slot>
        </div>
    </div>
</template>
