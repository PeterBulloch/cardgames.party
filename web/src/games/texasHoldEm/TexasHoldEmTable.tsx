import { useCallback, useRef, useState } from 'react'
import { cardFromTag, cardLabel, cardNames } from '../../cards'
import PlayingCard, { EmptyCardSlot } from '../../PlayingCard'
import { useNfcScanner } from '../../useNfcScanner'
import type { LobbyState, NdefRecordDto } from '../../types'
import type { GameTableProps } from '../types'
import type { Target, TexasHoldEmAction, TexasHoldEmView } from './types'

const DECK = cardNames.filter((name) => name !== 'CARD_JOKER')
const BOARD_SIZE = 5
const HAND_SIZE = 2

function targetKey(target: Target): string {
    return target.kind === 'seat' ? `seat:${target.member_id}` : target.kind
}

function parseTarget(key: string): Target {
    if (key.startsWith('seat:')) return { kind: 'seat', member_id: key.slice(5) }
    return key === 'burn' ? { kind: 'burn' } : { kind: 'board' }
}

function nameOf(state: LobbyState, memberId: string): string {
    return state.members.find((member) => member.member_id === memberId)?.name ?? 'Unknown'
}

export default function TexasHoldEmTable({ state, send }: GameTableProps<TexasHoldEmView, TexasHoldEmAction>) {
    const [target, setTarget] = useState<Target>({ kind: 'board' })
    const [manualCard, setManualCard] = useState(DECK[0] ?? '')
    const [scanError, setScanError] = useState<string | null>(null)
    const targetRef = useRef(target)
    targetRef.current = target

    const handleScan = useCallback(
        (serialNumber: string, records: NdefRecordDto[]) => {
            const card = cardFromTag(serialNumber, records)
            if (!card) {
                setScanError('That tag does not hold a card.')
                return
            }
            setScanError(null)
            send({ type: 'deal_card', card, target: targetRef.current })
        },
        [send],
    )
    const scanner = useNfcScanner(handleScan)

    const { game, you } = state
    const canAct = you.can_act
    const showdown = game.showdown
    const resultFor = (memberId: string) => showdown?.results.find((result) => result.member_id === memberId)
    const remove = (card: string) => (canAct ? () => send({ type: 'return_card', card }) : undefined)
    const visibleCards = new Set([
        ...game.board,
        ...(game.burn.cards ?? []),
        ...game.seats.flatMap((seat) => seat.cards ?? []),
    ])

    return (
        <>
            <ol className="stages">
                {game.stages.map((stage) => (
                    <li key={stage} className={stage === game.stage ? 'stages__current' : ''}>
                        {stage}
                    </li>
                ))}
            </ol>

            <section className="board">
                <h2>
                    Board <span className="count">{game.board.length}/{BOARD_SIZE}</span>
                    <span className="burn">Burned: {game.burn.count}</span>
                </h2>
                <div className="card-row">
                    {game.board.map((card) => (
                        <PlayingCard key={card} code={card} onRemove={remove(card)} />
                    ))}
                    {Array.from({ length: BOARD_SIZE - game.board.length }, (_, index) => (
                        <EmptyCardSlot key={index} />
                    ))}
                </div>
                {game.burn.cards && game.burn.cards.length > 0 && (
                    <div className="card-row card-row--small">
                        {game.burn.cards.map((card) => (
                            <PlayingCard key={card} code={card} onRemove={remove(card)} />
                        ))}
                    </div>
                )}
            </section>

            {showdown && (
                <section className="showdown">
                    <h2>Showdown</h2>
                    {showdown.complete ? (
                        <p>
                            Winner{showdown.winners.length > 1 ? 's' : ''}:{' '}
                            <strong>{showdown.winners.map((id) => nameOf(state, id)).join(', ')}</strong>
                            {showdown.winners.length === 1 && resultFor(showdown.winners[0]) &&
                                ` with ${resultFor(showdown.winners[0])!.hand_name}`}
                        </p>
                    ) : (
                        <p className="empty">Waiting for a full board and hands.</p>
                    )}
                </section>
            )}

            <section>
                <h2>
                    Players <span className="count">{game.seats.length}/{state.lobby.max_players}</span>
                </h2>
                <ul className="seats">
                    {game.seats.map((seat) => {
                        const member = state.members.find((m) => m.member_id === seat.member_id)
                        const result = resultFor(seat.member_id)
                        const classes = [
                            'seat',
                            seat.member_id === you.member_id && 'seat--you',
                            seat.folded && 'seat--folded',
                            showdown?.winners.includes(seat.member_id) && 'seat--winner',
                        ].filter(Boolean).join(' ')
                        return (
                            <li key={seat.member_id} className={classes}>
                                <div className="seat__head">
                                    <span className={`dot ${member?.connected ? 'dot--on' : ''}`} />
                                    <strong>{member?.name ?? 'Unknown'}</strong>
                                    {seat.folded && <span className="badge">folded</span>}
                                    {result && <span className="badge badge--hand">{result.hand_name}</span>}
                                    {canAct && (
                                        <button
                                            type="button"
                                            className="secondary small"
                                            onClick={() =>
                                                send({ type: seat.folded ? 'unfold' : 'fold', member_id: seat.member_id })
                                            }
                                        >
                                            {seat.folded ? 'Unfold' : 'Fold'}
                                        </button>
                                    )}
                                </div>
                                <div className="card-row card-row--small">
                                    {seat.cards
                                        ? seat.cards.map((card) => (
                                            <PlayingCard key={card} code={card} onRemove={remove(card)} />
                                        ))
                                        : Array.from({ length: seat.card_count }, (_, index) => (
                                            <PlayingCard key={index} code={null} />
                                        ))}
                                </div>
                            </li>
                        )
                    })}
                </ul>
            </section>

            {canAct && (
                <section className="actions">
                    <h2>Actions</h2>
                    <label>
                        Deal to
                        <select value={targetKey(target)} onChange={(e) => setTarget(parseTarget(e.target.value))}>
                            <option value="board">Board ({game.board.length}/{game.board_limit} this stage)</option>
                            <option value="burn">Burn pile</option>
                            {game.seats.map((seat) => (
                                <option
                                    key={seat.member_id}
                                    value={`seat:${seat.member_id}`}
                                    disabled={seat.folded || seat.card_count >= HAND_SIZE}
                                >
                                    {nameOf(state, seat.member_id)} ({seat.card_count}/{HAND_SIZE})
                                </option>
                            ))}
                        </select>
                    </label>

                    <div className="controls">
                        <select value={manualCard} onChange={(e) => setManualCard(e.target.value)}>
                            {DECK.map((name) => (
                                <option key={name} value={name} disabled={visibleCards.has(name)}>
                                    {cardLabel(name)}
                                </option>
                            ))}
                        </select>
                        <button
                            type="button"
                            onClick={() => send({ type: 'deal_card', card: manualCard, target })}
                            disabled={!manualCard || visibleCards.has(manualCard)}
                        >
                            Deal
                        </button>
                    </div>

                    <div className="controls">
                        {scanner.status === 'scanning' ? (
                            <button type="button" onClick={scanner.stop}>
                                Stop scanning
                            </button>
                        ) : (
                            <button type="button" onClick={() => void scanner.start()} disabled={!scanner.isSupported}>
                                {scanner.isSupported ? 'Scan cards' : 'NFC unavailable'}
                            </button>
                        )}
                    </div>
                    {scanner.status === 'scanning' && (
                        <p className="status status--scanning">Hold a card to the phone to deal it to the selected target.</p>
                    )}
                    {(scanner.error || scanError) && <p className="error">{scanner.error ?? scanError}</p>}

                    <div className="controls">
                        <button
                            type="button"
                            onClick={() => send({ type: 'next_stage' })}
                            disabled={game.stage === game.stages[game.stages.length - 1]}
                        >
                            Next stage
                        </button>
                        <button type="button" className="secondary" onClick={() => send({ type: 'new_hand' })}>
                            New hand
                        </button>
                    </div>
                </section>
            )}
        </>
    )
}
