import { defineConfig } from 'vite';

export default defineConfig({
    server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
            '/v1': {
                target: 'http://localhost:45000',
                changeOrigin: true,
                secure: false,
                configure: (proxy) => {
                    proxy.on('proxyReq', (proxyReq) => {
                        // Tell Django the request came over HTTPS (prevents SSL redirect)
                        proxyReq.setHeader('X-Forwarded-Proto', 'https');
                        proxyReq.setHeader('X-Forwarded-Port', '45000');
                    });
                },
            },
        },
    },
    build: {
        outDir: 'dist',
    },
    esbuild: {
        target: 'esnext',
        tsconfigRaw: {
            compilerOptions: {
                experimentalDecorators: true,
                useDefineForClassFields: false,
            },
        },
    },
});
