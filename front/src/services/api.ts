import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { getApiUrl } from '../config'

// Define interfaces for API responses
export interface ActiveSession {
    session_id: string
    scenario_id: string
    scenario_name: string
    character_id: string
    character_name: string
}

export interface ActiveSessionsResponse {
    sessions: ActiveSession[]
}


export interface ChoiceData {
    id: string
    label: string
    skill_check?: string | null
    difficulty?: "favorable" | "normal" | "unfavorable"
}

export interface PlayerInput {
    input_mode: "text" | "choice"
    text_content: string
    choice_data?: ChoiceData | null
    hidden?: boolean
}

export interface TimelineEvent {
    type: "USER_INPUT" | "SYSTEM_LOG" | "NARRATIVE" | "CHOICE" | "SKILL_CHECK" | "COMBAT_ATTACK" | "COMBAT_DAMAGE" | "COMBAT_INFO" | "COMBAT_TURN" | "ITEM_ADDED" | "ITEM_REMOVED" | "ITEM_CRAFTED" | "CURRENCY_CHANGE"
    timestamp: string
    content: any
    icon?: string | null
    metadata?: Record<string, any> | null
}

export interface Message {
    parts: any[] // Legacy / Fallback
    kind: string
}


export interface StartScenarioRequest {
    scenario_name: string
    character_id: string
}

export interface StartScenarioResponse {
    session_id: string
    scenario_name: string
    character_id: string
    message: string
    llm_response: string
}

export interface PlayScenarioRequest {
    session_id: string
    input: PlayerInput
}

export interface PlayScenarioResponse {
    session_id: string
    response: TimelineEvent[]
}
// ... (existing code)

export interface RestorePoint {
    index: number
    timestamp: string
    preview: string
}

export interface RestorePointsResponse {
    restore_points: RestorePoint[]
}

export interface RestoreHistoryResponse {
    message: string
    restored_to_index: number
    remaining_messages_count: number
}

export interface Character {
    id: string
    name: string
    race: string
    culture: string
    level: number
    status: string
    stats: Record<string, number>
    skills: Record<string, Record<string, number>>
    combat_stats: {
        max_hit_points: number
        current_hit_points: number
        max_mana_points: number
        current_mana_points: number
        armor_class: number
        attack_bonus: number
    }
    equipment: {
        weapons: any[]
        armor: any[]
        accessories: any[]
        consumables: any[]
        inventory?: any[]
        gold: number
        silver: number
        copper: number
        [key: string]: any
    }
    portrait_url?: string
    description_localized?: string
    physical_description_localized?: string
    [key: string]: any
}

export interface CharacterListResponse {
    characters: Character[]
}

export interface CharacterResponse {
    character: Character
    status: string
}

export interface Scenario {
    id: string
    title: string
    name: string
    status: string
    session_id?: string | null
    is_played: boolean
}

export interface ScenarioListResponse {
    scenarios: Scenario[]
}
// ...
// In methods around line 324

export interface Culture {
    id: string
    name: string
    description?: string | null
    skill_bonuses?: Record<string, number> | null
    characteristic_bonuses?: Record<string, number> | null
    free_skill_points?: number | null
    traits?: string | null
    special_traits?: Record<string, any> | null
}

export interface Race {
    id: string
    name: string
    description: string
    characteristic_bonuses?: Record<string, number>
    special_abilities?: any[]
    base_languages?: string[]
    optional_languages?: string[]
    cultures: Culture[]
    is_playable: boolean
    is_combatant: boolean
    default_equipment?: any[]
    [key: string]: any
}

export interface StatsResponse {
    stats: Record<string, { name: string;[key: string]: any }>
    [key: string]: any
}

const api: AxiosInstance = axios.create({
    baseURL: getApiUrl(),
    headers: {
        'Content-Type': 'application/json'
    }
})

// Request interceptor for API calls
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token')
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor for API calls
api.interceptors.response.use(
    (response) => {
        return response
    },
    async (error) => {
        if (error.response && error.response.status === 401) {
            // clear token
            localStorage.removeItem('token')
            // redirect to login
            if (!window.location.pathname.includes('/login')) {
                window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname)
            }
        }
        return Promise.reject(error)
    }
)

export default {
    // Auth
    login(data: FormData): Promise<AxiosResponse<{ access_token: string; token_type: string }>> {
        return api.post('/auth/token', data, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
    },
    register(data: any): Promise<AxiosResponse<any>> {
        return api.post('/auth/register', data)
    },
    forgotPassword(email: string): Promise<AxiosResponse<any>> {
        return api.post('/auth/forgot-password', { email })
    },
    resetPassword(token: string, newPassword: string): Promise<AxiosResponse<any>> {
        return api.post('/auth/reset-password', { token, new_password: newPassword })
    },
    requestMagicLink(email: string): Promise<AxiosResponse<any>> {
        return api.post('/auth/magic-login-request', { email })
    },
    verifyMagicLink(token: string): Promise<AxiosResponse<{ access_token: string; token_type: string }>> {
        return api.post('/auth/magic-login-verify', { token })
    },
    getProfile(): Promise<AxiosResponse<any>> {
        return api.get('/user/me')
    },
    // Admin
    getUsers(): Promise<AxiosResponse<any[]>> {
        return api.get('/users/')
    },
    adminUpdateUser(userId: string, data: any): Promise<AxiosResponse<any>> {
        return api.put(`/users/${userId}`, data)
    },
    deleteUser(userId: string): Promise<AxiosResponse<boolean>> {
        return api.delete(`/users/${userId}`)
    },

    // Sessions
    getActiveSessions(): Promise<AxiosResponse<ActiveSessionsResponse>> {
        return api.get('/gamesession/sessions')
    },
    playScenario(payload: PlayScenarioRequest, sessionId: string | null = null): Promise<AxiosResponse<PlayScenarioResponse>> {
        const config: AxiosRequestConfig = {}
        if (sessionId) {
            config.params = { session_id: sessionId }
        }
        return api.post('/gamesession/play', payload, config)
    },
    startScenario(payload: StartScenarioRequest): Promise<AxiosResponse<StartScenarioResponse>> {
        return api.post('/gamesession/start', payload)
    },
    async playScenarioStream(payload: PlayScenarioRequest): Promise<ReadableStreamDefaultReader<Uint8Array>> {
        const response = await fetch(`${getApiUrl()}/gamesession/play-stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }

        if (!response.body) {
            throw new Error('Response body is null')
        }

        return response.body.getReader()
    },
    getHistory(sessionId: string): Promise<AxiosResponse<{ history: any[] }>> {
        return api.get(`/gamesession/history/${sessionId}`)
    },
    getRestorePoints(sessionId: string): Promise<AxiosResponse<RestorePointsResponse>> {
        return api.get(`/gamesession/history/${sessionId}/restore-points`)
    },
    async restoreHistory(sessionId: string, timestamp: string): Promise<void> {
        await api.post(`/gamesession/history/${sessionId}/restore`, { timestamp })
    },

    // Characters
    getCharacters(): Promise<AxiosResponse<Character[]>> {
        return api.get('/characters/')
    },
    getCharacter(id: string): Promise<AxiosResponse<CharacterResponse>> {
        return api.get(`/characters/${id}`)
    },
    deleteCharacter(id: string): Promise<AxiosResponse<void>> {
        return api.delete(`/characters/${id}`)
    },
    createCharacter(character: any): Promise<AxiosResponse<any>> {
        return api.post('/creation/create', character)
    },
    updateCharacter(character: any): Promise<AxiosResponse<any>> {
        return api.post('/creation/update', character)
    },
    createRandomCharacter(): Promise<AxiosResponse<any>> {
        return api.post('/creation/random')
    },
    generateCharacterDetails(raceId: string, cultureId: string, sex: string): Promise<AxiosResponse<any>> {
        return api.post('/creation/generate-details', { race_id: raceId, culture_id: cultureId, sex })
    },
    regeneratePortrait(id: string): Promise<AxiosResponse<CharacterResponse>> {
        return api.post(`/characters/${id}/portrait`)
    },

    // Scenarios
    getScenarios(): Promise<AxiosResponse<ScenarioListResponse>> {
        return api.get('/scenarios/')
    },
    createScenario(data: { description: string }): Promise<AxiosResponse<any>> {
        return api.post('/scenarios/', data)
    },
    getScenario(filename: string): Promise<AxiosResponse<string>> {
        return api.get(`/scenarios/${filename}`)
    },
    updateScenario(filename: string, content: string): Promise<AxiosResponse<Scenario>> {
        return api.put(`/scenarios/${filename}`, content, {
            headers: { 'Content-Type': 'text/plain' }
        })
    },
    deleteScenario(filename: string): Promise<AxiosResponse<void>> {
        return api.delete(`/scenarios/${filename}`)
    },


    // Creation Data
    getRaces(): Promise<AxiosResponse<Race[]>> {
        return api.get('/creation/races')
    },
    getSkills(): Promise<AxiosResponse<any>> {
        return api.get('/creation/skills')
    },
    getStats(): Promise<AxiosResponse<StatsResponse>> {
        return api.get('/creation/stats')
    },
    getEquipment(): Promise<AxiosResponse<any>> {
        return api.get('/creation/equipment')
    },
    getTranslations(language: string): Promise<AxiosResponse<{ translations: Record<string, any> }>> {
        return api.get(`/translation/${language}`)
    },
    getSexBonuses(): Promise<AxiosResponse<Record<string, any>>> {
        return api.get('/creation/rules/sex_bonuses')
    },
    getStatsCreationRules(): Promise<AxiosResponse<any>> {
        return api.get('/creation/rules/stats_creation')
    },


    // Preferences
    async getPreferences(): Promise<AxiosResponse<{ language: string; theme?: string; font_size?: string }>> {
        return api.get('/user/preference')
    },

    async deleteSession(sessionId: string): Promise<void> {
        await api.delete(`/gamesession/${sessionId}`)
    },

    updatePreferences(preferences: { language: string; theme?: string }): Promise<AxiosResponse<any>> {
        return api.put('/user/preference', preferences)
    }
}
