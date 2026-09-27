import type { Scan } from './types'

// Vite resolves every card SVG at build time, so the map is a static name -> URL lookup.
const modules = import.meta.glob('../cards/*.svg', {
    eager: true,
    query: '?url',
    import: 'default',
}) as Record<string, string>

export const cardImages: Record<string, string> = Object.fromEntries(
    Object.entries(modules).map(([path, url]) => [
        path.slice(path.lastIndexOf('/') + 1).replace(/\.svg$/, ''),
        url,
    ]),
)

const CARD_PATTERN = /^CARD_[A-Z]+(_[A-Z]+)?$/

export const SUIT_ORDER = ['SPADE', 'HEART', 'DIAMOND', 'CLUB']
export const RANK_ORDER = [
    'ACE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN',
    'JACK', 'QUEEN', 'KING',
]

function sortKey(name: string): number {
    if (name === 'CARD_JOKER') return Number.MAX_SAFE_INTEGER
    const [, suit, rank] = name.split('_')
    return SUIT_ORDER.indexOf(suit) * 100 + RANK_ORDER.indexOf(rank)
}

export const cardNames: string[] = Object.keys(cardImages).sort((a, b) => sortKey(a) - sortKey(b))

function normalise(value: string | null | undefined): string | null {
    if (!value) return null
    const name = value.trim().toUpperCase()
    return CARD_PATTERN.test(name) ? name : null
}

/** The card code carried by a scan, or null when the tag holds something else. */
export function cardNameFor(scan: Scan): string | null {
    return cardFromTag(scan.serialNumber, scan.records)
}

export function cardFromTag(serialNumber: string, records: Scan['records']): string | null {
    for (const record of records) {
        const name = normalise(record.text)
        if (name) return name
    }
    return normalise(serialNumber)
}

export function cardLabel(name: string): string {
    if (name === 'CARD_JOKER') return 'Joker'
    const [, suit, rank] = name.split('_')
    const pretty = (word: string) => word.charAt(0) + word.slice(1).toLowerCase()
    return `${pretty(rank)} of ${pretty(suit)}s`
}

/** Warms the browser cache so a scanned card renders without a network round trip. */
export function preloadCardImages(): void {
    for (const url of Object.values(cardImages)) {
        const image = new Image()
        image.src = url
    }
}
