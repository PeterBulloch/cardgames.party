import type { CreateLobbyIn, JoinLobbyIn, Scan, ScanIn, Session } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(path, init)
    if (!response.ok) {
        const detail = await response.json().then((body) => body?.detail, () => null)
        const message = Array.isArray(detail) ? detail[0]?.msg : detail
        throw new Error(typeof message === 'string' ? message : `${init?.method ?? 'GET'} ${path} failed: ${response.status}`)
    }
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

function postJson<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
}

export function createLobby(body: CreateLobbyIn): Promise<Session> {
    return postJson<Session>('/api/lobbies', body)
}

export function joinLobby(body: JoinLobbyIn): Promise<Session> {
    return postJson<Session>('/api/lobbies/join', body)
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
