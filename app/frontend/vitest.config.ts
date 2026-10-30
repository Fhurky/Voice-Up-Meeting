import {fileURLToPath, URL} from 'node:url';
import {defineConfig} from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {alias: {'@': fileURLToPath(new URL('./src', import.meta.url))}},
  test: {
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {reporter: ['text', 'json-summary']},
    // The theme contrast test reads the token sheet as text through `?raw`.
    css: {include: [/globals\.css/]},
  },
});

