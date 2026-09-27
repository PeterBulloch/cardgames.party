import copy
from typing import Any, ClassVar

from pydantic import TypeAdapter, ValidationError

from .actions import Undo
from .player import Player

UNDO_LIMIT = 30


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
        self._history: list[dict[str, Any]] = []

    def parse_action(self, raw: dict[str, Any]) -> object:
        try:
            if raw.get("type") == "undo":
                return Undo.model_validate(raw)
            return self.actions.validate_python(raw)
        except ValidationError as error:
            raise ActionError(error.errors()[0]["msg"]) from None

    def perform(self, action: object, actor: Player) -> None:
        """Apply an action, keeping the prior state so it can be undone."""
        if isinstance(action, Undo):
            if not self._history:
                raise ActionError("Nothing to undo")
            self.__dict__.update(self._history.pop())
            return
        before = self._snapshot()
        self.apply(action, actor)
        self._history.append(before)
        del self._history[:-UNDO_LIMIT]

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def _snapshot(self) -> dict[str, Any]:
        return copy.deepcopy({key: value for key, value in self.__dict__.items() if key != "_history"})

    # Membership changes invalidate history, since undo must not resurrect or drop a seat.
    def add_member(self, member: Player) -> None:
        self._history.clear()
        if member.is_seated:
            self.add_seat(member.id)

    def remove_member(self, member: Player) -> None:
        self._history.clear()
        if member.is_seated:
            self.remove_seat(member.id)

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