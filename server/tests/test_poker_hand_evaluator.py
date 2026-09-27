from app.games.poker.hand_evaluator import best_hand, category_name


def score(cards: str) -> tuple[int, ...]:
    return best_hand([f"CARD_{card}" for card in cards.split()])[0]


def test_hand_categories() -> None:
    assert category_name(score("SPADE_ACE SPADE_KING SPADE_QUEEN SPADE_JACK SPADE_TEN HEART_TWO CLUB_THREE"))\
        == "Straight Flush"
    assert category_name(score("SPADE_ACE HEART_TWO CLUB_THREE DIAMOND_FOUR SPADE_FIVE HEART_NINE CLUB_KING"))\
        == "Straight"
    assert category_name(score("SPADE_TWO HEART_TWO CLUB_TWO DIAMOND_KING SPADE_KING HEART_NINE CLUB_FOUR"))\
        == "Full House"


def test_kickers_break_ties() -> None:
    assert score("SPADE_ACE HEART_ACE CLUB_KING DIAMOND_FOUR SPADE_THREE") > \
        score("DIAMOND_ACE CLUB_ACE HEART_QUEEN SPADE_FOUR HEART_THREE")
    assert score("SPADE_FIVE HEART_FOUR CLUB_THREE DIAMOND_TWO SPADE_ACE") < \
        score("SPADE_SIX HEART_FIVE CLUB_FOUR DIAMOND_THREE SPADE_TWO")
