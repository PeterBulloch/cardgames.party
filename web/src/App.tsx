import { useCallback, useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { clearScans, fetchScans, postScan } from './api'
import { useNfcScanner } from './useNfcScanner'
import type { NdefRecordDto, Scan } from './types'

const POLL_INTERVAL_MS = 2000

const shareUrl = window.location.origin
// A loopback origin encodes a URL no other device can reach.
const isLoopback = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)

function mergeScan(scans: Scan[], incoming: Scan): Scan[] {
    return scans.some((scan) => scan.id === incoming.id) ? scans : [incoming, ...scans]
}

export default function App() {
    const [scans, setScans] = useState<Scan[]>([])
    const [apiError, setApiError] = useState<string | null>(null)

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
                        {scans.map((scan) => (
                            <li key={scan.id}>
                                <code>{scan.serialNumber}</code>
                                <time dateTime={scan.receivedAt}>
                                    {new Date(scan.receivedAt).toLocaleTimeString()}
                                </time>
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
                            </li>
                        ))}
                    </ul>
                )}
            </section>

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
