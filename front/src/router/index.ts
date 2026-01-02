import { useUserStore } from '@/stores/user'
import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/auth/LoginView.vue'
import RegisterView from '../views/auth/RegisterView.vue'
import CreateCharacterView from '../views/CreateCharacterView.vue'
import GameView from '../views/GameView.vue'
import HomeView from '../views/HomeView.vue'
import NewGameView from '../views/NewGameView.vue'
import ProfileView from '../views/ProfileView.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/login',
            name: 'login',
            component: LoginView,
            meta: { guest: true }
        },
        {
            path: '/register',
            name: 'register',
            component: RegisterView,
            meta: { guest: true }
        },
        {
            path: '/forgot-password',
            name: 'forgot-password',
            component: () => import('../views/auth/ForgotPasswordView.vue'),
            meta: { guest: true }
        },
        {
            path: '/reset-password',
            name: 'reset-password',
            component: () => import('../views/auth/ResetPasswordView.vue'),
            meta: { guest: true }
        },
        {
            path: '/magic-login',
            name: 'magic-login',
            component: () => import('../views/auth/MagicLoginView.vue'),
            meta: { guest: true }
        },
        {
            path: '/profile',
            name: 'profile',
            component: ProfileView,
            meta: { requiresAuth: true }
        },
        {
            path: '/admin',
            name: 'admin',
            component: () => import('../views/admin/AdminDashboard.vue'),
            meta: { requiresAuth: true, adminOnly: true }
        },
        {
            path: '/admin/scenarios/:filename/edit',
            name: 'admin-scenario-edit',
            component: () => import('../views/admin/EditScenarioView.vue'),
            meta: { requiresAuth: true, adminOnly: true }
        },
        {
            path: '/admin/scenarios/:filename/preview',
            name: 'admin-scenario-preview',
            component: () => import('../views/admin/ScenarioPreviewView.vue'),
            meta: { requiresAuth: true, adminOnly: true }
        },
        {
            path: '/',
            name: 'home',
            component: HomeView,
            meta: { requiresAuth: true }
        },
        {
            path: '/create-character',
            name: 'create-character',
            component: CreateCharacterView,
            meta: { requiresAuth: true }
        },
        {
            path: '/edit-character/:id',
            name: 'edit-character',
            component: CreateCharacterView,
            meta: { requiresAuth: true }
        },
        {
            path: '/new-game',
            name: 'new-game',
            component: NewGameView,
            meta: { requiresAuth: true }
        },
        {
            path: '/game/:sessionId',
            name: 'game',
            component: GameView,
            props: true,
            meta: { requiresAuth: true }
        },
        {
            path: '/characters',
            name: 'characters',
            component: () => import('../views/CharactersView.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/characters/:id',
            name: 'character-sheet',
            component: () => import('../views/CharacterSheetView.vue'),
            meta: { requiresAuth: true }
        }
    ]
})

router.beforeEach(async (to, from, next) => {
    const isAuthenticated = !!localStorage.getItem('token')

    if (to.matched.some(record => record.meta.requiresAuth)) {
        if (!isAuthenticated) {
            next({
                path: '/login',
                query: { redirect: to.fullPath }
            })
            return
        }

        // Check for admin role
        if (to.matched.some(record => record.meta.adminOnly)) {
            const userStore = useUserStore()

            if (!userStore.user) {
                await userStore.fetchProfile()
            }

            if (userStore.user?.role !== 'admin') {
                next({ path: '/' })
                return
            }
        }

        next()
    } else if (to.matched.some(record => record.meta.guest)) {
        if (isAuthenticated) {
            next({ path: '/' })
        } else {
            next()
        }
    } else {
        next()
    }
})

export default router
