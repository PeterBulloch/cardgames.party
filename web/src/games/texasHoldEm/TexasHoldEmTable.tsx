import { useCallback, useState } from 'react'
import { cardFromTag, cardLabel, cardNames } from '../../cards'
import EditableNumber from '../../EditableNumber'
import PlayingCard, { EmptyCardSlot } from '../../PlayingCard'
import { useNfcScanner } from '../../useNfcScanner'
import type { LobbyState, NdefRecordDto } from '../../types'
import type { GameTableProps } from '../types'
import BettingControls from './BettingControls'
import BlindsForm from './BlindsForm'
import type { DealTarget, TexasHoldEmAction, TexasHoldEmView } from './types'

const DECK = cardNames.filter((name) => name !== 'CARD_JOKER')
const BOARD_SIZE = 5

function nameOf(state: LobbyState, memberId: string | null): string {
    return state.members.find((member) => member.member_id === memberId)?.name ?? 'Unknown'
}

function describeDeal(state: LobbyState, target: DealTarget): string {
    if (target.kind === 'seat') return `to ${nameOf(state, target.member_id)}`
    return target.kind === 'burn' ? 'to the burn pile' : 'to the board'
}

export default function TexasHoldEmTable({ state, send }: GameTableProps<TexasHoldEmView, TexasHoldEmAction>) {
    const [manualCard, setManualCard] = useState(DECK[0] ?? '')
    const [scanError, setScanError] = useState<string | null>(null)

    const handleScan = useCallback(
        (serialNumber: string, records: NdefRecordDto[]) => {
            const card = cardFromTag(serialNumber, records)
            if (!card) {
                setScanError('That tag does not hold a card.')
                return
            }
            setScanError(null)
            send({ type: 'deal_card', card })
        },
        [send],
    )
    const scanner = useNfcScanner(handleScan)

    const { game, you } = state
    const canAct = you.can_act
    const result = game.result
    const resultFor = (memberId: string) => result?.results.find((entry) => entry.member_id === memberId)
    const visibleCards = new Set([
        ...game.board,
        ...(game.burn.cards ?? []),
        ...game.seats.flatMap((seat) => seat.cards ?? []),
    ])
    const toActSeat = game.seats.find((seat) => seat.member_id === game.to_act)
    const names = (ids: string[]) => ids.map((id) => nameOf(state, id)).join(', ')

    let status: string
    if (game.phase === 'waiting') status = 'Waiting for the first hand to start.'
    else if (game.phase === 'dealing' && game.next_deal) status = `Next card goes ${describeDeal(state, game.next_deal)}.`
    else if (game.phase === 'betting') status = `${nameOf(state, game.to_act)} to act.`
    else if (result?.winners.length) {
        const winners = result.winners.map((id) => nameOf(state, id)).join(', ')
        const hand = result.winners.length === 1 ? resultFor(result.winners[0])?.hand_name : undefined
        status = `${winners} win${result.winners.length === 1 ? 's' : ''}${hand ? ` with ${hand}` : ''}${result.uncontested ? ' (everyone else folded)' : ''}.`
    } else status = 'Hand over.'

    return (
        <>
            <ol className="stages">
                {game.stages.map((stage) => (
                    <li key={stage} className={stage === game.stage ? 'stages__current' : ''}>
                        {stage}
                    </li>
                ))}
            </ol>

            <p className="turn">
                {game.hand_number > 0 && <span className="count">Hand {game.hand_number}</span>}
                {status}
            </p>
            {game.dealer?.dedicated && (
                <p className="status">Dealer: {nameOf(state, game.dealer.member_id)}</p>
            )}
            <p className="status">
                Blinds {game.blinds.small}/{game.blinds.big}
                {game.blinds.hands_until_double !== null &&
                    ` · doubling in ${game.blinds.hands_until_double} hand${game.blinds.hands_until_double === 1 ? '' : 's'}`}
            </p>

            {game.pots.length > 0 && (
                <section className="pots">
                    <h2>{game.pots.length > 1 ? 'Pots' : 'Pot'}</h2>
                    <ul>
                        {game.pots.map((pot, index) => (
                            <li key={index}>
                                <span>{index === 0 ? 'Main' : `Side ${index}`}</span>
                                <EditableNumber
                                    value={pot.amount}
                                    label={`pot ${index + 1}`}
                                    onSave={canAct ? (amount) => send({ type: 'set_pot', index, amount }) : undefined}
                                />
                                {game.pots.length > 1 && <span className="hint">{names(pot.eligible)}</span>}
                                {pot.winners.length > 0 && <span className="badge badge--hand">→ {names(pot.winners)}</span>}
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            <section className="board">
                <h2>
                    Board <span className="count">{game.board.length}/{BOARD_SIZE}</span>
                    <span className="burn">Burned: {game.burn.count}</span>
                </h2>
                <div className="card-row">
                    {game.board.map((card) => (
                        <PlayingCard key={card} code={card} />
                    ))}
                    {Array.from({ length: BOARD_SIZE - game.board.length }, (_, index) => (
                        <EmptyCardSlot key={index} />
                    ))}
                </div>
                {game.burn.cards && game.burn.cards.length > 0 && (
                    <div className="card-row card-row--small">
                        {game.burn.cards.map((card) => (
                            <PlayingCard key={card} code={card} />
                        ))}
                    </div>
                )}
            </section>

            <section>
                <h2>
                    Players <span className="count">{game.seats.length}/{state.lobby.max_players}</span>
                </h2>
                <ul className="seats">
                    {game.seats.map((seat) => {
                        const member = state.members.find((m) => m.member_id === seat.member_id)
                        const hand = resultFor(seat.member_id)
                        const classes = [
                            'seat',
                            seat.member_id === you.member_id && 'seat--you',
                            (seat.folded || !seat.in_hand) && 'seat--folded',
                            seat.member_id === game.to_act && 'seat--to-act',
                            result?.winners.includes(seat.member_id) && 'seat--winner',
                        ].filter(Boolean).join(' ')
                        return (
                            <li key={seat.member_id} className={classes}>
                                <div className="seat__head">
                                    <span className={`dot ${member?.connected ? 'dot--on' : ''}`} />
                                    <strong>{member?.name ?? 'Unknown'}</strong>
                                    {seat.member_id === game.button && <span className="badge badge--button">D</span>}
                                    {seat.member_id === game.small_blind && <span className="badge">SB</span>}
                                    {seat.member_id === game.big_blind && <span className="badge">BB</span>}
                                    {!seat.in_hand && game.hand_number > 0 && <span className="badge">sitting out</span>}
                                    {seat.folded && <span className="badge">folded</span>}
                                    {seat.all_in && <span className="badge">all-in</span>}
                                    {hand && <span className="badge badge--hand">{hand.hand_name}</span>}
                                </div>
                                <div className="seat__chips">
                                    <span>
                                        Chips{' '}
                                        <EditableNumber
                                            value={seat.chips}
                                            label={`chips for ${member?.name ?? 'player'}`}
                                            onSave={
                                                canAct
                                                    ? (chips) => send({ type: 'set_chips', member_id: seat.member_id, chips })
                                                    : undefined
                                            }
                                        />
                                    </span>
                                    {seat.street_bet > 0 && <span className="bet">Bet {seat.street_bet}</span>}
                                </div>
                                <div className="card-row card-row--small">
                                    {seat.cards
                                        ? seat.cards.map((card) => <PlayingCard key={card} code={card} />)
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

                    {game.phase === 'betting' && game.to_act && toActSeat && (
                        <BettingControls
                            key={`${game.to_act}-${game.current_bet}-${game.stage}`}
                            memberId={game.to_act}
                            playerName={nameOf(state, game.to_act)}
                            options={game.legal_bets}
                            currentBet={game.current_bet}
                            streetBet={toActSeat.street_bet}
                            send={send}
                        />
                    )}

                    {game.phase === 'dealing' && game.next_deal && (
                        <>
                            <p className="status">Deal the next card {describeDeal(state, game.next_deal)}:</p>
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
                                    onClick={() => send({ type: 'deal_card', card: manualCard })}
                                    disabled={!manualCard || visibleCards.has(manualCard)}
                                >
                                    Deal
                                </button>
                            </div>
                        </>
                    )}

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
                        <p className="status status--scanning">Scanned cards are dealt to the next position automatically.</p>
                    )}
                    {(scanner.error || scanError) && <p className="error">{scanner.error ?? scanError}</p>}

                    <div className="controls">
                        {game.can_award && (
                            <button type="button" onClick={() => send({ type: 'award_pots' })}>
                                Award {game.pots.length > 1 ? 'pots' : 'pot'}
                            </button>
                        )}
                        {game.can_start_hand && (
                            <button type="button" onClick={() => send({ type: 'start_hand' })}>
                                {game.hand_number === 0 ? 'Start first hand' : 'Next hand'}
                            </button>
                        )}
                        <button
                            type="button"
                            className="secondary"
                            onClick={() => send({ type: 'undo' })}
                            disabled={!game.can_undo}
                        >
                            Undo
                        </button>
                    </div>

                    {game.can_set_blinds && <BlindsForm blinds={game.blinds} send={send} />}
                </section>
            )}
        </>
    )
}
