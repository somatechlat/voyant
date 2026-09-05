import { defineConfig } from 'vite';

export default defineConfig({
    server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
            '/v1': {
                target: 'https://localhost:45000',
                changeOrigin: true,
                secure: false,
            },
        },
    },
    build: {
        outDir: 'dist',
    },
});
