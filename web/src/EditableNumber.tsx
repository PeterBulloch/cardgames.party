import { useState, type FormEvent } from 'react'

interface Props {
    value: number
    /** Omit to render read-only. */
    onSave?: (value: number) => void
    label: string
}

export default function EditableNumber({ value, onSave, label }: Props) {
    const [draft, setDraft] = useState<string | null>(null)

    if (!onSave || draft === null) {
        return (
            <span className="editable-number">
                {value}
                {onSave && (
                    <button type="button" className="icon" aria-label={`Edit ${label}`} onClick={() => setDraft(String(value))}>
                        ✎
                    </button>
                )}
            </span>
        )
    }

    const submit = (event: FormEvent) => {
        event.preventDefault()
        const next = Number(draft)
        if (Number.isInteger(next) && next >= 0) onSave(next)
        setDraft(null)
    }

    return (
        <form className="editable-number editable-number--editing" onSubmit={submit}>
            <input
                type="number"
                inputMode="numeric"
                min={0}
                step={1}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                aria-label={label}
                autoFocus
            />
            <button type="submit" className="small">
                Set
            </button>
            <button type="button" className="secondary small" onClick={() => setDraft(null)}>
                Cancel
            </button>
        </form>
    )
}
