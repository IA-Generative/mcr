/// <reference types="vitest" />

import process from 'node:process';
import { fileURLToPath, URL } from 'node:url';

import { vueDsfrAutoimportPreset, vueDsfrComponentResolver } from '@gouvminint/vue-dsfr/meta';

import vue from '@vitejs/plugin-vue';
import vueJsx from '@vitejs/plugin-vue-jsx';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import { defineConfig } from 'vite';
import svgLoader from 'vite-svg-loader';
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite';
import path, { dirname, resolve } from 'node:path';

function setViteEnvMode() {
  const ALLOWED_ENV_MODE = ['DEV', 'DATA', 'STAGING', 'PREPROD', 'PROD'];
  if (process.env.ENV_MODE !== undefined && ALLOWED_ENV_MODE.includes(process.env.ENV_MODE)) {
    process.env.VITE_ENV_MODE = process.env.ENV_MODE;
  }
}

// https://vitejs.dev/config/
export default defineConfig(() => {
  setViteEnvMode();

  return {
    plugins: [
      vue(),
      vueJsx(),
      svgLoader(),
      VueI18nPlugin({
        include: resolve(dirname(fileURLToPath(import.meta.url)), './src/locales/**'),
      }),
      AutoImport({
        include: [/\.[tj]sx?$/, /\.vue$/, /\.vue\?vue/],
        imports: [
          // @ts-expect-error TS2322
          'vue',
          // @ts-expect-error TS2322
          'vue-router',
          // @ts-expect-error TS2322
          'vitest',
          // @ts-expect-error TS2322
          vueDsfrAutoimportPreset,
          {
            // @ts-expect-error TS2322
            '@sentry/vue': [
              'captureMessage',
              'captureException',
              'captureEvent',
              'setUser',
              'setTag',
              'setExtra',
              'addBreadcrumb',
              'configureScope',
              'getCurrentHub',
              'withScope',
              'startTransaction',
              'setContext',
            ],
          },
        ],
        vueTemplate: true,
        dts: './src/auto-imports.d.ts',
        eslintrc: {
          enabled: true,
          filepath: './.eslintrc-auto-import.json',
          globalsPropValue: true,
        },
      }),
      Components({
        extensions: ['vue'],
        dirs: ['src/components'],
        include: [/\.vue$/, /\.vue\?vue/],
        dts: './src/components.d.ts',
        resolvers: [vueDsfrComponentResolver],
      }),
    ],
    optimizeDeps: {
      exclude: ['@ffmpeg/ffmpeg', '@ffmpeg/util'],
    },
    server: {
      headers: {
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Embedder-Policy': 'require-corp',
      },
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    base: process.env.BASE_URL || '/',
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@dsb-norge/vue-keycloak-js': '@dsb-norge/vue-keycloak-js/dist/dsb-vue-keycloak.es.js',
        '@dsfr-artwork': path.resolve(__dirname, 'node_modules/@gouvfr/dsfr/dist/artwork'),
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      root: './src/',
      setupFiles: ['./vitest.setup.ts'],
    },
  }
})
