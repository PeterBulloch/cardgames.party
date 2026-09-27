import { cardImages, cardLabel } from './cards'

interface Props {
    /** Null renders a face-down card. */
    code: string | null
    onRemove?: () => void
}

export default function PlayingCard({ code, onRemove }: Props) {
    if (!code) return <div className="playing-card playing-card--back" aria-label="Hidden card" />
    const image = cardImages[code]
    return (
        <div className="playing-card">
            {image ? <img src={image} alt={cardLabel(code)} /> : <span>{code}</span>}
            {onRemove && (
                <button type="button" className="playing-card__remove" onClick={onRemove} aria-label="Return card">
                    ×
                </button>
            )}
        </div>
    )
}

export function EmptyCardSlot() {
    return <div className="playing-card playing-card--empty" />
}
