<template>
    <div class="container mx-auto px-4 py-8">
        <div class="mb-8 flex justify-between items-center">
            <h1 class="text-3xl font-bold text-fantasy-gold">{{ t('auth.admin_dashboard') }}</h1>
            <h1 class="text-3xl font-bold text-fantasy-gold">{{ t('auth.admin_dashboard') }}</h1>
        </div>

        <!-- Tabs -->
        <div class="flex space-x-1 mb-6 bg-gray-900/50 p-1 rounded-lg inline-flex">
            <button @click="activeTab = 'users'"
                :class="['px-6 py-2 rounded-md font-bold transition-all', activeTab === 'users' ? 'bg-fantasy-accent text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-gray-800']">
                {{ t('admin.users') }}
            </button>
            <button @click="activeTab = 'scenarios'"
                :class="['px-6 py-2 rounded-md font-bold transition-all', activeTab === 'scenarios' ? 'bg-fantasy-accent text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-gray-800']">
                {{ t('admin.scenarios') }}
            </button>
        </div>

        <div v-if="activeTab === 'users'">
            <div v-if="loading" class="flex justify-center p-12">
                <svg class="animate-spin h-10 w-10 text-fantasy-accent" xmlns="http://www.w3.org/2000/svg" fill="none"
                    viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                    </path>
                </svg>
            </div>

            <div v-else class="bg-fantasy-secondary border border-gray-700 rounded-lg overflow-hidden shadow-xl">
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead
                            class="bg-gray-900/50 text-fantasy-gold uppercase text-sm font-bold border-b border-gray-700">
                            <tr>
                                <th class="px-6 py-4">{{ t('admin.name') }}</th>
                                <th class="px-6 py-4">{{ t('admin.email') }}</th>
                                <th class="px-6 py-4">{{ t('admin.role') }}</th>
                                <th class="px-6 py-4">{{ t('admin.status') }}</th>
                                <th class="px-6 py-4 text-right">{{ t('admin.actions') }}</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-700">
                            <tr v-for="user in users" :key="user.id" class="hover:bg-gray-800/30 transition-colors">
                                <td class="px-6 py-4">
                                    <div v-if="editingUser === user.id" class="flex items-center">
                                        <input v-model="editForm.full_name"
                                            class="bg-gray-900 border border-gray-600 rounded px-2 py-1 w-full text-white" />
                                    </div>
                                    <span v-else class="font-medium text-white">{{ user.full_name }}</span>
                                </td>
                                <td class="px-6 py-4 text-gray-300">
                                    <div v-if="editingUser === user.id">
                                        <input v-model="editForm.email"
                                            class="bg-gray-900 border border-gray-600 rounded px-2 py-1 w-full text-white" />
                                    </div>
                                    <span v-else>{{ user.email }}</span>
                                </td>
                                <td class="px-6 py-4">
                                    <div v-if="editingUser === user.id">
                                        <select v-model="editForm.role"
                                            class="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-white">
                                            <option value="user">USER</option>
                                            <option value="admin">ADMIN</option>
                                        </select>
                                    </div>
                                    <span v-else
                                        :class="user.role === 'admin' ? 'text-purple-400 font-bold' : 'text-blue-400'">
                                        {{ user.role.toUpperCase() }}
                                    </span>
                                </td>
                                <td class="px-6 py-4">
                                    <div v-if="editingUser === user.id">
                                        <select v-model="editForm.is_active"
                                            class="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-white">
                                            <option :value="true">{{ t('admin.active') }}</option>
                                            <option :value="false">{{ t('admin.inactive') }}</option>
                                        </select>
                                    </div>
                                    <span v-else class="inline-flex px-2 py-1 text-xs font-semibold rounded-full"
                                        :class="user.is_active ? 'bg-green-900/30 text-green-400 border border-green-900' : 'bg-red-900/30 text-red-400 border border-red-900'">
                                        {{ user.is_active ? t('admin.active') : t('admin.inactive') }}
                                    </span>
                                </td>
                                <td class="px-6 py-4 text-right space-x-2">
                                    <div v-if="editingUser === user.id">
                                        <button @click="saveEdit(user.id)"
                                            class="text-green-400 hover:text-green-300 mr-2">
                                            <Check :size="18" />
                                        </button>
                                        <button @click="cancelEdit" class="text-red-400 hover:text-red-300">
                                            <X :size="18" />
                                        </button>
                                    </div>
                                    <div v-else>
                                        <button @click="startEdit(user)"
                                            class="text-fantasy-accent hover:text-purple-400 mr-3"
                                            :title="t('admin.edit')">
                                            <Edit2 :size="18" />
                                        </button>
                                        <button @click="confirmDelete(user)" class="text-red-500 hover:text-red-400"
                                            :title="t('admin.delete')">
                                            <Trash2 :size="18" />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Delete Confirmation -->
            <ConfirmationModal :show="showDeleteModal" :title="t('admin.delete')" :message="t('admin.delete_confirm')"
                @confirm="handleDelete" @cancel="showDeleteModal = false" />
        </div>

        <!-- Scenarios Tab -->
        <div v-if="activeTab === 'scenarios'">
            <AdminScenariosView />
        </div>
    </div>
</template>

<script setup lang="ts">
import ConfirmationModal from '@/components/ConfirmationModal.vue'
import { useUserStore } from '@/stores/user'
import { Check, Edit2, Trash2, X } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import AdminScenariosView from './AdminScenariosView.vue'

const { t } = useI18n()
const userStore = useUserStore()

const route = useRoute()
const activeTab = ref((route.query.tab as string) || 'users')
const users = ref<any[]>([])
const loading = ref(true)
const editingUser = ref<string | null>(null)
const editForm = ref<any>({})
const showDeleteModal = ref(false)
const userToDelete = ref<string | null>(null)

const loadUsers = async () => {
    loading.value = true
    try {
        users.value = await userStore.fetchUsers()
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const startEdit = (user: any) => {
    editingUser.value = user.id
    editForm.value = { ...user }
}

const cancelEdit = () => {
    editingUser.value = null
    editForm.value = {}
}

const saveEdit = async (userId: string) => {
    try {
        await userStore.updateAdminUser(userId, editForm.value)
        editingUser.value = null
        await loadUsers()
    } catch (e) {
        console.error(e)
    }
}

const confirmDelete = (user: any) => {
    userToDelete.value = user.id
    showDeleteModal.value = true
}

const handleDelete = async () => {
    if (!userToDelete.value) return

    try {
        await userStore.deleteUser(userToDelete.value)
        showDeleteModal.value = false
        userToDelete.value = null
        await loadUsers()
    } catch (e) {
        console.error(e)
    }
}

onMounted(() => {
    loadUsers()
})
</script>
