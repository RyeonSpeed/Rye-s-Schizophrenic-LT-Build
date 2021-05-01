from app.data.item_components import ItemComponent
from app.data.components import Type

class MapHitAddBlend(ItemComponent):
    nid = 'map_hit_add_blend'
    desc = "Changes the color that appears on the unit when hit -- Use to make brighter"
    tag = 'aesthetic'

    expose = Type.Color3
    value = (255, 255, 255)

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        playback.append(('unit_tint_add', target, self.value))

class MapHitSubBlend(ItemComponent):
    nid = 'map_hit_sub_blend'
    desc = "Changes the color that appears on the unit when hit -- Use to make darker"
    tag = 'aesthetic'

    expose = Type.Color3
    value = (0, 0, 0)

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        playback.append(('unit_tint_sub', target, self.value))

class MapHitSFX(ItemComponent):
    nid = 'map_hit_sfx'
    desc = "Changes the sound the item will make on hit"
    tag = 'aesthetic'

    expose = Type.Sound
    value = 'Attack Hit 1'

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        playback.append(('hit_sound', self.value))

class MapCastSFX(ItemComponent):
    nid = 'map_cast_sfx'
    desc = "Adds a sound to the item on cast"
    tag = 'aesthetic'

    expose = Type.Sound
    value = 'Attack Hit 1'

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        playback.append(('cast_sound', self.value))

    def on_miss(self, actions, playback, unit, item, target, target_pos, mode):
        playback.append(('cast_sound', self.value))

class MapCastAnim(ItemComponent):
    nid = 'map_cast_anim'
    desc = "Adds a map animation to the item on cast"
    tag = 'aesthetic'

    expose = Type.MapAnimation

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        playback.append(('cast_anim', self.value))

    def on_miss(self, actions, playback, unit, item, target, target_pos, mode):
        playback.append(('cast_anim', self.value))

class Warning(ItemComponent):
    nid = 'warning'
    desc = "Yellow warning sign appears above wielder's head"
    tag = 'aesthetic'

    def warning(self, unit, item, target) -> bool:
        return True

class EvalWarning(ItemComponent):
    nid = 'eval_warning'
    desc = "Yellow warning sign appears above wielder's head if current unit meets eval"
    tag = 'aesthetic'

    expose = Type.String
    value = 'True'

    def warning(self, unit, item, target) -> bool:
        from app.engine import evaluate
        try:
            val = evaluate.evaluate(self.value, unit, target, item)
            return bool(val)
        except Exception as e:
            print("Could not evaluate %s (%s)" % (self.value, e))
            return False
