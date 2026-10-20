import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backend = env.BACKEND_URL || 'http://127.0.0.1:5000';
  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      allowedHosts: ['.e2b.app', 'localhost'],
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
          timeout: 70_000,
          proxyTimeout: 70_000,
        },
      },
    },
  };
});
