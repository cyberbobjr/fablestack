/**
 * Application configuration
 * Centralizes access to environment variables
 */

/**
 * Get the API base URL from environment variables
 * Falls back to localhost:8001 for development
 */
export const getApiBaseUrl = (): string => {
    return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'
}

/**
 * Get the full API URL (with /api suffix)
 */
export const getApiUrl = (): string => {
    return `${getApiBaseUrl()}/api`
}
