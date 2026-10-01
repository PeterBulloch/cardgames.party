import { useCallback, useEffect, useState } from 'react'
import { clearScans, fetchScans, postScan } from './api'
import { cardImages, cardLabel, cardNameFor, cardNames, preloadCardImages } from './cards'
import CardPicker from './CardPicker'
import { useNfcScanner } from './useNfcScanner'
import { useNfcWriter } from './useNfcWriter'
import type { NdefRecordDto, Scan } from './types'

const POLL_INTERVAL_MS = 2000
const standardDeck = cardNames.filter((name) => name !== 'CARD_JOKER')
const noUnavailableCards = new Set<string>()

function mergeScan(scans: Scan[], incoming: Scan): Scan[] {
    return scans.some((scan) => scan.id === incoming.id) ? scans : [incoming, ...scans]
}

export default function ScannerPage() {
    const [scans, setScans] = useState<Scan[]>([])
    const [apiError, setApiError] = useState<string | null>(null)
    const [cardToWrite, setCardToWrite] = useState<string | null>(standardDeck[0] ?? null)

    const handleScan = useCallback(async (serialNumber: string, records: NdefRecordDto[]) => {
        try {
            const saved = await postScan({ serialNumber, records })
            setScans((current) => mergeScan(current, saved))
            setApiError(null)
        } catch (cause) {
            setApiError(cause instanceof Error ? cause.message : 'Failed to save scan.')
        }
    }, [])

    const { status, error, start, stop, isSupported } = useNfcScanner(handleScan)
    const writer = useNfcWriter()

    useEffect(preloadCardImages, [])

    useEffect(() => {
        let cancelled = false

        const load = async () => {
            try {
                const latest = await fetchScans()
                if (!cancelled) {
                    setScans(latest.slice().reverse())
                    setApiError(null)
                }
            } catch (cause) {
                if (!cancelled) {
                    setApiError(cause instanceof Error ? cause.message : 'Failed to load scans.')
                }
            }
        }

        void load()
        const timer = setInterval(load, POLL_INTERVAL_MS)
        return () => {
            cancelled = true
            clearInterval(timer)
        }
    }, [])

    const handleClear = async () => {
        try {
            await clearScans()
            setScans([])
        } catch (cause) {
            setApiError(cause instanceof Error ? cause.message : 'Failed to clear scans.')
        }
    }

    const scannedCards = scans.flatMap((scan) => {
        const name = cardNameFor(scan)
        return name && cardImages[name] ? [{ scan, name }] : []
    })

    return (
        <main className="app app--scanner">
            <header>
                <h1>Card tag setup</h1>
                <p className="status">Write and test the NFC tags used to identify your playing cards.</p>
            </header>

            <section className={`support-notice ${isSupported ? 'support-notice--ready' : ''}`}>
                <h2>Supported devices</h2>
                <p>
                    This setup tool only works in Chrome on an NFC-capable Android device over HTTPS.
                    {!isSupported && ' Web NFC is not available on this device or browser.'}
                </p>
            </section>

            <section className="setup-guide">
                <h2>Set up your deck</h2>
                <ol>
                    <li>Buy 52 small rewritable NFC or RFID stickers.</li>
                    <li>Place one sticker on the face of each playing card.</li>
                    <li>Pick the matching card below, tap Write tag, then hold its sticker to your phone.</li>
                </ol>
            </section>

            <section className="scanner-section">
                <h2>Write a card</h2>
                <CardPicker
                    cards={standardDeck}
                    unavailable={noUnavailableCards}
                    value={cardToWrite}
                    onChange={setCardToWrite}
                />
                <div className="controls">
                    {writer.status === 'writing' ? (
                        <button type="button" className="secondary" onClick={writer.cancel}>
                            Cancel
                        </button>
                    ) : (
                        <button
                            type="button"
                            onClick={() => cardToWrite && void writer.write(cardToWrite)}
                            disabled={!writer.isSupported || !cardToWrite}
                        >
                            Write tag
                        </button>
                    )}
                </div>
                <p className="status">
                    {writer.status === 'unsupported' && 'Writing is unavailable on this device.'}
                    {writer.status === 'idle' && 'Choose a card before writing its sticker.'}
                    {writer.status === 'writing' && 'Hold the sticker to the back of your phone.'}
                    {writer.status === 'written' && cardToWrite && `Wrote ${cardLabel(cardToWrite)}.`}
                    {writer.status === 'error' && 'The tag could not be written.'}
                </p>
                {writer.error && <p className="error">{writer.error}</p>}
            </section>

            <section className="scanner-section">
                <h2>
                    Test reading <span className="count">{scannedCards.length}</span>
                </h2>
                <p className={`status status--${status}`}>
                    {status === 'unsupported' && 'Reading is unavailable on this device.'}
                    {status === 'idle' && 'Start reading, then hold a tagged card to your phone.'}
                    {status === 'scanning' && 'Reading cards. Hold a tagged card to your phone.'}
                    {status === 'error' && 'Reading stopped.'}
                </p>
                {(error || apiError) && <p className="error">{error ?? apiError}</p>}
                <div className="controls">
                    {status === 'scanning' ? (
                        <button type="button" onClick={stop}>
                            Stop reading
                        </button>
                    ) : (
                        <button type="button" onClick={() => void start()} disabled={!isSupported}>
                            Start reading
                        </button>
                    )}
                    <button type="button" className="secondary" onClick={() => void handleClear()}>
                        Clear cards
                    </button>
                </div>
                {scannedCards.length === 0 ? (
                    <p className="empty">No cards read yet.</p>
                ) : (
                    <ul className="scans">
                        {scannedCards.map(({ scan, name }) => (
                            <li key={scan.id}>
                                <figure className="card">
                                    <img src={cardImages[name]} alt={cardLabel(name)} />
                                    <figcaption>{cardLabel(name)}</figcaption>
                                </figure>
                            </li>
                        ))}
                    </ul>
                )}
            </section>
        </main>
    )
}
