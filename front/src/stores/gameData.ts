import { defineStore } from 'pinia'
import api, { type Race } from '../services/api'

export interface EquipmentItem {
    id: string
    name: string
    category: string
    cost: number
    weight: number
    description: string
    [key: string]: any
}

interface GameDataState {
    skills: Record<string, any>
    stats: Record<string, any>
    translations: Record<string, any>
    races: Race[]
    equipment: EquipmentItem[]
    loading: boolean
    error: string | null
}

export const useGameDataStore = defineStore('gameData', {
    state: (): GameDataState => ({
        skills: {},
        stats: {},
        translations: {},
        races: [],
        equipment: [],
        loading: false,
        error: null
    }),

    getters: {
        getItemById: (state) => (id: string) => {
            return state.equipment.find(item => item.id === id)
        }
    },

    actions: {
        async fetchAllData(language: string = 'fr') {
            this.loading = true
            this.error = null
            try {
                const [skillsRes, statsRes, translationsRes, equipmentRes, racesRes] = await Promise.all([
                    api.getSkills(),
                    api.getStats(),
                    api.getTranslations(language),
                    api.getEquipment(),
                    api.getRaces()
                ])

                this.skills = skillsRes.data
                this.stats = statsRes.data
                this.translations = translationsRes.data.translations
                this.races = racesRes.data

                // Flatten equipment data
                const eqData = equipmentRes.data
                this.equipment = [
                    ...(eqData.weapons || []),
                    ...(eqData.armor || []),
                    ...(eqData.accessories || []),
                    ...(eqData.consumables || []),
                    ...(eqData.general || [])
                ]
            } catch (error) {
                console.error('Error fetching game data:', error)
                this.error = 'Failed to load game data'
            } finally {
                this.loading = false
            }
        },

        translate(key: string, category?: string): string {
            if (!this.translations) return key

            const lowerKey = key.toLowerCase()

            // Handle equipment legacy mapping
            if (category === 'equipment' && this.translations['equipment_details'] && this.translations['equipment_details'][lowerKey]) {
                return this.translations['equipment_details'][lowerKey].name
            }

            if (category && this.translations[category] && this.translations[category][lowerKey]) {
                const val = this.translations[category][lowerKey]
                if (typeof val === 'object' && val.name) return val.name
                return val
            }

            // Fallback search across all categories
            for (const cat in this.translations) {
                if (this.translations[cat][lowerKey]) {
                    const val = this.translations[cat][lowerKey]
                    if (typeof val === 'object' && val.name) return val.name
                    return val
                }
            }

            return key
        },

        getEquipmentDetails(key: string): { name: string, description: string } | null {
            if (!this.translations || !this.translations['equipment_details']) return null

            const lowerKey = key.toLowerCase()
            return this.translations['equipment_details'][lowerKey] || null
        }
    }
})
