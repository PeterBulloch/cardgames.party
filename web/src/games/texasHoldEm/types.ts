export type BetKind = 'fold' | 'check' | 'call' | 'bet' | 'raise'

export type TexasHoldEmAction =
    | { type: 'start_hand' }
    | { type: 'deal_card'; card: string }
    | { type: BetKind; member_id: string }
    | { type: 'undo' }

export type DealTarget = { kind: 'seat'; member_id: string } | { kind: 'board' } | { kind: 'burn' }

export interface SeatView {
    member_id: string
    in_hand: boolean
    folded: boolean
    card_count: number
    /** Null when the viewer is not allowed to see this hand. */
    cards: string[] | null
}

export interface HandResult {
    uncontested: boolean
    winners: string[]
    results: { member_id: string; hand_name: string; best_cards: string[] }[]
}

export interface TexasHoldEmView {
    phase: 'waiting' | 'dealing' | 'betting' | 'complete'
    stage: string
    stages: string[]
    hand_number: number
    button: string | null
    small_blind: string | null
    big_blind: string | null
    dealer: { member_id: string; dedicated: boolean } | null
    to_act: string | null
    legal_bets: BetKind[]
    next_deal: DealTarget | null
    can_start_hand: boolean
    can_undo: boolean
    board: string[]
    burn: { count: number; cards: string[] | null }
    seats: SeatView[]
    result: HandResult | null
}
