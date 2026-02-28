import type { Config } from "tailwindcss";

/**
 * SOMA Universal Tailwind Config
 * Based on: SRS Style Guide (SA01-SRS-STYLE-2025-01 v2.0.0)
 * Standard: Clean Light Theme + Industrial Minimalism
 * Applies to: AgentVoiceBox, GPUBroker, Voyant
 */

const config: Config = {
    darkMode: ["class"], // Future dark mode support
    content: [
        "./index.html",
        "./src/**/*.{ts,js,html}",
    ],
    theme: {
        extend: {
            // ==========================================
            // TYPOGRAPHY (Geist Font Family)
            // ==========================================
            fontFamily: {
                sans: [
                    "Geist",
                    "-apple-system",
                    "BlinkMacSystemFont",
                    "Segoe UI",
                    "Roboto",
                    "sans-serif",
                ],
                mono: [
                    "Geist Mono",
                    "SF Mono",
                    "Monaco",
                    "Cascadia Code",
                    "monospace",
                ],
            },

            // ==========================================
            // COLORS: SaaS Kit Semantic Tokens
            // (SRS Style Guide Section 1.1 & 1.2)
            // ==========================================
            colors: {
                // Core Background & Surface
                "saas-page": "#f5f5f5",      // Global page background (Gray-100)
                "saas-card": "#ffffff",       // Cards, modals, inputs

                // Typography
                "saas-text-primary": "#1a1a1a",    // Headings, body text (Black-900)
                "saas-text-secondary": "#666666",  // Labels, metadata (Gray-600)

                // Accents & Actions
                "saas-accent": "#1a1a1a",     // Primary buttons, links (Black)
                "saas-border": "#e0e0e0",     // Dividers, card borders (Gray-300)

                // Status Indicators (SRS Section 1.2)
                "saas-success": "#22c55e",    // Green - valid, healthy
                "saas-warning": "#f59e0b",    // Amber - caution
                "saas-danger": "#ef4444",     // Red - error, delete
                "saas-info": "#3b82f6",       // Blue - neutral info

                // Glassmorphism Support
                "saas-glass-bg": "rgba(255, 255, 255, 0.9)",
                "saas-glass-border": "rgba(0, 0, 0, 0.1)",
            },

            // ==========================================
            // SPACING & LAYOUT
            // ==========================================
            spacing: {
                "sidebar-collapsed": "64px",
                "sidebar-expanded": "240px",
            },

            // ==========================================
            // BORDER RADIUS (Subtle, Industrial)
            // ==========================================
            borderRadius: {
                "saas": "8px",        // Standard cards, modals
                "saas-sm": "4px",     // Buttons, inputs
                "saas-lg": "12px",    // Large containers
            },

            // ==========================================
            // SHADOWS (Minimal Depth)
            // ==========================================
            boxShadow: {
                "saas-card": "0 1px 3px 0 rgb(0 0 0 / 0.05)",
                "saas-card-hover": "0 4px 6px -1px rgb(0 0 0 / 0.08)",
                "saas-modal": "0 8px 32px rgba(0, 0, 0, 0.1)",
            },

            // ==========================================
            // BACKDROP BLUR (Glassmorphism)
            // ==========================================
            backdropBlur: {
                "saas-glass": "8px",
                "saas-glass-heavy": "16px",
            },

            // ==========================================
            // ANIMATIONS (SRS Section 4.1)
            // ==========================================
            transitionDuration: {
                "saas-fast": "150ms",    // Hover, toggles
                "saas-modal": "200ms",   // Modal appear, dropdowns
                "saas-toast": "300ms",   // Notifications
            },

            transitionTimingFunction: {
                "saas": "cubic-bezier(0.4, 0, 0.2, 1)", // ease-out
            },

            // ==========================================
            // TYPOGRAPHY SCALE
            // ==========================================
            fontSize: {
                "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
            },
        },
    },
    plugins: [],
};

export default config;
