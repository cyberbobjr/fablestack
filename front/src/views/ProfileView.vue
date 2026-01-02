<template>
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-2xl mx-auto bg-fantasy-secondary border border-gray-700 rounded-lg shadow-xl overflow-hidden">
            <!-- Header -->
            <div class="bg-gray-800/50 p-6 border-b border-gray-700 flex justify-between items-center">
                <h1 class="text-2xl font-bold text-fantasy-gold">{{ t('auth.profile') }}</h1>
                <button @click="handleLogout"
                    class="flex items-center gap-2 px-4 py-2 rounded bg-red-900/30 text-red-400 hover:bg-red-900/50 hover:text-red-300 transition-colors border border-red-900/50">
                    <LogOut :size="18" />
                    {{ t('auth.logout') }}
                </button>
            </div>

            <div class="p-6 space-y-8">
                <!-- User Info -->
                <div v-if="userStore.user"
                    class="flex items-center gap-6 p-4 bg-gray-900/30 rounded-lg border border-gray-700/50">
                    <div
                        class="w-16 h-16 rounded-full bg-fantasy-accent/20 flex items-center justify-center border-2 border-fantasy-accent/50 text-fantasy-accent font-bold text-2xl">
                        {{ userInitials }}
                    </div>
                    <div>
                        <h2 class="text-xl font-bold text-white">{{ userStore.user.full_name }}</h2>
                        <p class="text-gray-400">{{ userStore.user.email }}</p>
                        <span
                            class="inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium bg-fantasy-accent/20 text-fantasy-accent border border-fantasy-accent/30">
                            {{ userStore.user.role }}
                        </span>
                    </div>
                </div>

                <!-- Preferences Section -->
                <div class="space-y-6">
                    <h3 class="text-lg font-medium text-fantasy-gold border-b border-gray-700 pb-2">{{
                        t('auth.preferences') }}</h3>

                    <!-- Language -->
                    <div>
                        <label class="block text-sm font-medium text-fantasy-text mb-2">{{ t('ui.languages') }}</label>
                        <select :value="userStore.preferences.language"
                            @change="userStore.updatePreferences({ language: ($event.target as HTMLSelectElement).value })"
                            class="w-full bg-fantasy-dark border border-gray-600 rounded p-3 text-fantasy-text focus:border-fantasy-accent outline-none cursor-pointer transition-colors focus:ring-1 focus:ring-fantasy-accent">
                            <option value="English">English</option>
                            <option value="French">Français</option>
                        </select>
                    </div>

                    <!-- Theme -->
                    <div>
                        <label class="block text-sm font-medium text-fantasy-text mb-2">{{ t('auth.theme') }}</label>
                        <div class="flex gap-4">
                            <button @click="userStore.updatePreferences({ theme: 'dark' })"
                                class="flex-1 p-4 rounded-lg border transition-all flex items-center justify-center gap-3 cursor-pointer group"
                                :class="userStore.preferences.theme === 'dark' ? 'bg-fantasy-accent border-fantasy-accent text-white shadow-lg shadow-purple-900/20' : 'bg-fantasy-dark border-gray-600 text-fantasy-muted hover:border-gray-500 hover:bg-gray-800'">
                                <Moon :size="20" class="group-hover:scale-110 transition-transform" />
                                {{ t('auth.theme_dark') }}
                            </button>
                            <button @click="userStore.updatePreferences({ theme: 'light' })"
                                class="flex-1 p-4 rounded-lg border transition-all flex items-center justify-center gap-3 cursor-pointer group"
                                :class="userStore.preferences.theme === 'light' ? 'bg-fantasy-accent border-fantasy-accent text-white shadow-lg shadow-purple-900/20' : 'bg-fantasy-dark border-gray-600 text-fantasy-muted hover:border-gray-500 hover:bg-gray-800'">
                                <Sun :size="20" class="group-hover:scale-110 transition-transform" />
                                {{ t('auth.theme_light') }}
                            </button>
                        </div>
                    </div>

                    <!-- Font Size -->
                    <div>
                        <label class="block text-sm font-medium text-fantasy-text mb-2">{{ t('auth.font_size') }}</label>
                        <div class="grid grid-cols-2 gap-3">
                            <button v-for="size in fontSizes" :key="size.value"
                                @click="userStore.updatePreferences({ font_size: size.value as any })"
                                class="p-3 rounded-lg border transition-all flex items-center justify-center gap-2 cursor-pointer hover:bg-gray-800"
                                :class="userStore.preferences.font_size === size.value ? 'bg-fantasy-accent border-fantasy-accent text-white shadow-md' : 'bg-fantasy-dark border-gray-600 text-fantasy-muted hover:border-gray-500'">
                                <Type :size="16" />
                                <span :class="size.class">{{ size.label }}</span>
                            </button>
                        </div>
                    </div>

                    <!-- Change Password -->
                    <div class="pt-6 border-t border-gray-700">
                        <h3 class="text-lg font-medium text-fantasy-gold mb-4">{{ t('auth.change_password') }}</h3>
                        <form @submit.prevent="handleChangePassword" class="space-y-4">
                            <div>
                                <PasswordInput id="current-password" name="current-password" v-model="currentPassword"
                                    :label="t('auth.current_password')" :placeholder="t('auth.password_placeholder')"
                                    required />
                            </div>
                            <div>
                                <PasswordInput id="new-password" name="new-password" v-model="newPassword"
                                    :label="t('auth.new_password')" :placeholder="t('auth.new_password_placeholder')"
                                    required />
                            </div>
                            <div>
                                <PasswordInput id="confirm-password" name="confirm-password" v-model="confirmPassword"
                                    :label="t('auth.confirm_password')"
                                    :placeholder="t('auth.confirm_password_placeholder')" required />
                            </div>

                            <div v-if="passwordMessage" class="text-green-400 text-sm">{{ passwordMessage }}</div>
                            <div v-if="passwordError" class="text-red-400 text-sm">{{ passwordError }}</div>

                            <button type="submit" :disabled="loadingPassword"
                                class="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50">
                                {{ loadingPassword ? t('common.loading') : t('auth.save') }}
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>


<script setup lang="ts">
import PasswordInput from '@/components/common/PasswordInput.vue';
import api from '@/services/api';
import { useUserStore } from '@/stores/user';
import { LogOut, Moon, Sun, Type } from 'lucide-vue-next';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordMessage = ref('')
const passwordError = ref('')
const loadingPassword = ref(false)

const fontSizes = computed(() => [
    { value: 'small', label: t('auth.font_small'), class: 'text-sm' },
    { value: 'medium', label: t('auth.font_medium'), class: 'text-base' },
    { value: 'large', label: t('auth.font_large'), class: 'text-lg' },
    { value: 'xlarge', label: t('auth.font_xlarge'), class: 'text-xl' }
])

const userInitials = computed(() => {
    if (!userStore.user?.full_name) return '?'
    return userStore.user.full_name
        .split(' ')
        .map((n: string) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
})

const handleLogout = () => {
    userStore.logout()
    router.push('/login')
}

const handleChangePassword = async () => {
    if (newPassword.value !== confirmPassword.value) {
        passwordError.value = t('auth.passwords_do_not_match')
        return
    }

    loadingPassword.value = true
    passwordMessage.value = ''
    passwordError.value = ''

    try {
        await api.changePassword({
            current_password: currentPassword.value,
            new_password: newPassword.value
        })
        passwordMessage.value = t('auth.password_updated')
        currentPassword.value = ''
        newPassword.value = ''
        confirmPassword.value = ''
    } catch (e: any) {
        passwordError.value = e.response?.data?.detail || t('auth.password_change_error')
    } finally {
        loadingPassword.value = false
    }
}

onMounted(() => {
    userStore.fetchPreferences()
    if (!userStore.user) {
        userStore.fetchProfile()
    }
})
</script>
