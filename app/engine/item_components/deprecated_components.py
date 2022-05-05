
from __future__ import annotations
from app.data.database import DB

from app.data.components import Type
from app.data.item_components import ItemComponent, ItemTags
from app.engine.game_state import game


class EvalTargetRestrict(ItemComponent):
    nid = 'eval_target_restrict'
    desc = "Use this to restrict what units can be targeted"
    tag = ItemTags.DEPRECATED

    expose = Type.String
    value = 'True'

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        from app.engine import evaluate
        try:
            target = game.board.get_unit(def_pos)
            if target and evaluate.evaluate(self.value, target, position=def_pos):
                return True
            for s_pos in splash:
                target = game.board.get_unit(s_pos)
                if evaluate.evaluate(self.value, target, position=s_pos):
                    return True
        except Exception as e:
            print("Could not evaluate %s (%s)" % (self.value, e))
            return True
        return False

    def simple_target_restrict(self, unit, item):
        from app.engine import evaluate
        try:
            if evaluate.evaluate(self.value, unit):
                return True
        except Exception as e:
            print("Could not evaluate %s (%s)" % (self.value, e))
            return True
        return False

class EventOnUse(ItemComponent):
    nid = 'event_on_use'
    desc = 'Item calls an event on use, before any effects are played'
    tag = ItemTags.DEPRECATED

    expose = Type.Event

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode, attack_info):
        event_prefab = DB.events.get_from_nid(self.value)
        if event_prefab:
            game.events.trigger_specific_event(event_prefab.nid, unit=unit, unit2=target, item=item, position=unit.position, region=target_pos)

class EventAfterUse(ItemComponent):
    nid = 'event_after_use'
    desc = 'Item calls an event after use'
    tag = ItemTags.DEPRECATED

    expose = Type.Event

    _target_pos = None

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode, attack_info):
        self._target_pos = target_pos

    def end_combat(self, playback, unit, item, target, mode):
        event_prefab = DB.events.get_from_nid(self.value)
        if event_prefab:
            game.events.trigger_specific_event(event_prefab.nid, unit=unit, unit2=target, item=item, position=unit.position, region=self._target_pos)
        self._target_pos = None