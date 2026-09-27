import { useState } from 'react'
import type { LegalBet, TexasHoldEmAction } from './types'

interface Props {
    memberId: string
    playerName: string
    options: LegalBet[]
    currentBet: number
    streetBet: number
    send: (action: TexasHoldEmAction) => void
}

/** Remount (via `key`) when the turn changes so the amount resets to the new minimum. */
export default function BettingControls({ memberId, playerName, options, currentBet, streetBet, send }: Props) {
    const sized = options.find((option) => option.type === 'bet' || option.type === 'raise')
    // Kept as text so the field can be cleared while typing.
    const [amountText, setAmountText] = useState(String(sized && 'min' in sized ? sized.min : 0))
    const amount = amountText.trim() === '' ? NaN : Number(amountText)

    return (
        <div className="betting">
            <p className="status">
                Acting for <strong>{playerName}</strong>
                {currentBet > 0 && ` · to match: ${currentBet} (in: ${streetBet})`}
            </p>
            <div className="controls">
                {options.map((option) => {
                    if (option.type === 'fold' || option.type === 'check') {
                        return (
                            <button
                                key={option.type}
                                type="button"
                                className={option.type === 'fold' ? 'secondary' : ''}
                                onClick={() => send({ type: option.type, member_id: memberId })}
                            >
                                {option.type === 'fold' ? 'Fold' : 'Check'}
                            </button>
                        )
                    }
                    if (option.type === 'call') {
                        return (
                            <button key="call" type="button" onClick={() => send({ type: 'call', member_id: memberId })}>
                                Call {option.amount}
                            </button>
                        )
                    }
                    return null
                })}
            </div>
            {sized && 'min' in sized && (
                <div className="controls sized-bet">
                    <input
                        type="range"
                        min={sized.min}
                        max={sized.max}
                        value={Number.isNaN(amount) ? sized.min : amount}
                        onChange={(event) => setAmountText(event.target.value)}
                        aria-label={`${sized.type} amount`}
                    />
                    <input
                        type="number"
                        inputMode="numeric"
                        min={sized.min}
                        max={sized.max}
                        value={amountText}
                        onChange={(event) => setAmountText(event.target.value)}
                    />
                    <button
                        type="button"
                        onClick={() => send({ type: sized.type, member_id: memberId, amount })}
                        disabled={!Number.isInteger(amount) || amount < sized.min || amount > sized.max}
                    >
                        {amount === sized.max ? 'All-in' : `${sized.type === 'bet' ? 'Bet' : 'Raise to'} ${amountText}`}
                    </button>
                </div>
            )}
        </div>
    )
}
