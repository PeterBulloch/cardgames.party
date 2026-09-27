export type Target = { kind: 'seat'; member_id: string } | { kind: 'board' } | { kind: 'burn' }

export type TexasHoldEmAction =
    | { type: 'deal_card'; card: string; target: Target }
    | { type: 'return_card'; card: string }
    | { type: 'fold'; member_id: string }
    | { type: 'unfold'; member_id: string }
    | { type: 'next_stage' }
    | { type: 'new_hand' }

export interface SeatView {
    member_id: string
    folded: boolean
    card_count: number
    /** Null when the viewer is not allowed to see this hand. */
    cards: string[] | null
}

export interface ShowdownView {
    complete: boolean
    winners: string[]
    results: { member_id: string; hand_name: string; best_cards: string[] }[]
}

export interface TexasHoldEmView {
    stage: string
    stages: string[]
    board_limit: number
    board: string[]
    burn: { count: number; cards: string[] | null }
    seats: SeatView[]
    showdown: ShowdownView | null
}
