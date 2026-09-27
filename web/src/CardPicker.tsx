import { useState } from 'react'
import { RANK_ORDER, SUIT_ORDER, cardLabel } from './cards'
import PlayingCard, { EmptyCardSlot } from './PlayingCard'

const SUIT_SYMBOLS: Record<string, string> = { SPADE: '♠', HEART: '♥', DIAMOND: '♦', CLUB: '♣' }
const RED_SUITS = new Set(['HEART', 'DIAMOND'])
const RANK_SHORT: Record<string, string> = {
    ACE: 'A', TWO: '2', THREE: '3', FOUR: '4', FIVE: '5', SIX: '6', SEVEN: '7',
    EIGHT: '8', NINE: '9', TEN: '10', JACK: 'J', QUEEN: 'Q', KING: 'K',
}

interface Props {
    /** Card codes that may be picked, e.g. a standard deck without jokers. */
    cards: string[]
    /** Cards already in play, shown but not selectable. */
    unavailable: Set<string>
    value: string | null
    /** Null when the remembered rank is not available in the newly chosen suit. */
    onChange: (card: string | null) => void
}

function suitOf(card: string | null): string | null {
    return card?.split('_')[1] ?? null
}

function rankOf(card: string | null): string | null {
    return card?.split('_')[2] ?? null
}

export default function CardPicker({ cards, unavailable, value, onChange }: Props) {
    const available = new Set(cards)
    const suits = SUIT_ORDER.filter((suit) => cards.some((card) => suitOf(card) === suit))
    const [suit, setSuit] = useState<string | null>(suitOf(value) ?? suits[0] ?? null)
    const [rank, setRank] = useState<string | null>(rankOf(value))

    const chooseSuit = (next: string) => {
        setSuit(next)
        if (!rank) return
        const card = `CARD_${next}_${rank}`
        onChange(available.has(card) && !unavailable.has(card) ? card : null)
    }

    const chooseRank = (next: string, card: string) => {
        setRank(next)
        onChange(card)
    }

    return (
        <div className="card-picker">
            <div className="card-picker__preview" aria-live="polite">
                {value ? <PlayingCard code={value} /> : <EmptyCardSlot />}
                <span>{value ? cardLabel(value) : 'Pick a card'}</span>
            </div>
            <div className="card-picker__suits" role="group" aria-label="Suit">
                {suits.map((option) => (
                    <button
                        key={option}
                        type="button"
                        className={`suit ${RED_SUITS.has(option) ? 'suit--red' : ''} ${option === suit ? 'is-selected' : ''}`}
                        aria-pressed={option === suit}
                        aria-label={`${option.toLowerCase()}s`}
                        onClick={() => chooseSuit(option)}
                    >
                        {SUIT_SYMBOLS[option] ?? option}
                    </button>
                ))}
            </div>
            {suit && (
                <div className="card-picker__ranks" role="group" aria-label="Rank">
                    {RANK_ORDER.map((option) => {
                        const card = `CARD_${suit}_${option}`
                        if (!available.has(card)) return null
                        const selected = option === rank && !unavailable.has(card)
                        return (
                            <button
                                key={card}
                                type="button"
                                className={`rank ${RED_SUITS.has(suit) ? 'suit--red' : ''} ${selected ? 'is-selected' : ''}`}
                                aria-pressed={selected}
                                aria-label={cardLabel(card)}
                                disabled={unavailable.has(card)}
                                onClick={() => chooseRank(option, card)}
                            >
                                {RANK_SHORT[option] ?? option}
                            </button>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
