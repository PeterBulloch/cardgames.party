import secrets
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["player", "dealer", "observer"]


# A member of a lobby, whether seated or watching.
@dataclass(eq=False)
class Player:
    name: str
    role: Role
    id: str = field(default_factory=lambda: secrets.token_hex(6))
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32), repr=False)
    connections: int = 0
    hide_hands: bool = False

    @property
    def can_act(self) -> bool:
        return self.role in ("player", "dealer")

    @property
    def is_seated(self) -> bool:
        return self.role == "player"

    @property
    def sees_all(self) -> bool:
        return self.role == "dealer" or (self.role == "observer" and not self.hide_hands)