<template>
    <div class="min-h-screen flex items-center justify-center bg-gray-900 px-4">
        <div class="text-center">
            <div v-if="loading" class="space-y-4">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
                <h2 class="text-xl text-white font-medium">{{ t('auth.verifying_token') }}</h2>
            </div>

            <div v-else-if="error" class="space-y-4">
                <div class="text-red-500 text-5xl mb-4">✕</div>
                <h2 class="text-xl text-white font-medium">{{ error }}</h2>
                <router-link to="/login"
                    class="inline-block mt-4 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                    {{ t('auth.back_to_login') }}
                </router-link>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import api from '@/services/api';
import { useUserStore } from '@/stores/user';
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const error = ref('')

onMounted(async () => {
    const token = route.query.token as string

    if (!token) {
        error.value = t('auth.invalid_token')
        loading.value = false
        return
    }

    try {
        const response = await api.verifyMagicLink(token)
        userStore.setToken(response.data.access_token)
        await userStore.fetchProfile()
        router.push('/')
    } catch (e) {
        error.value = t('auth.invalid_token')
    } finally {
        loading.value = false
    }
})
</script>
