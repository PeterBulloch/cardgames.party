import { useCallback, useEffect, useRef, useState } from 'react'

export type WriterStatus = 'unsupported' | 'idle' | 'writing' | 'written' | 'error'

const isSupported = typeof window !== 'undefined' && 'NDEFReader' in window

export function useNfcWriter() {
    const [status, setStatus] = useState<WriterStatus>(isSupported ? 'idle' : 'unsupported')
    const [error, setError] = useState<string | null>(null)
    const abortRef = useRef<AbortController | null>(null)

    const cancel = useCallback(() => {
        abortRef.current?.abort()
        abortRef.current = null
        setStatus((current) => (current === 'writing' ? 'idle' : current))
    }, [])

    const write = useCallback(async (text: string) => {
        if (!isSupported || abortRef.current) return

        const controller = new AbortController()
        abortRef.current = controller
        setError(null)
        setStatus('writing')

        try {
            // Resolves only once a tag is actually tapped, so this stays pending until then.
            await new NDEFReader().write(
                { records: [{ recordType: 'text', data: text }] },
                { overwrite: true, signal: controller.signal },
            )
            setStatus('written')
        } catch (cause) {
            if (controller.signal.aborted) return
            setStatus('error')
            setError(cause instanceof Error ? cause.message : 'Failed to write the tag.')
        } finally {
            abortRef.current = null
        }
    }, [])

    useEffect(() => () => abortRef.current?.abort(), [])

    return { status, error, write, cancel, isSupported }
}
