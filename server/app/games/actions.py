from typing import Literal

from ..models import Strict


class Undo(Strict):
    type: Literal["undo"]
