import { useCallback, useEffect, useRef, useState } from 'react'
import type { GameAction, LobbyAction, LobbyState, ServerMessage, Session } from './types'

export type SocketStatus = 'connecting' | 'open' | 'closed'

// Server close codes that mean the session is gone for good, so reconnecting is pointless.
const FINAL_CLOSE_CODES = new Set([1008, 4404])
const MAX_BACKOFF_MS = 10_000

export function useLobbySocket(session: Session | null, onEnded: (reason: string) => void) {
    const [state, setState] = useState<LobbyState | null>(null)
    const [status, setStatus] = useState<SocketStatus>('connecting')
    const [error, setError] = useState<string | null>(null)
    const socketRef = useRef<WebSocket | null>(null)
    const seqRef = useRef(0)
    const versionRef = useRef(-1)
    const onEndedRef = useRef(onEnded)

    onEndedRef.current = onEnded

    useEffect(() => {
        if (!session) return
        let disposed = false
        let attempt = 0
        let timer: ReturnType<typeof setTimeout> | undefined
        versionRef.current = -1
        setState(null)

        const connect = () => {
            const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const socket = new WebSocket(`${scheme}//${window.location.host}/api/ws`)
            socketRef.current = socket
            setStatus('connecting')

            socket.onopen = () => {
                attempt = 0
                socket.send(JSON.stringify({ type: 'hello', token: session.token }))
                setStatus('open')
            }

            socket.onmessage = (event) => {
                const message = JSON.parse(event.data as string) as ServerMessage
                if (message.type === 'state') {
                    if (message.version < versionRef.current) return
                    versionRef.current = message.version
                    setState(message.state)
                } else if (message.type === 'error') {
                    setError(message.message)
                } else if (message.seq === seqRef.current) {
                    setError(null)
                }
            }

            socket.onclose = (event) => {
                if (socketRef.current === socket) socketRef.current = null
                if (disposed) return
                if (FINAL_CLOSE_CODES.has(event.code)) {
                    setStatus('closed')
                    onEndedRef.current(event.reason || 'The session has ended.')
                    return
                }
                setStatus('connecting')
                timer = setTimeout(connect, Math.min(500 * 2 ** attempt++, MAX_BACKOFF_MS))
            }
        }

        connect()
        return () => {
            disposed = true
            clearTimeout(timer)
            socketRef.current?.close()
            socketRef.current = null
        }
    }, [session])

    const send = useCallback(
        (action: LobbyAction | GameAction) => {
            const socket = socketRef.current
            if (!session || !socket || socket.readyState !== WebSocket.OPEN) {
                setError('Not connected to the server.')
                return
            }
            seqRef.current += 1
            socket.send(
                JSON.stringify({
                    lobby: session.lobby_id,
                    player: session.member_id,
                    seq: seqRef.current,
                    sent_at: new Date().toISOString(),
                    action,
                }),
            )
        },
        [session],
    )

    return { state, status, error, send, clearError: () => setError(null) }
}
