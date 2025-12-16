/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                display: ['Outfit', 'sans-serif'],
            },
            colors: {
                // Premium palette - "Ledgerix" inspired
                brand: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    900: '#0c4a6e',
                },
                slate: {
                    850: '#1e293b', // Rich dark for cards
                    900: '#0f172a', // Deep background
                },
                // Tasteful status colors
                live: {
                    DEFAULT: '#ef4444', // Red for live
                    glow: 'rgba(239, 68, 68, 0.5)',
                },
                money: {
                    DEFAULT: '#10b981', // Emerald for money
                }
            },
            animation: {
                'pulse-subtle': 'pulse-subtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'ping-slow': 'ping 3s cubic-bezier(0, 0, 0.2, 1) infinite',
            },
            keyframes: {
                'pulse-subtle': {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: .7 },
                }
            }
        },
    },
    plugins: [],
}
