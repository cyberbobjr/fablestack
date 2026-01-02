export const getParsedArgs = (args: any) => {
    if (typeof args === 'string') {
        try {
            return JSON.parse(args)
        } catch (e) {
            return {}
        }
    }
    return args || {}
}

export const isSuccess = (content: any) => {
    if (!content) return false
    if (typeof content === 'object') {
        if ('success' in content) {
            return content.success
        }
        // Fallback: if no success boolean, check for error key
        if ('error' in content) {
            return false
        }
        // If neither, assume success if it's a non-empty object
        return true
    }
    return false
}

export const getRollValue = (content: any) => {
    if (content && typeof content === 'object' && 'roll' in content) {
        return content.roll
    }
    return '-'
}

export const getTargetValue = (content: any) => {
    if (content && typeof content === 'object' && 'target' in content) {
        return content.target
    }
    return '-'
}
