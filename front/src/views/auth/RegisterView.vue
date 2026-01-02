<template>
    <div
        class="min-h-screen flex items-center justify-center bg-gray-900 px-4 py-12 sm:px-6 lg:px-8 relative overflow-hidden">
        <!-- Background Glow -->
        <div
            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-900/20 rounded-full blur-[120px] pointer-events-none">
        </div>

        <div
            class="max-w-md w-full space-y-8 relative z-10 bg-gray-800/50 backdrop-blur-xl p-8 rounded-2xl border border-gray-700/50 shadow-2xl">
            <div>
                <h2 class="mt-2 text-center text-3xl font-extrabold text-white tracking-tight">
                    {{ t('auth.register_title') }}
                </h2>
                <p class="mt-2 text-center text-sm text-gray-400">
                    {{ t('auth.already_have_account') }}
                    <router-link to="/login" class="font-medium text-blue-400 hover:text-blue-300 transition-colors">
                        {{ t('auth.sign_in_link') }}
                    </router-link>
                </p>
            </div>

            <form class="mt-8 space-y-6" @submit.prevent="handleRegister">
                <div class="rounded-md shadow-sm space-y-4">
                    <div>
                        <label for="full-name" class="block text-sm font-medium text-gray-300 mb-1">{{
                            t('auth.full_name') }}</label>
                        <input id="full-name" name="full_name" type="text" required v-model="fullName"
                            class="appearance-none relative block w-full px-3 py-3 border border-gray-600 placeholder-gray-500 text-white bg-gray-900/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm transition-all"
                            :placeholder="t('auth.full_name_placeholder')" />
                    </div>
                    <div>
                        <label for="email-address" class="block text-sm font-medium text-gray-300 mb-1">{{
                            t('auth.email') }}</label>
                        <input id="email-address" name="email" type="email" autocomplete="email" required
                            v-model="email"
                            class="appearance-none relative block w-full px-3 py-3 border border-gray-600 placeholder-gray-500 text-white bg-gray-900/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm transition-all"
                            :placeholder="t('auth.email_placeholder')" />
                    </div>
                    <div>
                        <PasswordInput id="password" name="password" v-model="password" :label="t('auth.password')"
                            :placeholder="t('auth.password_placeholder')" autocomplete="new-password" required
                            inputClass="focus:ring-blue-500 focus:border-blue-500" />
                        <!-- Password Strength Rules -->
                        <div class="mt-2 p-3 bg-gray-800 rounded-lg border border-gray-700 text-xs text-left">
                            <p class="font-medium text-gray-400 mb-2">{{ t('auth.password_rules.title') }}</p>
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
                    <div>
                        <PasswordInput id="confirm-password" name="confirm-password" v-model="confirmPassword"
                            :label="t('auth.confirm_password')" :placeholder="t('auth.confirm_password_placeholder')"
                            autocomplete="new-password" required
                            inputClass="focus:ring-blue-500 focus:border-blue-500" />
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
                    <button type="submit" :disabled="loading"
                        class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02]">
                        <span v-if="loading" class="absolute left-0 inset-y-0 flex items-center pl-3">
                            <svg class="animate-spin h-5 w-5 text-blue-300" xmlns="http://www.w3.org/2000/svg"
                                fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                    stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                                </path>
                            </svg>
                        </span>
                        {{ loading ? t('common.loading') : t('auth.sign_up') }}
                    </button>
                </div>
            </form>
        </div>
    </div>
</template>

<script setup lang="ts">
import PasswordInput from '@/components/common/PasswordInput.vue'
import { useUserStore } from '@/stores/user'
import { CheckCircle, Circle } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

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

const handleRegister = async () => {
    error.value = ''

    if (!isPasswordValid.value) {
        error.value = t('auth.password_requirements')
        return
    }

    if (password.value !== confirmPassword.value) {
        error.value = t('auth.passwords_do_not_match')
        return
    }

    loading.value = true

    try {
        const success = await userStore.register(email.value, password.value, fullName.value)
        if (success) {
            router.push('/')
        } else {
            error.value = t('auth.registration_failed')
        }
    } catch (e: any) {
        error.value = e.response?.data?.detail || t('auth.registration_failed')
    } finally {
        loading.value = false
    }
}
</script>
