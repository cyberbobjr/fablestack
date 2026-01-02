<template>
    <div class="relative">
        <label v-if="label" :for="id" class="block text-sm font-medium text-gray-300 mb-1">
            {{ label }}
        </label>
        <div class="relative">
            <input :id="id" :name="name" :type="showPassword ? 'text' : 'password'" :value="modelValue"
                @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)" :class="[
                    'appearance-none block w-full px-3 py-3 border border-gray-600 placeholder-gray-500 text-white bg-gray-900/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 focus:z-10 sm:text-sm transition-all',
                    inputClass
                ]" :placeholder="placeholder" :required="required" :autocomplete="autocomplete" />
            <button type="button" @click="togglePasswordVisibility"
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-200 focus:outline-none"
                tabindex="-1">
                <Eye v-if="!showPassword" :size="20" />
                <EyeOff v-else :size="20" />
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { Eye, EyeOff } from 'lucide-vue-next';
import { ref } from 'vue';

defineProps({
    modelValue: {
        type: String,
        required: true
    },
    label: {
        type: String,
        default: ''
    },
    id: {
        type: String,
        required: true
    },
    name: {
        type: String,
        required: true
    },
    placeholder: {
        type: String,
        default: ''
    },
    required: {
        type: Boolean,
        default: false
    },
    autocomplete: {
        type: String,
        default: 'off'
    },
    inputClass: {
        type: String,
        default: ''
    }
});

defineEmits(['update:modelValue']);

const showPassword = ref(false);

const togglePasswordVisibility = () => {
    showPassword.value = !showPassword.value;
};
</script>
