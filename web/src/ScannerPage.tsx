import { useCallback, useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { clearScans, fetchScans, postScan } from './api'
import { cardImages, cardLabel, cardNameFor, cardNames, preloadCardImages } from './cards'
import { useNfcScanner } from './useNfcScanner'
import { useNfcWriter } from './useNfcWriter'
import type { NdefRecordDto, Scan } from './types'

const POLL_INTERVAL_MS = 2000

const shareUrl = window.location.origin
// A loopback origin encodes a URL no other device can reach.
const isLoopback = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)

function mergeScan(scans: Scan[], incoming: Scan): Scan[] {
    return scans.some((scan) => scan.id === incoming.id) ? scans : [incoming, ...scans]
}

export default function ScannerPage() {
    const [scans, setScans] = useState<Scan[]>([])
    const [apiError, setApiError] = useState<string | null>(null)
    const [cardToWrite, setCardToWrite] = useState(cardNames[0] ?? '')

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

    return (
        <main className="app">
            <header>
                <h1>Card Scanner</h1>
                <p className={`status status--${status}`}>
                    {status === 'unsupported' && 'Web NFC is unavailable. Use Chrome on Android over HTTPS.'}
                    {status === 'idle' && 'Ready. Tap Start, then hold a card to the back of the phone.'}
                    {status === 'scanning' && 'Scanning — hold a card to the back of the phone.'}
                    {status === 'error' && 'Scanner stopped.'}
                </p>
            </header>

            {(error || apiError) && <p className="error">{error ?? apiError}</p>}

            <div className="controls">
                {status === 'scanning' ? (
                    <button type="button" onClick={stop}>
                        Stop scanning
                    </button>
                ) : (
                    <button type="button" onClick={() => void start()} disabled={!isSupported}>
                        Start scanning
                    </button>
                )}
                <button type="button" className="secondary" onClick={() => void handleClear()}>
                    Clear
                </button>
            </div>

            <section>
                <h2>
                    Scans <span className="count">{scans.length}</span>
                </h2>
                {scans.length === 0 ? (
                    <p className="empty">No scans yet.</p>
                ) : (
                    <ul className="scans">
                        {scans.map((scan) => {
                            const name = cardNameFor(scan)
                            const image = name ? cardImages[name] : undefined
                            const label = name ? cardLabel(name) : ''
                            return (
                                <li key={scan.id}>
                                    {image ? (
                                        <figure className="card">
                                            <img src={image} alt={label} />
                                            <figcaption>{label}</figcaption>
                                        </figure>
                                    ) : (
                                        <>
                                            <code>{scan.serialNumber}</code>
                                            {scan.records.length > 0 && (
                                                <ul className="records">
                                                    {scan.records.map((record, index) => (
                                                        <li key={index}>
                                                            {record.recordType}
                                                            {record.text ? `: ${record.text}` : ''}
                                                        </li>
                                                    ))}
                                                </ul>
                                            )}
                                        </>
                                    )}
                                    <time dateTime={scan.receivedAt}>
                                        {new Date(scan.receivedAt).toLocaleTimeString()}
                                    </time>
                                </li>
                            )
                        })}
                    </ul>
                )}
            </section>

            <details className="writer">
                <summary>Write a card to a tag</summary>
                <div className="writer__body">
                    {cardToWrite && cardImages[cardToWrite] && (
                        <img
                            className="writer__preview"
                            src={cardImages[cardToWrite]}
                            alt={cardLabel(cardToWrite)}
                        />
                    )}
                    <div className="writer__controls">
                        <select
                            value={cardToWrite}
                            onChange={(event) => setCardToWrite(event.target.value)}
                            disabled={writer.status === 'writing'}
                        >
                            {cardNames.map((name) => (
                                <option key={name} value={name}>
                                    {cardLabel(name)}
                                </option>
                            ))}
                        </select>
                        {writer.status === 'writing' ? (
                            <button type="button" className="secondary" onClick={writer.cancel}>
                                Cancel
                            </button>
                        ) : (
                            <button
                                type="button"
                                onClick={() => void writer.write(cardToWrite)}
                                disabled={!writer.isSupported || !cardToWrite}
                            >
                                Write tag
                            </button>
                        )}
                    </div>
                    <p className="status">
                        {writer.status === 'unsupported' &&
                            'Web NFC is unavailable. Use Chrome on Android over HTTPS.'}
                        {writer.status === 'writing' && 'Hold a blank tag to the back of the phone.'}
                        {writer.status === 'written' && `Wrote ${cardToWrite}.`}
                    </p>
                    {writer.error && <p className="error">{writer.error}</p>}
                </div>
            </details>

            <details className="share">
                <summary>Open on another phone</summary>
                {isLoopback ? (
                    <p className="empty">
                        This page was opened on localhost, so the code would not work on another device.
                        Reload it using the LAN address first.
                    </p>
                ) : (
                    <>
                        <div className="qr">
                            <QRCodeSVG value={shareUrl} size={200} marginSize={2} />
                        </div>
                        <code>{shareUrl}</code>
                    </>
                )}
            </details>
        </main>
    )
}
