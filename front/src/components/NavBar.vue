<script setup lang="ts">
import { useUserStore } from '@/stores/user';
import { PlusCircle, Settings, Shield, User } from 'lucide-vue-next';
const userStore = useUserStore();
</script>

<template>
    <header class="bg-fantasy-secondary p-4 shadow-md border-b border-fantasy-accent/20">
        <div class="container mx-auto flex justify-between items-center">
            <router-link to="/"
                class="text-2xl font-sans font-bold text-fantasy-gold hover:text-white transition-colors">
                JdR - Terres du Milieu
            </router-link>
            <nav class="flex items-center gap-4">
                <router-link to="/"
                    class="text-fantasy-text hover:text-fantasy-accent transition-colors">Accueil</router-link>

                <router-link v-if="userStore.user?.role === 'admin'" to="/admin"
                    class="flex items-center gap-2 text-purple-400 hover:text-purple-300 transition-colors font-bold">
                    <Shield :size="18" />
                    Admin
                </router-link>

                <router-link to="/characters"
                    class="flex items-center gap-2 text-fantasy-text hover:text-fantasy-accent transition-colors">
                    <User :size="18" />
                    Personnages
                </router-link>

                <router-link to="/new-game"
                    class="flex items-center gap-2 bg-fantasy-accent text-white px-4 py-2 rounded hover:bg-red-600 transition-colors">
                    <PlusCircle :size="18" />
                    Nouvelle Partie
                </router-link>

                <router-link to="/profile"
                    class="p-2 rounded-full hover:bg-fantasy-hover transition-colors text-fantasy-muted hover:text-fantasy-text cursor-pointer"
                    title="Préférences">
                    <Settings :size="20" />
                </router-link>
            </nav>
        </div>
    </header>
</template>
