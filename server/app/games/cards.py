SUITS = ("SPADE", "HEART", "DIAMOND", "CLUB")
RANKS = (
    "ACE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
    "JACK", "QUEEN", "KING",
)
JOKER = "CARD_JOKER"

STANDARD_DECK = frozenset(f"CARD_{suit}_{rank}" for suit in SUITS for rank in RANKS)


def suit_and_rank(card: str) -> tuple[str, str]:
    _, suit, rank = card.split("_")
    return suit, rank
