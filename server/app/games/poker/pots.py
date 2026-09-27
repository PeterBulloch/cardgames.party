from dataclasses import dataclass


@dataclass
class Pot:
    amount: int
    eligible: list[str]


def build_pots(contributions: dict[str, int], live: list[str], all_in: set[str]) -> list[Pot]:
    """Main pot then side pots; an all-in player is only eligible up to what they put in."""
    pots: list[Pot] = []
    previous = 0
    for layer in sorted({amount for amount in contributions.values() if amount > 0}):
        amount = sum(min(c, layer) - min(c, previous) for c in contributions.values())
        eligible = [seat for seat in live if seat not in all_in or contributions.get(seat, 0) >= layer]
        # Chips above every live player's stake (from folders) stay with the pot below.
        if pots and (not eligible or pots[-1].eligible == eligible):
            pots[-1].amount += amount
        else:
            pots.append(Pot(amount, eligible))
        previous = layer
    return pots


def split(amount: int, winners: list[str]) -> dict[str, int]:
    """Equal shares; odd chips go to winners in the given order (clockwise from the button)."""
    share, remainder = divmod(amount, len(winners))
    return {seat: share + (1 if index < remainder else 0) for index, seat in enumerate(winners)}
