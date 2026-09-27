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

export type Role = 'player' | 'dealer' | 'observer'

export interface Session {
    lobby_id: string
    member_id: string
    token: string
}

export interface CreateLobbyIn {
    name: string
    password: string | null
    game: string
    max_players: number
    display_name: string
    role: Role
}

export interface JoinLobbyIn {
    name: string
    password: string | null
    display_name: string
    role: Role
}

export type LobbyAction = { type: 'set_view'; hide_hands: boolean } | { type: 'leave' }

/** Game-specific actions are defined by each game; the lobby only needs the discriminator. */
export interface GameAction {
    type: string
}

export interface LobbyState<G = unknown> {
    lobby: { id: string; name: string; game: string; max_players: number; has_password: boolean }
    you: { member_id: string; name: string; role: Role; hide_hands: boolean; can_act: boolean }
    members: { member_id: string; name: string; role: Role; connected: boolean }[]
    game: G
}

export type ServerMessage =
    | { type: 'state'; version: number; updated_at: string; state: LobbyState }
    | { type: 'ack'; seq: number; version: number }
    | { type: 'error'; seq: number | null; message: string }
