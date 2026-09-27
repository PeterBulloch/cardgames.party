import { useState, type FormEvent } from 'react'
import type { BlindSettings, TexasHoldEmAction } from './types'

interface Props {
    blinds: BlindSettings
    send: (action: TexasHoldEmAction) => void
}

// Inputs hold text so a field can be emptied while typing instead of snapping back to 0.
interface Draft {
    small: string
    big: string
    auto_double: boolean
    double_every: string
}

function toDraft({ small, big, auto_double, double_every }: BlindSettings): Draft {
    return { small: String(small), big: String(big), auto_double, double_every: String(double_every) }
}

function wholeNumber(text: string, minimum: number): number | null {
    const value = Number(text)
    return text.trim() !== '' && Number.isInteger(value) && value >= minimum ? value : null
}

export default function BlindsForm({ blinds, send }: Props) {
    const [draft, setDraft] = useState<Draft>(() => toDraft(blinds))

    const small = wholeNumber(draft.small, 0)
    const big = wholeNumber(draft.big, 0)
    const doubleEvery = wholeNumber(draft.double_every, 1)
    const valid = small !== null && big !== null && big >= small && (!draft.auto_double || doubleEvery !== null)

    const submit = (event: FormEvent) => {
        event.preventDefault()
        if (!valid || small === null || big === null) return
        send({
            type: 'set_blinds',
            small,
            big,
            auto_double: draft.auto_double,
            double_every: doubleEvery ?? blinds.double_every,
        })
    }

    const update = (patch: Partial<Draft>) => setDraft((current) => ({ ...current, ...patch }))

    return (
        <details className="writer" onToggle={() => setDraft(toDraft(blinds))}>
            <summary>Blinds settings</summary>
            <form className="form" onSubmit={submit}>
                <div className="controls">
                    <label>
                        Small blind
                        <input
                            type="number"
                            inputMode="numeric"
                            min={0}
                            value={draft.small}
                            onChange={(e) => update({ small: e.target.value })}
                        />
                    </label>
                    <label>
                        Big blind
                        <input
                            type="number"
                            inputMode="numeric"
                            min={0}
                            value={draft.big}
                            onChange={(e) => update({ big: e.target.value })}
                        />
                    </label>
                </div>
                <label className="toggle">
                    <input
                        type="checkbox"
                        checked={draft.auto_double}
                        onChange={(e) => update({ auto_double: e.target.checked })}
                    />
                    Double the blinds automatically
                </label>
                {draft.auto_double && (
                    <label>
                        Every how many hands
                        <input
                            type="number"
                            inputMode="numeric"
                            min={1}
                            value={draft.double_every}
                            onChange={(e) => update({ double_every: e.target.value })}
                        />
                    </label>
                )}
                {small !== null && big !== null && big < small && (
                    <p className="hint">The big blind cannot be smaller than the small blind.</p>
                )}
                <button type="submit" disabled={!valid}>
                    Save blinds
                </button>
            </form>
        </details>
    )
}
