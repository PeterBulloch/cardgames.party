import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const certFile = fileURLToPath(new URL('../certs/server.pem', import.meta.url))
const keyFile = fileURLToPath(new URL('../certs/server.key', import.meta.url))
const hasCert = fs.existsSync(certFile) && fs.existsSync(keyFile)

if (!hasCert) {
    console.warn('[vite] certs/ missing - serving plain HTTP, Web NFC will be unavailable.')
}

export default defineConfig({
    plugins: [react()],
    server: {
        host: '0.0.0.0',
        port: 5173,
        https: hasCert
            ? { cert: fs.readFileSync(certFile), key: fs.readFileSync(keyFile) }
            : undefined,
        proxy: {
            '/api': { target: 'http://127.0.0.1:8000', ws: true },
        },
    },
})
