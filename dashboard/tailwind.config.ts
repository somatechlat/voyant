import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: ["class"],
    content: [
        "./index.html",
        "./src/**/*.{ts,js,html}",
    ],
    theme: {
        extend: {
            colors: {
                brand: "#FF4D00",
                ink: "#050505",
                surface: "#f5f5f5",
                card: "#ffffff",
                "card-hover": "#FF4D00",
                success: "#22c55e",
                warning: "#f59e0b",
                danger: "#ef4444",
                info: "#3b82f6",
            },
            fontFamily: {
                sans: ["Inter", "system-ui", "sans-serif"],
                display: ["Geist", "Inter", "system-ui", "sans-serif"],
                mono: ["JetBrains Mono", "SF Mono", "monospace"],
            },
        },
    },
    plugins: [],
};

export default config;
