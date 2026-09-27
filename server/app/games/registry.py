from .game import Game
from .poker.texas_hold_em import TexasHoldEm

GAMES: dict[str, type[Game]] = {game.key: game for game in (TexasHoldEm,)}
