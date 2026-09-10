import { useCallback, useEffect, useRef, useState } from 'react'
import type { NdefRecordDto } from './types'

export type ScannerStatus = 'unsupported' | 'idle' | 'scanning' | 'error'

const DUPLICATE_WINDOW_MS = 2000

const isSupported = typeof window !== 'undefined' && 'NDEFReader' in window

function decodeRecords(message: NDEFMessage): NdefRecordDto[] {
    return message.records.slice(0, 16).map((record) => {
        let text: string | null = null
        if (record.data && (record.recordType === 'text' || record.recordType === 'url')) {
            try {
                text = new TextDecoder(record.encoding ?? 'utf-8').decode(record.data).slice(0, 2048)
            } catch {
                text = null
            }
        }
        return { recordType: record.recordType, mediaType: record.mediaType ?? null, text }
    })
}

export function useNfcScanner(onScan: (serialNumber: string, records: NdefRecordDto[]) => void) {
    const [status, setStatus] = useState<ScannerStatus>(isSupported ? 'idle' : 'unsupported')
    const [error, setError] = useState<string | null>(null)
    const abortRef = useRef<AbortController | null>(null)
    const lastSeenRef = useRef(new Map<string, number>())
    const onScanRef = useRef(onScan)

    onScanRef.current = onScan

    const stop = useCallback(() => {
        abortRef.current?.abort()
        abortRef.current = null
        setStatus((current) => (current === 'scanning' ? 'idle' : current))
    }, [])

    const start = useCallback(async () => {
        if (!isSupported || abortRef.current) return

        const controller = new AbortController()
        abortRef.current = controller
        setError(null)

        try {
            const ndef = new NDEFReader()

            ndef.addEventListener(
                'reading',
                ({ serialNumber, message }) => {
                    // Holding a tag against the phone fires `reading` repeatedly.
                    const now = Date.now()
                    const previous = lastSeenRef.current.get(serialNumber)
                    if (previous !== undefined && now - previous < DUPLICATE_WINDOW_MS) return
                    lastSeenRef.current.set(serialNumber, now)

                    onScanRef.current(serialNumber, decodeRecords(message))
                },
                { signal: controller.signal },
            )

            ndef.addEventListener(
                'readingerror',
                () => setError('Could not read that tag. Try repositioning it.'),
                { signal: controller.signal },
            )

            // Must be called from a user gesture, and throws if permission is denied.
            await ndef.scan({ signal: controller.signal })
            setStatus('scanning')
        } catch (cause) {
            abortRef.current = null
            setStatus('error')
            setError(cause instanceof Error ? cause.message : 'Failed to start scanning.')
        }
    }, [])

    useEffect(() => () => abortRef.current?.abort(), [])

    return { status, error, start, stop, isSupported }
}
