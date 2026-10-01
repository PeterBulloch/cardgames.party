import { useState, type FormEvent } from 'react'
import { createLobby, joinLobby } from './api'
import { games } from './games'
import type { Role, Session } from './types'

type Mode = 'join' | 'create'

const ROLES: { value: Role; label: string }[] = [
    { value: 'player', label: 'Player - sees own hand' },
    { value: 'dealer', label: 'Dealer - sees all, can act' },
    { value: 'observer', label: 'Observer - watch only' },
]

interface Props {
    onEnter: (session: Session) => void
    notice: string | null
}

export default function Home({ onEnter, notice }: Props) {
    const [mode, setMode] = useState<Mode | null>(null)
    const [lobbyName, setLobbyName] = useState('')
    const [password, setPassword] = useState('')
    const [displayName, setDisplayName] = useState('')
    const [role, setRole] = useState<Role>('player')
    const [gameKey, setGameKey] = useState(games[0].key)
    const [maxPlayers, setMaxPlayers] = useState(String(games[0].maxPlayers))
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const selectedGame = games.find((game) => game.key === gameKey) ?? games[0]

    const openForm = (nextMode: Mode) => {
        setMode(nextMode)
        setError(null)
    }

    const submit = async (event: FormEvent) => {
        event.preventDefault()
        if (!mode) return
        setBusy(true)
        setError(null)
        const common = {
            name: lobbyName,
            password: password || null,
            display_name: displayName,
            role,
        }
        try {
            const session =
                mode === 'create'
                    ? await createLobby({ ...common, game: gameKey, max_players: Number(maxPlayers) })
                    : await joinLobby(common)
            onEnter(session)
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : 'Request failed.')
        } finally {
            setBusy(false)
        }
    }

    return (
        <main className="app">
            <header>
                <h1>CardGames.party</h1>
                <p className="status">Track and view your card games with friends.</p>
            </header>

            {notice && <p className="notice">{notice}</p>}

            <div className="home-actions">
                <button type="button" onClick={() => openForm('create')}>
                    Create lobby
                </button>
                <button type="button" className="secondary" onClick={() => openForm('join')}>
                    Join lobby
                </button>
            </div>

            {mode && (
                <div className="modal-backdrop" onMouseDown={() => !busy && setMode(null)}>
                    <section
                        className="modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="lobby-dialog-title"
                        onMouseDown={(event) => event.stopPropagation()}
                    >
                        <div className="modal__header">
                            <h2 id="lobby-dialog-title">{mode === 'create' ? 'Create lobby' : 'Join lobby'}</h2>
                            <button
                                type="button"
                                className="icon-button"
                                aria-label="Close"
                                onClick={() => setMode(null)}
                                disabled={busy}
                            >
                                &times;
                            </button>
                        </div>
                        <form className="form" onSubmit={(event) => void submit(event)}>
                            <label>
                                Lobby name
                                <input value={lobbyName} onChange={(e) => setLobbyName(e.target.value)} maxLength={40} required autoFocus />
                            </label>
                            <label>
                                Password {mode === 'create' && <span className="hint">(optional)</span>}
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    maxLength={128}
                                    autoComplete={mode === 'create' ? 'new-password' : 'current-password'}
                                />
                            </label>
                            {mode === 'create' && (
                                <>
                                    <label>
                                        Game
                                        <select
                                            value={gameKey}
                                            onChange={(e) => {
                                                setGameKey(e.target.value)
                                                setMaxPlayers(String(games.find((g) => g.key === e.target.value)?.maxPlayers ?? 2))
                                            }}
                                        >
                                            {games.map((game) => (
                                                <option key={game.key} value={game.key}>
                                                    {game.label}
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                    <label>
                                        Max players
                                        <input
                                            type="number"
                                            min={selectedGame.minPlayers}
                                            max={selectedGame.maxPlayers}
                                            value={maxPlayers}
                                            inputMode="numeric"
                                            onChange={(e) => setMaxPlayers(e.target.value)}
                                            required
                                        />
                                    </label>
                                </>
                            )}
                            <label>
                                Your name
                                <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={24} required />
                            </label>
                            <label>
                                Join as
                                <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
                                    {ROLES.map(({ value, label }) => (
                                        <option key={value} value={value}>
                                            {label}
                                        </option>
                                    ))}
                                </select>
                            </label>

                            {error && <p className="error">{error}</p>}

                            <button type="submit" disabled={busy}>
                                {mode === 'create' ? 'Create and join' : 'Join'}
                            </button>
                        </form>
                    </section>
                </div>
            )}

            <p className="footer-link">
                <a href="/scanner">Card scanner and tag writer</a>
            </p>
            <p className="version">v{__APP_VERSION__}</p>
        </main>
    )
}
