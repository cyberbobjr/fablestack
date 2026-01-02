<template>
    <div
        class="min-h-screen flex items-center justify-center bg-gray-900 px-4 py-12 sm:px-6 lg:px-8 relative overflow-hidden">
        <!-- Background Glow -->
        <div
            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-900/20 rounded-full blur-[120px] pointer-events-none">
        </div>

        <div
            class="max-w-md w-full space-y-8 relative z-10 bg-gray-800/50 backdrop-blur-xl p-8 rounded-2xl border border-gray-700/50 shadow-2xl">
            <div>
                <h2 class="mt-2 text-center text-3xl font-extrabold text-white tracking-tight">
                    {{ t('auth.login_title') }}
                </h2>
                <p class="mt-2 text-center text-sm text-gray-400">
                    {{ t('auth.or') }}
                    <router-link to="/register"
                        class="font-medium text-purple-400 hover:text-purple-300 transition-colors">
                        {{ t('auth.create_account') }}
                    </router-link>
                </p>
            </div>

            <form class="mt-8 space-y-6" @submit.prevent="handleLogin">

                <!-- Login Mode Switcher -->
                <div class="flex border-b border-gray-700 mb-6">
                    <button type="button" @click="loginMode = 'password'"
                        :class="loginMode === 'password' ? 'text-purple-400 border-purple-400' : 'text-gray-400 border-transparent hover:text-gray-200'"
                        class="flex-1 pb-2 border-b-2 font-medium transition-colors">
                        {{ t('auth.sign_in') }}
                    </button>
                    <button type="button" @click="loginMode = 'magic'"
                        :class="loginMode === 'magic' ? 'text-blue-400 border-blue-400' : 'text-gray-400 border-transparent hover:text-gray-200'"
                        class="flex-1 pb-2 border-b-2 font-medium transition-colors">
                        {{ t('auth.magic_login') }}
                    </button>
                </div>

                <div v-if="loginMode === 'password'">
                    <div class="rounded-md shadow-sm -space-y-px">
                        <div class="mb-4">
                            <label for="email-address" class="block text-sm font-medium text-gray-300 mb-1">{{
                                t('auth.email') }}</label>
                            <input id="email-address" name="email" type="email" autocomplete="email" required
                                v-model="email"
                                class="appearance-none relative block w-full px-3 py-3 border border-gray-600 placeholder-gray-500 text-white bg-gray-900/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 focus:z-10 sm:text-sm transition-all"
                                :placeholder="t('auth.email_placeholder')" />
                        </div>
                        <div>
                            <PasswordInput id="password" name="password" v-model="password" :label="t('auth.password')"
                                :placeholder="t('auth.password_placeholder')" autocomplete="current-password"
                                required />
                        </div>
                    </div>

                    <div class="flex items-center justify-end mt-2">
                        <router-link to="/forgot-password"
                            class="text-xs font-medium text-purple-400 hover:text-purple-300">
                            {{ t('auth.forgot_password') }}
                        </router-link>
                    </div>
                </div>

                <div v-if="loginMode === 'magic'" class="space-y-4">
                    <p class="text-sm text-gray-400 text-center">{{ t('auth.magic_login_desc') }}</p>
                    <div>
                        <label for="magic-email" class="block text-sm font-medium text-gray-300 mb-1">{{
                            t('auth.email') }}</label>
                        <input id="magic-email" name="email" type="email" autocomplete="email" required v-model="email"
                            class="appearance-none relative block w-full px-3 py-3 border border-gray-600 placeholder-gray-500 text-white bg-gray-900/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm transition-all"
                            :placeholder="t('auth.email_placeholder')" />
                    </div>
                </div>

                <div v-if="error" class="rounded-md bg-red-900/50 border border-red-500/50 p-4">
                    <div class="flex">
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-red-200">{{ error }}</h3>
                        </div>
                    </div>
                </div>

                <div v-if="successMessage" class="rounded-md bg-green-900/50 border border-green-500/50 p-4">
                    <div class="flex">
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-green-200">{{ successMessage }}</h3>
                        </div>
                    </div>
                </div>

                <div>
                    <button type="submit" :disabled="loading"
                        :class="loginMode === 'magic' ? 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500' : 'bg-purple-600 hover:bg-purple-700 focus:ring-purple-500'"
                        class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02]">
                        <span v-if="loading" class="absolute left-0 inset-y-0 flex items-center pl-3">
                            <svg class="animate-spin h-5 w-5 text-white opacity-70" xmlns="http://www.w3.org/2000/svg"
                                fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                    stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                                </path>
                            </svg>
                        </span>
                        {{ loading ? t('common.loading') : (loginMode === 'magic' ? t('auth.send_magic_link') :
                        t('auth.sign_in')) }}
                    </button>
                </div>
            </form>
        </div>
    </div>
</template>

<script setup lang="ts">
import PasswordInput from '@/components/common/PasswordInput.vue'
import { useUserStore } from '@/stores/user'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const email = ref('')
const password = ref('')
const error = ref('')
const successMessage = ref('')
const loading = ref(false)
const loginMode = ref<'password' | 'magic'>('password')

import api from '@/services/api'; // Make sure to import api

const handleLogin = async () => {
    loading.value = true
    error.value = ''
    successMessage.value = ''

    try {
        if (loginMode.value === 'password') {
            const success = await userStore.login(email.value, password.value)
            if (success) {
                const redirect = route.query.redirect as string || '/'
                router.push(redirect)
            } else {
                error.value = t('auth.invalid_credentials')
            }
        } else {
            // Magic Login
            await api.requestMagicLink(email.value)
            successMessage.value = t('auth.magic_link_sent')
        }
    } catch (e: any) {
        if (loginMode.value === 'password') {
            error.value = e.response?.data?.detail || t('auth.login_failed')
        } else {
            // For magic link, we don't necessarily want to expose if error meant user not found, 
            // but api usually returns 200 anyway for safety. If error happens:
            error.value = t('auth.generic_error')
        }
    } finally {
        loading.value = false
    }
}
</script>
