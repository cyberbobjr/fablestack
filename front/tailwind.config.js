/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'fantasy-dark': 'var(--color-fantasy-dark)',
                'fantasy-accent': 'var(--color-fantasy-accent)',
                'fantasy-secondary': 'var(--color-fantasy-secondary)',
                'fantasy-text': 'var(--color-fantasy-text)',
                'fantasy-gold': 'var(--color-fantasy-gold)',
                'fantasy-silver': 'var(--color-fantasy-silver)',
                'fantasy-muted': 'var(--color-fantasy-muted)',
                'fantasy-hover': 'var(--color-fantasy-hover)',
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                serif: ['Inter', 'sans-serif'],
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
