import { useEffect } from 'react'
import { preloadCardImages } from './cards'
import { findGame } from './games'
import { useLobbySocket } from './useLobbySocket'
import type { Session } from './types'

interface Props {
    session: Session
    onEnded: (reason: string) => void
}

export default function LobbyRoom({ session, onEnded }: Props) {
    const { state, status, error, send, clearError } = useLobbySocket(session, onEnded)

    useEffect(preloadCardImages, [])

    if (!state) {
        return (
            <main className="app">
                <p className="status">{status === 'connecting' ? 'Connecting…' : 'Disconnected.'}</p>
            </main>
        )
    }

    const { you } = state
    const game = findGame(state.lobby.game)
    const onlookers = state.members.filter((member) => member.role !== 'player')

    return (
        <main className="app app--table">
            <header className="table-header">
                <div>
                    <h1>{state.lobby.name}</h1>
                    <p className="status">
                        {game?.label ?? state.lobby.game} · {you.name} · {you.role} ·{' '}
                        <span className={`conn conn--${status}`}>{status === 'open' ? 'live' : status}</span>
                    </p>
                </div>
                <button type="button" className="secondary" onClick={() => send({ type: 'leave' })}>
                    Leave
                </button>
            </header>

            {error && (
                <p className="error" onClick={clearError}>
                    {error}
                </p>
            )}

            {game ? (
                <game.Table state={state} send={send} />
            ) : (
                <p className="error">This client does not support {state.lobby.game}.</p>
            )}

            {onlookers.length > 0 && (
                <p className="onlookers">
                    Watching: {onlookers.map((member) => `${member.name} (${member.role})`).join(', ')}
                </p>
            )}

            {you.role === 'observer' && (
                <label className="toggle">
                    <input
                        type="checkbox"
                        checked={you.hide_hands}
                        onChange={(event) => send({ type: 'set_view', hide_hands: event.target.checked })}
                    />
                    Hide players' hands (public view)
                </label>
            )}
        </main>
    )
}
