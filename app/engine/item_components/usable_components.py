from app.data.item_components import ItemComponent
from app.data.components import Type

from app.engine import action

class Uses(ItemComponent):
    nid = 'uses'
    desc = "Number of uses of item"
    tag = 'uses'

    expose = Type.Int
    value = 1

    def init(self, item):
        item.data['uses'] = self.value
        item.data['starting_uses'] = self.value

    def available(self, unit, item) -> bool:
        return item.data['uses'] > 0

    def is_broken(self, unit, item) -> bool:
        return item.data['uses'] <= 0

    def on_hit(self, actions, playback, unit, item, target, mode):
        actions.append(action.SetObjData(item, 'uses', item.data['uses'] - 1))
        actions.append(action.UpdateRecords('item_use', (unit.nid, item.nid)))

    def on_miss(self, actions, playback, unit, item, target, mode):
        actions.append(action.SetObjData(item, 'uses', item.data['uses'] - 1))
        actions.append(action.UpdateRecords('item_use', (unit.nid, item.nid)))

    def on_broken(self, unit, item):
        action.do(action.RemoveItem(unit, item))
        return True

    def special_sort(self, unit, item):
        return item.data['uses']

class ChapterUses(ItemComponent):
    nid = 'c_uses'
    desc = "Number of uses per chapter for item. (Refreshes after each chapter)"
    tag = 'uses'

    expose = Type.Int
    value = 1

    def init(self, item):
        item.data['c_uses'] = self.value
        item.data['starting_c_uses'] = self.value

    def available(self, unit, item) -> bool:
        return item.data['c_uses'] > 0

    def is_broken(self, unit, item) -> bool:
        return item.data['c_uses'] <= 0

    def on_hit(self, actions, playback, unit, item, target, mode=None):
        actions.append(action.SetObjData(item, 'c_uses', item.data['c_uses'] - 1))
        actions.append(action.UpdateRecords('item_use', (unit.nid, item.nid)))

    def on_miss(self, actions, playback, unit, item, target, mode=None):
        actions.append(action.SetObjData(item, 'c_uses', item.data['c_uses'] - 1))
        actions.append(action.UpdateRecords('item_use', (unit.nid, item.nid)))

    def on_broken(self, unit, item):
        if unit.equipped_weapon is item:
            action.do(action.UnequipItem(unit, item))
        return True

    def on_end_chapter(self, unit, item):
        # Don't need to use action here because it will be end of chapter
        item.data['c_uses'] = item.data['starting_c_uses']

    def special_sort(self, unit, item):
        return item.data['c_uses']

class HPCost(ItemComponent):
    nid = 'hp_cost'
    desc = "Item costs HP to use"
    tag = 'uses'

    expose = Type.Int
    value = 1

    def available(self, unit, item) -> bool:
        return unit.get_hp() > self.value

    def start_combat(self, playback, unit, item, target):
        action.do(action.ChangeHP(unit, -self.value))

class ManaCost(ItemComponent):
    nid = 'mana_cost'
    desc = "Item costs mana to use"
    tag = 'uses'

    expose = Type.Int
    value = 1

    def available(self, unit, item) -> bool:
        return unit.get_mana() > self.mana_cost

    def start_combat(self, playback, unit, item, target):
        action.do(action.ChangeMana(unit, -self.value))

class Cooldown(ItemComponent):
    nid = 'cooldown'
    desc = "After use, item cannot be used until X turns have passed"
    tag = 'uses'

    expose = Type.Int
    value = 1

    def init(self, item):
        item.data['cooldown'] = 0
        item.data['starting_cooldown'] = self.value
        self._used_in_combat = False

    def available(self, unit, item) -> bool:
        return item.data['cooldown'] == 0

    def is_broken(self, unit, item) -> bool:
        return item.data['cooldown'] != 0

    def on_hit(self, actions, playback, unit, item, target, mode):
        self._used_in_combat = True

    def on_miss(self, actions, playback, unit, item, target, mode):
        self._used_in_combat = True

    def end_combat(self, playback, unit, item, target):
        if self._used_in_combat:
            action.do(action.SetObjData(item, 'cooldown', self.value))
            self._used_in_combat = False

    def on_broken(self, unit, item):
        if unit.equipped_weapon is item:
            action.do(action.UnequipItem(unit, item))
        return False

    def on_upkeep(self, actions, playback, unit, item):
        if item.data['cooldown'] > 0:
            # Doesn't use actions list in order to prevent 
            # requiring the status phase to show health bar
            action.do(action.SetObjData(item, 'cooldown', item.data['cooldown'] - 1))

    def on_end_chapter(self, unit, item):
        # Don't need to use action here because it will be end of chapter
        item.data['cooldown'] = 0

class PrfUnit(ItemComponent):
    nid = 'prf_unit'
    desc = 'Item can only be wielded by certain units'
    tag = 'uses'

    expose = (Type.List, Type.Unit)

    def available(self, unit, item) -> bool:
        return unit.nid in self.value

class PrfClass(ItemComponent):
    nid = 'prf_class'
    desc = 'Item can only be wielded by certain classes'
    tag = 'uses'

    expose = (Type.List, Type.Class)

    def available(self, unit, item) -> bool:
        return unit.klass in self.value

class PrfTag(ItemComponent):
    nid = 'prf_tags'
    desc = 'Item can only be wielded by units with certain tags'
    tag = 'uses'

    expose = (Type.List, Type.Tag)

    def available(self, unit, item) -> bool:
        return any(tag in self.value for tag in unit.tags)

class Locked(ItemComponent):
    nid = 'locked'
    desc = 'Item cannot be discarded, traded, or stolen'
    tag = 'extra'

    def locked(self, unit, item) -> bool:
        return True

class CanUnlock(ItemComponent):
    nid = 'can_unlock'
    desc = "Item can be used to unlock events. String will be evaluated to determine kind of event"
    tag = 'extra'

    expose = Type.String
    value = 'True'

    def can_unlock(self, unit, item, region) -> bool:
        from app.engine import evaluate
        try:
            return bool(evaluate.evaluate(self.value, unit, item, region=region))
        except:
            print("Could not evaluate %s" % self.value)
        return False
