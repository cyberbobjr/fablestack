/**
 * API Configuration
 * 
 * The API base URL is configured via environment variables using Vite's env system.
 * Set VITE_API_BASE_URL in your .env file or deployment environment.
 * 
 * Example .env file:
 *   VITE_API_BASE_URL=http://localhost:8001
 * 
 * For production:
 *   VITE_API_BASE_URL=https://api.yourproduction.com
 * 
 * The default fallback is http://localhost:8001 for local development.
 */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'
export const API_URL: string = `${API_BASE_URL}/api`

export const HIDDEN_TOOLS = [
    'search_enemy_archetype_tool',
    'retrieve_context',
    'search_knowledge_base'
]

export const VISIBLE_TOOLS = [
    'skill_check_with_character',
    'combat_attack',
    'inventory_add',
    'inventory_remove',
    'update_character_stats'
]

export const isToolVisible = (toolName?: string) => {
    if (!toolName) return false
    if (HIDDEN_TOOLS.includes(toolName)) return false
    // By default show everything else, or restrict to VISIBLE_TOOLS if strict mode is needed
    return true
}
