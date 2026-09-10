export interface NdefRecordDto {
    recordType: string
    mediaType?: string | null
    text?: string | null
}

export interface ScanIn {
    serialNumber: string
    records: NdefRecordDto[]
}

export interface Scan extends ScanIn {
    id: number
    receivedAt: string
}
