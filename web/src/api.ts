import type { Scan, ScanIn } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(path, init)
    if (!response.ok) {
        throw new Error(`${init?.method ?? 'GET'} ${path} failed: ${response.status}`)
    }
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

export function fetchScans(): Promise<Scan[]> {
    return request<Scan[]>('/api/scans')
}

export function postScan(scan: ScanIn): Promise<Scan> {
    return request<Scan>('/api/scans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scan),
    })
}

export function clearScans(): Promise<void> {
    return request<void>('/api/scans', { method: 'DELETE' })
}
