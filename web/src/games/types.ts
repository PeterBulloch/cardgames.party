import type { ComponentType } from 'react'
import type { GameAction, LobbyState } from '../types'

export interface GameTableProps<G, A extends GameAction> {
    state: LobbyState<G>
    send: (action: A) => void
}

export interface GameDefinition<G = unknown, A extends GameAction = GameAction> {
    key: string
    label: string
    minPlayers: number
    maxPlayers: number
    Table: ComponentType<GameTableProps<G, A>>
}
