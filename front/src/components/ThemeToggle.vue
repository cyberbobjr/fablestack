<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Sun, Moon } from 'lucide-vue-next'

const isDark = ref(true)

const toggleTheme = () => {
    isDark.value = !isDark.value
    updateTheme()
}

const updateTheme = () => {
    const html = document.documentElement
    if (isDark.value) {
        html.classList.remove('light-theme')
        localStorage.setItem('theme', 'dark')
    } else {
        html.classList.add('light-theme')
        localStorage.setItem('theme', 'light')
    }
}

onMounted(() => {
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme === 'light') {
        isDark.value = false
    } else {
        isDark.value = true
    }
    updateTheme()
})
</script>

<template>
    <button @click="toggleTheme"
        class="p-2 rounded-full hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
        :title="isDark ? 'Passer en mode clair' : 'Passer en mode sombre'">
        <Sun v-if="isDark" :size="20" />
        <Moon v-else :size="20" />
    </button>
</template>
