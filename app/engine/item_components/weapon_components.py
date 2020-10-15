from app.data.database import DB

from app.data.item_components import ItemComponent, Type

from app.engine import action, combat_calcs, equations, item_system, image_mods, engine

class WeaponType(ItemComponent):
    nid = 'weapon_type'
    desc = "Item has a weapon type and can only be used by certain classes"
    tag = 'weapon'

    expose = Type.WeaponType

    def weapon_type(self, unit, item):
        return self.value

    def available(self, unit, item) -> bool:
        klass = DB.classes.get(unit.klass)
        klass_usable = klass.wexp_gain.get(self.value).usable
        return unit.wexp[self.value] > 0 and klass_usable

class WeaponRank(ItemComponent):
    nid = 'weapon_rank'
    desc = "Item has a weapon rank and can only be used by units with high enough rank"
    requires = ['weapon_type']
    tag = 'weapon'

    expose = Type.WeaponRank

    def weapon_rank(self, unit, item):
        return self.value

    def available(self, unit, item):
        required_wexp = DB.weapon_ranks.get(self.value).requirement
        weapon_type = item_system.weapon_type(unit, item)
        if weapon_type:
            return unit.wexp.get(weapon_type) >= required_wexp
        else:  # If no weapon type, then always available
            return True

class Magic(ItemComponent):
    nid = 'magic'
    desc = 'Makes Item use magic damage formula'
    tag = 'weapon'

    def damage_formula(self, unit, item):
        return 'MAGIC_DAMAGE'

    def defense_formula(self, unit, item):
        return 'MAGIC_DEFENSE'

class Hit(ItemComponent):
    nid = 'hit'
    desc = "Item has a chance to hit. If left off, item will always hit."
    tag = 'weapon'

    expose = Type.Int
    value = 75

    def hit(self, unit, item):
        return self.value

class Crit(ItemComponent):
    nid = 'crit'
    desc = "Item has a chance to crit. If left off, item cannot crit."
    tag = 'weapon'

    expose = Type.Int
    value = 0

    def crit(self, unit, item):
        return self.value

class Weight(ItemComponent):
    nid = 'weight'
    desc = "Item has a weight."
    tag = 'weapon'

    expose = Type.Int
    value = 0

    def modify_attack_speed(self, unit, item):
        return -2 * max(0, self.value - equations.parser.constitution(unit))

    def modify_defense_speed(self, unit, item):
        return -2 * max(0, self.value - equations.parser.constitution(unit))

class Effective(ItemComponent):
    nid = 'effective'
    desc = 'Item does extra damage against certain units'
    # requires = ['damage']
    paired_with = ('effective_tag',)
    tag = 'extra'

    expose = Type.Int
    value = 0

    def effective(self, unit, item):
        return self.value

class EffectiveTag(ItemComponent):
    nid = 'effective_tag'
    desc = "Item is does extra damage against units with these tags"
    # requires = ['damage']
    paired_with = ('effective',)
    tag = 'extra'

    expose = (Type.List, Type.Tag)

    def dynamic_damage(self, unit, item, target, mode=None) -> int:
        if any(tag in target.tags for tag in self.value):
            return item_system.effective(unit, item)
        return 0

    def item_icon_mod(self, unit, item, target, sprite):
        if any(tag in target.tags for tag in self.value):
            sprite = image_mods.make_white(sprite.convert_alpha(), abs(250 - engine.get_time()%500)/250) 
        return sprite

class Brave(ItemComponent):
    nid = 'brave'
    desc = "Item multi-attacks"
    tag = 'extra'

    def dynamic_multiattacks(self, unit, item, target, mode=None):
        return 1

class BraveOnAttack(ItemComponent):
    nid = 'brave_on_attack'
    desc = "Item multi-attacks only when attacking"
    tag = 'extra'

    def dynamic_multiattacks(self, unit, item, target, mode=None):
        return 1 if mode == 'Attack' else 0

class CannotBeCountered(ItemComponent):
    nid = 'cannot_be_countered'
    desc = "Item cannot be countered"
    tag = 'extra'

    def can_be_countered(self, unit, item):
        return False

class Lifelink(ItemComponent):
    nid = 'lifelink'
    desc = "Heals user %% of damage dealt"
    # requires = ['damage']
    tag = 'extra'

    expose = Type.Float
    value = 0.5

    def on_hit(self, actions, playback, unit, item, target, mode=None):
        damage = combat_calcs.compute_damage(unit, target, item, mode)
        true_damage = int(damage * self.value)
        actions.append(action.ChangeHP(unit, true_damage))

        # For animation
        playback.append(('heal_hit', unit, item, unit, damage))

    def on_crit(self, actions, playback, unit, item, target, mode=None):
        damage = combat_calcs.compute_damage(unit, target, item, mode)
        true_damage = int(damage * self.value)
        actions.append(action.ChangeHP(unit, true_damage))

        playback.append(('heal_hit', unit, item, unit, damage))

class DamageOnMiss(ItemComponent):
    nid = 'damage_on_miss'
    desc = "Does %% damage even on miss"
    # requires = ['damage']
    tag = 'extra'

    expose = Type.Float
    value = 0.5

    def on_miss(self, actions, playback, unit, item, target, mode=None):
        damage = combat_calcs.compute_damage(unit, target, item, mode)
        true_damage = int(-damage * self.value)

        actions.append(action.ChangeHP(target, true_damage))

        # For animation
        playback.append(('damage_hit', unit, item, target, true_damage))
        if true_damage == 0:
            playback.append(('hit_sound', 'No Damage'))
            playback.append(('hit_anim', 'MapNoDamage', target))        

class NoDouble(ItemComponent):
    nid = 'no_double'
    desc = "Item cannot double"
    tag = 'extra'

    def can_double(self, unit, item):
        return False
