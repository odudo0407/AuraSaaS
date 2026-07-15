import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import { presetWind } from '@unocss/preset-wind'
import { transformerDirectives } from 'unocss'

export default defineConfig({
  plugins: [
    vue(),
    UnoCSS({
      presets: [presetWind()],
      transformers: [transformerDirectives()],
      theme: {
        colors: {
          canvas: '#ffffff',
          'surface-soft': '#f7f7f7',
          'surface-strong': '#f2f2f2',
          'surface-card': '#ffffff',
          primary: '#ff385c',
          'primary-active': '#e00b41',
          ink: '#222222',
          body: '#3f3f3f',
          muted: '#6a6a6a',
          'muted-soft': '#929292',
          hairline: '#dddddd',
          'hairline-soft': '#ebebeb',
          'border-strong': '#c1c1c1',
          'error-text': '#c13515',
        },
      },
    }),
  ],
  server: {
    port: 3000,
    proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          charts: ['echarts', 'vue-echarts'],
        },
      },
    },
  },
})
