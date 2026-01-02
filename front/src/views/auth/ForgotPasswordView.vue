<template>
    <div
        class="min-h-screen flex items-center justify-center bg-gray-900 px-4 py-12 sm:px-6 lg:px-8 relative overflow-hidden">
        <div
            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-900/20 rounded-full blur-[120px] pointer-events-none">
        </div>

        <div
            class="max-w-md w-full space-y-8 relative z-10 bg-gray-800/50 backdrop-blur-xl p-8 rounded-2xl border border-gray-700/50 shadow-2xl">
            <div>
                <h2 class="mt-2 text-center text-3xl font-extrabold text-white tracking-tight">
                    {{ t('auth.forgot_password_title') }}
                </h2>
                <p class="mt-2 text-center text-sm text-gray-400">
                    {{ t('auth.forgot_password_desc') }}
                </p>
            </div>

            <form class="mt-8 space-y-6" @submit.prevent="handleSubmit">
                <div class="rounded-md shadow-sm -space-y-px">
                    <div>
                        <label for="email-address" class="block text-sm font-medium text-gray-300 mb-1">{{
                            t('auth.email') }}</label>
                        <input id="email-address" name="email" type="email" autocomplete="email" required
                            v-model="email"
                            class="appearance-none relative block w-full px-3 py-3 border border-gray-600 placeholder-gray-500 text-white bg-gray-900/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 focus:z-10 sm:text-sm transition-all"
                            :placeholder="t('auth.email_placeholder')" />
                    </div>
                </div>

                <div v-if="message" class="rounded-md bg-green-900/50 border border-green-500/50 p-4">
                    <div class="flex">
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-green-200">{{ message }}</h3>
                        </div>
                    </div>
                </div>

                <div v-if="error" class="rounded-md bg-red-900/50 border border-red-500/50 p-4">
                    <div class="flex">
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-red-200">{{ error }}</h3>
                        </div>
                    </div>
                </div>

                <div class="flex items-center justify-between">
                    <router-link to="/login" class="text-sm font-medium text-purple-400 hover:text-purple-300">
                        {{ t('auth.back_to_login') }}
                    </router-link>
                </div>

                <div>
                    <button type="submit" :disabled="loading || !!message"
                        class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02]">
                        <span v-if="loading" class="absolute left-0 inset-y-0 flex items-center pl-3">
                            <svg class="animate-spin h-5 w-5 text-purple-300" xmlns="http://www.w3.org/2000/svg"
                                fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                    stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                                </path>
                            </svg>
                        </span>
                        {{ loading ? t('common.loading') : t('auth.send_reset_link') }}
                    </button>
                </div>
            </form>
        </div>
    </div>
</template>

<script setup lang="ts">
import api from '@/services/api';
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n()
const email = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

const handleSubmit = async () => {
    loading.value = true
    message.value = ''
    error.value = ''

    try {
        await api.forgotPassword(email.value)
        message.value = t('auth.reset_link_sent')
    } catch (e: any) {
        error.value = t('auth.generic_error')
    } finally {
        loading.value = false
    }
}
</script>
