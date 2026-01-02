<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import NavBar from './components/NavBar.vue'
import ToastContainer from './components/ui/ToastContainer.vue'
import { useGameDataStore } from './stores/gameData'

const gameDataStore = useGameDataStore()
const userStore = useUserStore()

onMounted(async () => {
  await gameDataStore.fetchAllData()
})
</script>

<template>
  <div class="min-h-screen bg-fantasy-dark text-fantasy-text font-sans">
    <NavBar v-if="userStore.isAuthenticated" />

    <ToastContainer />

    <main class="w-full mx-auto p-4">
      <RouterView />
    </main>
  </div>
</template>

<style scoped></style>
