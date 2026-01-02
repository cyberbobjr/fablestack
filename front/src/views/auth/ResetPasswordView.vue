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
                    {{ t('auth.new_password_placeholder') }}
                </p>
            </div>

            <form class="mt-8 space-y-6" @submit.prevent="handleSubmit">
                <div class="rounded-md shadow-sm space-y-4">
                    <div>
                        <PasswordInput id="password" name="password" v-model="password" :label="t('auth.new_password')"
                            :placeholder="t('auth.new_password_placeholder')" autocomplete="new-password" required
                            inputClass="focus:ring-purple-500 focus:border-purple-500" />

                        <!-- Reuse password rules display from RegisterView (could be extracted to component) -->
                        <div class="mt-2 p-3 bg-gray-800 rounded-lg border border-gray-700 text-xs text-left">
                            <ul class="space-y-1">
                                <li :class="rules.min ? 'text-green-400' : 'text-gray-500'"
                                    class="flex items-center gap-2 transition-colors">
                                    <CheckCircle v-if="rules.min" :size="12" />
                                    <Circle v-else :size="12" />
                                    {{ t('auth.password_rules.min_chars') }}
                                </li>
                                <li :class="rules.upper ? 'text-green-400' : 'text-gray-500'"
                                    class="flex items-center gap-2 transition-colors">
                                    <CheckCircle v-if="rules.upper" :size="12" />
                                    <Circle v-else :size="12" />
                                    {{ t('auth.password_rules.uppercase') }}
                                </li>
                                <li :class="rules.lower ? 'text-green-400' : 'text-gray-500'"
                                    class="flex items-center gap-2 transition-colors">
                                    <CheckCircle v-if="rules.lower" :size="12" />
                                    <Circle v-else :size="12" />
                                    {{ t('auth.password_rules.lowercase') }}
                                </li>
                                <li :class="rules.number ? 'text-green-400' : 'text-gray-500'"
                                    class="flex items-center gap-2 transition-colors">
                                    <CheckCircle v-if="rules.number" :size="12" />
                                    <Circle v-else :size="12" />
                                    {{ t('auth.password_rules.number') }}
                                </li>
                                <li :class="rules.special ? 'text-green-400' : 'text-gray-500'"
                                    class="flex items-center gap-2 transition-colors">
                                    <CheckCircle v-if="rules.special" :size="12" />
                                    <Circle v-else :size="12" />
                                    {{ t('auth.password_rules.special') }}
                                </li>
                            </ul>
                        </div>
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

                <div>
                    <button type="submit" :disabled="loading || message !== ''"
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
                        {{ loading ? t('common.loading') : t('auth.reset_password') }}
                    </button>

                    <div class="mt-4 text-center" v-if="message">
                        <router-link to="/login" class="text-sm font-medium text-purple-400 hover:text-purple-300">
                            {{ t('auth.back_to_login') }}
                        </router-link>
                    </div>
                </div>
            </form>
        </div>
    </div>
</template>

<script setup lang="ts">
import PasswordInput from '@/components/common/PasswordInput.vue';
import api from '@/services/api';
import { CheckCircle, Circle } from 'lucide-vue-next';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

const { t } = useI18n()
const route = useRoute()
const password = ref('')
const message = ref('')
const error = ref('')
const loading = ref(false)

const token = route.query.token as string

const rules = computed(() => ({
    min: password.value.length >= 8,
    upper: /[A-Z]/.test(password.value),
    lower: /[a-z]/.test(password.value),
    number: /\d/.test(password.value),
    special: /[\W_]/.test(password.value)
}))

const isPasswordValid = computed(() => {
    const r = rules.value
    return r.min && r.upper && r.lower && r.number && r.special
})

const handleSubmit = async () => {
    if (!isPasswordValid.value) {
        error.value = t('auth.password_requirements')
        return
    }

    loading.value = true
    message.value = ''
    error.value = ''

    try {
        await api.resetPassword(token, password.value)
        message.value = t('auth.password_reset_success')
    } catch (e: any) {
        error.value = e.response?.data?.detail || t('auth.reset_link_invalid')
    } finally {
        loading.value = false
    }
}
</script>
