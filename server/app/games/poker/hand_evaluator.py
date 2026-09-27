from collections import Counter
from itertools import combinations

from ..cards import suit_and_rank

# Poker ranks aces high; the ace-low straight is handled separately below.
RANK_VALUE = {
    "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7, "EIGHT": 8,
    "NINE": 9, "TEN": 10, "JACK": 11, "QUEEN": 12, "KING": 13, "ACE": 14,
}

CATEGORY_NAMES = [
    "High Card", "Pair", "Two Pair", "Three of a Kind", "Straight",
    "Flush", "Full House", "Four of a Kind", "Straight Flush",
]


def parse(card: str) -> tuple[int, str]:
    suit, rank = suit_and_rank(card)
    return RANK_VALUE[rank], suit


def _score_five(cards: tuple[str, ...]) -> tuple[int, ...]:
    parsed = [parse(card) for card in cards]
    values = sorted((value for value, _ in parsed), reverse=True)
    is_flush = len({suit for _, suit in parsed}) == 1

    unique = sorted(set(values), reverse=True)
    straight_high = None
    if len(unique) == 5:
        if unique[0] - unique[4] == 4:
            straight_high = unique[0]
        elif unique == [14, 5, 4, 3, 2]:
            straight_high = 5

    # Sort by count then value so the tuple compares kickers correctly.
    grouped = sorted(Counter(values).items(), key=lambda item: (item[1], item[0]), reverse=True)
    counts = [count for _, count in grouped]
    ordered = [value for value, _ in grouped]

    if straight_high and is_flush:
        return (8, straight_high)
    if counts[0] == 4:
        return (7, *ordered)
    if counts[:2] == [3, 2]:
        return (6, *ordered)
    if is_flush:
        return (5, *values)
    if straight_high:
        return (4, straight_high)
    if counts[0] == 3:
        return (3, *ordered)
    if counts[:2] == [2, 2]:
        return (2, *ordered)
    if counts[0] == 2:
        return (1, *ordered)
    return (0, *values)


def best_hand(cards: list[str]) -> tuple[tuple[int, ...], list[str]]:
    """Best 5-card score and the cards making it, from 5 to 7 cards."""
    if len(cards) < 5:
        raise ValueError("At least five cards are required")
    return max(
        ((_score_five(combo), list(combo)) for combo in combinations(cards, 5)),
        key=lambda item: item[0],
    )


def category_name(score: tuple[int, ...]) -> str:
    return CATEGORY_NAMES[score[0]]
