import { useCallback, useState } from 'react'
import Home from './Home'
import LobbyRoom from './LobbyRoom'
import type { Session } from './types'

const STORAGE_KEY = 'cards.session'

function loadSession(): Session | null {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY)
        return raw ? (JSON.parse(raw) as Session) : null
    } catch {
        return null
    }
}

export default function LobbyApp() {
    const [session, setSession] = useState<Session | null>(loadSession)
    const [notice, setNotice] = useState<string | null>(null)

    const enter = useCallback((next: Session) => {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
        setNotice(null)
        setSession(next)
    }, [])

    const exit = useCallback((reason: string) => {
        sessionStorage.removeItem(STORAGE_KEY)
        setNotice(reason)
        setSession(null)
    }, [])

    return session ? <LobbyRoom session={session} onEnded={exit} /> : <Home onEnter={enter} notice={notice} />
}
