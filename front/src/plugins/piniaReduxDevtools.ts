import { type PiniaPluginContext } from 'pinia'

export function piniaReduxDevtools({ store }: PiniaPluginContext) {
    // Check if we are in a browser environment and if Redux DevTools is available
    if (typeof window === 'undefined' || !(window as any).__REDUX_DEVTOOLS_EXTENSION__) {
        return
    }

    const devtools = (window as any).__REDUX_DEVTOOLS_EXTENSION__.connect({
        name: `Pinia: ${store.$id}`,
    })

    // Initialize with current state
    devtools.init(store.$state)

    // Subscribe to store changes
    store.$subscribe((mutation, state) => {
        // Send the mutation type and the new state to Redux DevTools
        // We try to format the action name nicely
        const actionName = mutation.type === 'direct'
            ? `[${store.$id}] mutation`
            : `[${store.$id}] ${mutation.type}`

        devtools.send({ type: actionName, payload: mutation }, state)
    })

    // Note: Time travel (receiving messages from devtools) is more complex 
    // and requires handling 'DISPATCH' messages to replace state.
    // For now, we only implement one-way logging.
}
