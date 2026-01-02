import { defineStore } from 'pinia'
import api from '../services/api'

export interface ScenarioStatus {
    id: string
    title: string
    name: string
    status: string
    is_played: boolean
    session_id?: string | null
}

export const useScenarioStore = defineStore('scenario', {
    state: () => ({
        scenarios: [] as ScenarioStatus[],
        loading: false,
        error: null as string | null
    }),

    actions: {
        async fetchScenarios() {
            this.loading = true
            this.error = null
            try {
                const response = await api.getScenarios()
                this.scenarios = response.data.scenarios || []
            } catch (e: any) {
                this.error = e.message || 'Failed to fetch scenarios'
                console.error('Error fetching scenarios:', e)
            } finally {
                this.loading = false
            }
        },

        async createScenario(description: string) {
            this.loading = true
            this.error = null
            try {
                const response = await api.createScenario({ description })
                // Add the new scenario to the list or re-fetch
                // The status will be 'creating'
                this.scenarios.push(response.data)

                // Start Polling
                this.pollForCreation(response.data.name)

                return response.data
            } catch (e: any) {
                this.error = e.message || 'Failed to create scenario'
                throw e
            } finally {
                this.loading = false
            }
        },

        async pollForCreation(filename: string) {
            const maxAttempts = 24; // 2 minutes (24 * 5s)
            let attempts = 0;

            const interval = setInterval(async () => {
                attempts++;
                try {
                    // Re-fetch list to check status (or check specific if endpoint existed)
                    // Currently we rely on list_scenarios which reads all files.
                    // Or we can try to fetch details? But getScenarioDetails throws 404 if weird state?
                    // Let's use fetchScenarios but maybe optimize? No, simplest is re-fetch.
                    await this.fetchScenarios()

                    const scenario = this.scenarios.find(s => s.name === filename)
                    if (scenario && scenario.status !== 'creating') {
                        // Done or failed
                        clearInterval(interval)
                    }
                } catch (e) {
                    console.error("Polling error", e)
                }

                if (attempts >= maxAttempts) {
                    clearInterval(interval)
                }
            }, 5000)
        },

        async updateScenario(filename: string, content: string) {
            this.loading = true
            this.error = null
            try {
                const response = await api.updateScenario(filename, content)
                // Update local state if necessary or re-fetch
                const index = this.scenarios.findIndex(s => s.name === filename)
                if (index !== -1) {
                    // Update only relevant fields if response implies partial update
                    // or just replace.
                    // Ideally response returns updated ScenarioStatus
                    this.scenarios[index] = { ...this.scenarios[index], ...response.data }
                }
                return response.data
            } catch (e: any) {
                this.error = e.message || 'Failed to update scenario'
                throw e
            } finally {
                this.loading = false
            }
        },

        async deleteScenario(filename: string) {
            this.loading = true
            this.error = null
            try {
                await api.deleteScenario(filename)
                this.scenarios = this.scenarios.filter(s => s.name !== filename)
            } catch (e: any) {
                this.error = e.message || 'Failed to delete scenario'
                throw e
            } finally {
                this.loading = false
            }
        },

        async fetchScenarioContent(filename: string) {
            this.loading = true
            this.error = null
            try {
                const response = await api.getScenario(filename)
                return response.data
            } catch (e: any) {
                this.error = e.message || 'Failed to fetch scenario content'
                throw e
            } finally {
                this.loading = false
            }
        },


    }
})
