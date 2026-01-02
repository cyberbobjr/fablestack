import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../services/api'

export interface UserPreferences {
    language: string
    theme: 'light' | 'dark'
    font_size: 'small' | 'medium' | 'large' | 'xlarge'
}

export const useUserStore = defineStore('user', () => {
    const preferences = ref<UserPreferences>({
        language: 'English',
        theme: 'dark',
        font_size: 'medium'
    })

    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<any | null>(null)
    const isAuthenticated = ref(!!token.value)

    const loading = ref(false)
    const { locale } = useI18n()

    const applyTheme = () => {
        const html = document.documentElement
        if (preferences.value.theme === 'dark') {
            html.classList.remove('light-theme')
            localStorage.setItem('theme', 'dark')
        } else {
            html.classList.add('light-theme')
            localStorage.setItem('theme', 'light')
        }
    }

    const fetchPreferences = async () => {
        loading.value = true
        try {
            const res = await api.getPreferences()
            if (res.data) {
                preferences.value = {
                    language: res.data.language || 'English',
                    theme: (res.data.theme as 'light' | 'dark') || 'dark',
                    font_size: res.data.font_size || 'medium'
                }

                // Sync locale
                const targetLocale = preferences.value.language === 'French' ? 'fr' : 'en'
                if (locale.value !== targetLocale) {
                    locale.value = targetLocale
                }

                applyTheme()
            }
        } catch (err) {
            console.error('Failed to fetch preferences', err)
        } finally {
            loading.value = false
        }
    }

    const updatePreferences = async (newPrefs: Partial<UserPreferences>) => {
        loading.value = true
        try {
            // Optimistic update
            preferences.value = { ...preferences.value, ...newPrefs }
            applyTheme()

            // Sync locale if language changed
            if (newPrefs.language) {
                const targetLocale = newPrefs.language === 'French' ? 'fr' : 'en'
                locale.value = targetLocale
            }

            await api.updatePreferences(preferences.value)
        } catch (err) {
            console.error('Failed to update preferences', err)
            // Revert on failure could be implemented here
        } finally {
            loading.value = false
        }
    }

    const login = async (email: string, password: string): Promise<boolean> => {
        loading.value = true
        try {
            const formData = new FormData()
            formData.append('username', email)
            formData.append('password', password)

            const res = await api.login(formData)
            if (res.data.access_token) {
                setToken(res.data.access_token)
                await fetchProfile()
                return true
            }
            return false
        } catch (err) {
            console.error('Login failed', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    const register = async (email: string, password: string, fullName: string): Promise<boolean> => {
        loading.value = true
        try {
            const res = await api.register({ email, password, full_name: fullName })
            if (res.data) {
                // Auto login after register
                return await login(email, password)
            }
            return false
        } catch (err) {
            console.error('Registration failed', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    const logout = () => {
        token.value = null
        user.value = null
        isAuthenticated.value = false
        localStorage.removeItem('token')
        // We could redirect here or let the caller decide
    }

    const fetchProfile = async () => {
        if (!token.value) return
        try {
            const res = await api.getProfile()
            user.value = res.data
        } catch (err) {
            console.error('Failed to fetch profile', err)
            // If 401, logout? handled by interceptor ideally
        }
    }

    // Admin Actions
    const fetchUsers = async () => {
        try {
            const res = await api.getUsers()
            return res.data
        } catch (err) {
            console.error('Failed to fetch users', err)
            throw err
        }
    }

    const deleteUser = async (userId: string) => {
        try {
            await api.deleteUser(userId)
            return true
        } catch (err) {
            console.error('Failed to delete user', err)
            throw err
        }
    }

    const updateAdminUser = async (userId: string, data: any) => {
        try {
            await api.adminUpdateUser(userId, data)
            return true
        } catch (err) {
            console.error('Failed to update user', err)
            throw err
        }
    }

    const setToken = (newToken: string) => {
        token.value = newToken
        isAuthenticated.value = true
        localStorage.setItem('token', newToken)
    }

    // Attempt to hydrate user logic if token exists
    if (token.value) {
        fetchProfile()
    }

    return {
        preferences,
        loading,
        token,
        user,
        isAuthenticated,
        login,
        register,
        logout,
        fetchPreferences,
        updatePreferences,
        applyTheme,
        fetchProfile,
        fetchUsers,
        deleteUser,
        updateAdminUser,
        setToken
    }
})
