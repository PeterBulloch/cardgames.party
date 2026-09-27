from typing import Any, ClassVar

from pydantic import TypeAdapter, ValidationError

from .player import Player


class ActionError(Exception):
    """An action that is well-formed but not allowed in the current game state."""


# Base class for all games
class Game:
    key: ClassVar[str] = ""
    label: ClassVar[str] = ""
    stages: ClassVar[tuple[str, ...]] = ()
    min_players: ClassVar[int] = 1
    max_players: ClassVar[int] = 10
    actions: ClassVar[TypeAdapter[Any]]

    def __init__(self) -> None:
        self.stage_index = 0

    def parse_action(self, raw: dict[str, Any]) -> object:
        try:
            return self.actions.validate_python(raw)
        except ValidationError as error:
            raise ActionError(error.errors()[0]["msg"]) from None

    @property
    def current_stage(self) -> str:
        return self.stages[self.stage_index]

    def next_stage(self) -> None:
        if self.stage_index >= len(self.stages) - 1:
            raise ActionError("Already at the final stage; start a new hand")
        self.stage_index += 1

    def add_seat(self, member_id: str) -> None:
        raise NotImplementedError

    def remove_seat(self, member_id: str) -> None:
        raise NotImplementedError

    def apply(self, action: object, actor: Player) -> None:
        raise NotImplementedError

    def view_for(self, viewer: Player) -> dict:
        raise NotImplementedError