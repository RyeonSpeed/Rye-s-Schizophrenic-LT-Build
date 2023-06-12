from app.engine.objects.item import ItemObject
from app.utilities.data import Prefab

from app.engine.game_state import game
from typing import List, Optional
from app.utilities.typing import NID

class AIGroupObject(Prefab):
    def __init__(self, nid: NID, trigger_threshold: int = 1):
        self.nid = nid
        self.trigger_threshold = trigger_threshold
        self.active: bool = False
        # Cleared at the end of an AI phase
        self.triggered = set()

    def trigger(self, unit_nid: NID) -> bool:
        """
        # Returns whether this trigger has finally triggered the number of units required for the ai group to fire
        """
        self.triggered.add(unit_nid)
        return len(self.triggered) >= self.trigger_threshold

    def clear(self):
        self.triggered.clear()

    def save(self):
        return {'nid': self.nid,
                'trigger_threshold': self.trigger_threshold,
                'active': self.active,
        }

    @classmethod
    def restore(cls, s_dict):
        ai_group = cls(s_dict['nid'], s_dict['trigger_threshold']. s_dict['active'])
        return ai_group
