export type BetKind = 'fold' | 'check' | 'call' | 'bet' | 'raise'

export interface BlindSettings {
    small: number
    big: number
    auto_double: boolean
    double_every: number
}

export type TexasHoldEmAction =
    | { type: 'start_hand' }
    | { type: 'deal_card'; card: string }
    | { type: 'fold' | 'check' | 'call'; member_id: string }
    /** `amount` is the player's total bet this street, not the increment. */
    | { type: 'bet' | 'raise'; member_id: string; amount: number }
    | { type: 'set_chips'; member_id: string; chips: number }
    | { type: 'set_pot'; index: number; amount: number }
    | ({ type: 'set_blinds' } & BlindSettings)
    | { type: 'award_pots' }
    | { type: 'undo' }

export type LegalBet =
    | { type: 'fold' | 'check' }
    | { type: 'call'; amount: number }
    | { type: 'bet' | 'raise'; min: number; max: number }

export interface PotView {
    amount: number
    eligible: string[]
    winners: string[]
}

export type DealTarget = { kind: 'seat'; member_id: string } | { kind: 'board' } | { kind: 'burn' }

export interface SeatView {
    member_id: string
    in_hand: boolean
    folded: boolean
    chips: number
    street_bet: number
    all_in: boolean
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
    blinds: BlindSettings & { hands_until_double: number | null }
    to_act: string | null
    current_bet: number
    legal_bets: LegalBet[]
    next_deal: DealTarget | null
    pots: PotView[]
    awarded: boolean
    can_award: boolean
    can_start_hand: boolean
    can_set_blinds: boolean
    can_undo: boolean
    board: string[]
    burn: { count: number; cards: string[] | null }
    seats: SeatView[]
    result: HandResult | null
}
