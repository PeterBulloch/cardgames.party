// Web NFC is not in TypeScript's DOM lib; this covers only the read path we use.
interface NDEFRecord {
    readonly recordType: string
    readonly mediaType?: string
    readonly id?: string
    readonly data?: DataView
    readonly encoding?: string
    readonly lang?: string
}

interface NDEFMessage {
    readonly records: readonly NDEFRecord[]
}

interface NDEFReadingEvent extends Event {
    readonly serialNumber: string
    readonly message: NDEFMessage
}

interface NDEFReaderEventMap {
    reading: NDEFReadingEvent
    readingerror: Event
}

declare class NDEFReader extends EventTarget {
    constructor()
    scan(options?: { signal?: AbortSignal }): Promise<void>
    addEventListener<K extends keyof NDEFReaderEventMap>(
        type: K,
        listener: (event: NDEFReaderEventMap[K]) => void,
        options?: boolean | AddEventListenerOptions,
    ): void
    removeEventListener<K extends keyof NDEFReaderEventMap>(
        type: K,
        listener: (event: NDEFReaderEventMap[K]) => void,
        options?: boolean | EventListenerOptions,
    ): void
}
