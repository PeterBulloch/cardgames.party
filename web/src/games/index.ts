import type { GameDefinition } from './types'
import TexasHoldEmTable from './texasHoldEm/TexasHoldEmTable'
import type { TexasHoldEmAction, TexasHoldEmView } from './texasHoldEm/types'

const texasHoldEm: GameDefinition<TexasHoldEmView, TexasHoldEmAction> = {
    key: 'texas_hold_em',
    label: "Texas Hold'em",
    minPlayers: 2,
    maxPlayers: 10,
    Table: TexasHoldEmTable,
}

// Each entry pairs its own view and action types, which the lobby shell does not need to know.
export const games: GameDefinition<any, any>[] = [texasHoldEm]

export function findGame(key: string) {
    return games.find((game) => game.key === key)
}
