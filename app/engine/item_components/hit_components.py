from app.utilities import utils

from app.data.database import DB

from app.data.item_components import ItemComponent
from app.data.components import Type

from app.engine import action, combat_calcs, equations, banner
from app.engine import item_system, skill_system, item_funcs
from app.engine.game_state import game

class Heal(ItemComponent):
    nid = 'heal'
    desc = "Item heals this amount on hit"
    tag = 'weapon'

    expose = Type.Int
    value = 10

    def _get_heal_amount(self, unit):
        return self.value

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Restricts target based on whether any unit has < full hp
        defender = game.board.get_unit(def_pos)
        if defender and defender.get_hp() < equations.parser.hitpoints(defender):
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if s and s.get_hp() < equations.parser.hitpoints(s):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode=None):
        heal = self._get_heal_amount(unit)
        true_heal = min(heal, equations.parser.hitpoints(target) - target.get_hp())
        actions.append(action.ChangeHP(target, heal))

        # For animation
        playback.append(('heal_hit', unit, item, target, heal, true_heal))
        playback.append(('hit_sound', 'MapHeal'))
        if heal >= 30:
            name = 'MapBigHealTrans'
        elif heal >= 15:
            name = 'MapMediumHealTrans'
        else:
            name = 'MapSmallHealTrans'
        playback.append(('hit_anim', name, target))

    def ai_priority(self, unit, item, target, move):
        if skill_system.check_ally(unit, target):
            max_hp = equations.parser.hitpoints(target)
            missing_health = max_hp - target.get_hp()
            help_term = utils.clamp(missing_health / float(max_hp), 0, 1)
            heal = self._get_heal_amount(unit)
            heal_term = utils.clamp(min(heal, missing_health) / float(max_hp), 0, 1)
            return help_term * heal_term
        return 0

class MagicHeal(Heal, ItemComponent):
    nid = 'magic_heal'
    desc = "Item heals this amount + HEAL on hit"

    def _get_heal_amount(self, unit):
        return self.value + equations.parser.heal(unit)

class Damage(ItemComponent):
    nid = 'damage'
    desc = "Item does damage on hit"
    tag = 'weapon'

    expose = Type.Int
    value = 0

    def damage(self, unit, item):
        return self.value

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Restricts target based on whether any unit is an enemy
        defender = game.board.get_unit(def_pos)
        if defender and skill_system.check_enemy(unit, defender):
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if s and skill_system.check_enemy(unit, s):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        damage = combat_calcs.compute_damage(unit, target, item, target.get_weapon(), mode)

        true_damage = min(damage, target.get_hp())
        actions.append(action.ChangeHP(target, -damage))

        # For animation
        playback.append(('damage_hit', unit, item, target, damage, true_damage))
        if damage == 0:
            playback.append(('hit_sound', 'No Damage'))
            playback.append(('hit_anim', 'MapNoDamage', target))

    def on_crit(self, actions, playback, unit, item, target, target_pos, mode):
        damage = combat_calcs.compute_damage(unit, target, item, target.get_weapon(), mode, crit=True)

        true_damage = min(damage, target.get_hp())
        actions.append(action.ChangeHP(target, -damage))

        playback.append(('damage_crit', unit, item, target, damage, true_damage))
        if damage == 0:
            playback.append(('hit_sound', 'No Damage'))
            playback.append(('hit_anim', 'MapNoDamage', target))

class Eclipse(ItemComponent):
    nid = 'Eclipse'
    desc = "Target loses half current HP on hit"
    tag = 'special'

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        true_damage = damage = target.get_hp()//2
        actions.append(action.ChangeHP(target, -damage))

        # For animation
        playback.append(('damage_hit', unit, item, target, damage, true_damage))
        if damage == 0:
            playback.append(('hit_sound', 'No Damage'))
            playback.append(('hit_anim', 'MapNoDamage', target))

class PermanentStatChange(ItemComponent):
    nid = 'permanent_stat_change'
    desc = "Item changes target's stats on hit."
    tag = 'special'

    expose = (Type.Dict, Type.Stat)

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Ignore's splash
        defender = game.board.get_unit(def_pos)
        if not defender:
            return False
        klass = DB.classes.get(defender.klass)
        for stat, inc in self.value:
            if inc <= 0 or defender.stats[stat] < klass.max_stats.get(stat, 30):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode=None):
        stat_changes = {k: v for (k, v) in self.value}
        klass = DB.classes.get(target.klass)
        # clamp stat changes
        stat_changes = {k: utils.clamp(v, -unit.stats[k], klass.max_stats.get(k, 30) - target.stats[k]) for k, v in stat_changes.items()}
        actions.append(action.ApplyStatChanges(target, stat_changes))
        playback.append(('stat_hit', unit, item, target))

    def end_combat(self, playback, unit, item, target):
        # Count number of stat hits
        count = 0
        for p in playback:
            if p[0] == 'stat_hit':
                count += 1
        if count > 0:
            stat_changes = {k: v*count for (k, v) in self.value}
            klass = DB.classes.get(target.klass)
            # clamp stat changes
            stat_changes = {k: utils.clamp(v, -target.stats[k], klass.max_stats.get(k, 30) - target.stats[k]) for k, v in stat_changes.items()}
            game.memory['stat_changes'] = stat_changes
            game.exp_instance.append((target, 0, None, 'stat_booster'))
            game.state.change('exp')

class PermanentGrowthChange(ItemComponent):
    nid = 'permanent_growth_change'
    desc = "Item changes target's growths on hit"
    tag = 'special'

    expose = (Type.Dict, Type.Stat)

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode=None):
        growth_changes = {k: v for (k, v) in self.value}
        actions.append(action.ApplyGrowthChanges(target, growth_changes))
        playback.append(('stat_hit', unit, item, target))

class WexpChange(ItemComponent):
    nid = 'wexp_change'
    desc = "Item changes target's wexp on hit"
    tag = 'special'

    expose = (Type.Dict, Type.WeaponType)

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode=None):
        actions.append(action.WexpChange(unit, self.value))
        playback.append(('hit', unit, item, target))

class Refresh(ItemComponent):
    nid = 'refresh'
    desc = "Item allows target to move again on hit"
    tag = 'special'

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # only targets areas where unit could move again
        defender = game.board.get_unit(def_pos)
        if defender and defender.finished:
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if s.finished:
                return True

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        actions.append(action.Reset(target))
        playback.append(('refresh_hit', unit, item, target))

class StatusOnHit(ItemComponent):
    nid = 'status_on_hit'
    desc = "Item gives status to target when it hits"
    tag = 'special'

    expose = Type.Skill  # Nid

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        act = action.AddSkill(target, self.value, unit)
        actions.append(act)
        playback.append(('status_hit', unit, item, target, self.value))

    def ai_priority(self, unit, item, target, move):
        # Do I add a new status to the target
        if target and self.value not in [skill.nid for skill in target.skills]:
            accuracy_term = utils.clamp(combat_calcs.compute_hit(unit, target, item, target.get_weapon(), "attack")/100., 0, 1)
            num_attacks = combat_calcs.outspeed(unit, target, item, target.get_weapon(), "attack")
            accuracy_term *= num_attacks
            # Tries to maximize distance from target
            distance_term = 0.01 * utils.calculate_distance(move, target.position)
            if skill_system.check_enemy(unit, target):
                return 0.5 * accuracy_term + distance_term
            else:
                return -0.5 * accuracy_term
        return 0

class Restore(ItemComponent):
    nid = 'restore'
    desc = "Item removes all time statuses from target on hit"
    tag = 'special'

    def _can_be_restored(self, status):
        return status.time

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        defender = game.board.get_unit(def_pos)
        # only targets units that need to be restored
        if defender and skill_system.check_ally(unit, defender) and any(self._can_be_restored(skill) for skill in defender.skills):
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if skill_system.check_ally(unit, s) and any(self._can_be_restored(skill) for skill in s.skills):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        for skill in unit.skill:
            if self._can_be_restored(skill):
                actions.append(action.RemoveSkill(unit, skill))
        playback.append(('restore_hit', unit, item, target))

class RestoreSpecific(Restore, ItemComponent):
    nid = 'restore_specific'
    desc = "Item removes status from target on hit"
    tag = 'special'

    expose = Type.Skill # Nid

    def _can_be_restored(self, status):
        return status.nid == self.value

class Shove(ItemComponent):
    nid = 'shove'
    desc = "Item shoves target on hit"
    tag = 'special'

    expose = Type.Int
    value = 1

    def _check_shove(self, unit_to_move, anchor_pos, magnitude):
        offset_x = utils.clamp(unit_to_move.position[0] - anchor_pos[0], -1, 1)
        offset_y = utils.clamp(unit_to_move.position[1] - anchor_pos[1], -1, 1)
        new_position = (unit_to_move.position[0] + offset_x * magnitude,
                        unit_to_move.position[1] + offset_y * magnitude)

        mcost = game.movement.get_mcost(unit_to_move, new_position)
        if game.tilemap.check_bounds(new_position) and \
                not game.board.get_unit(new_position) and \
                mcost <= equations.parser.movement(unit_to_move):
            return new_position
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        if not skill_system.ignore_forced_movement(target):
            new_position = self._check_shove(target, unit.position, self.value)
            if new_position:
                actions.append(action.ForcedMovement(target, new_position))
                playback.append(('shove_hit', unit, item, target))

class ShoveOnEndCombat(Shove):
    nid = 'shove_on_end_combat'
    desc = "Item shoves target at the end of combat"
    tag = 'special'

    expose = Type.Int
    value = 1

    def end_combat(self, playback, unit, item, target):
        if not skill_system.ignore_forced_movement(target):
            new_position = self._check_shove(target, unit.position, self.value)
            if new_position:
                action.do(action.ForcedMovement(target, new_position))

class ShoveTargetRestrict(Shove, ItemComponent):
    nid = 'shove_target_restrict'
    desc = "Target restriction for Shove"
    tag = 'special'

    expose = Type.Int
    value = 1

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # only targets units that need to be restored
        defender = game.board.get_unit(def_pos)
        if defender and self._check_shove(defender, unit.position, self.value) and \
                not skill_system.ignore_forced_movement(defender):
            return True
        for s_pos in splash:
            s = game.board.get_unit(s_pos)
            if self._check_shove(s, unit.position, self.value) and \
                    not skill_system.ignore_forced_movement(s):
                return True
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        pass

    def end_combat(self, playback, unit, item, target):
        pass

class Swap(ItemComponent):
    nid = 'swap'
    desc = "Item swaps user with target on hit"
    tag = 'special'

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        if not skill_system.ignore_forced_movement(unit) and not skill_system.ignore_forced_movement(target):
            actions.append(action.Swap(unit, target))
            playback.append(('swap_hit', unit, item, target))

"""
class Warp(ItemComponent):
    nid = 'warp'
    desc = 'Item warps target to position on hit'
    tag = 'extra'

    def on_hit(self, actions, playback, unit, item, target, mode):
        if not skill_system.ignore_forced_movement(unit):
            actions.append(action.Warp(target, (0, 0)))
            playback.append(('warp_hit', unit, item, target, (0, 0)))
"""

class EvalTargetRestrict(ItemComponent):
    nid = 'eval_target_restrict'
    desc = "Use this to restrict what units can be targeted"
    tag = 'extra'

    expose = Type.String
    value = 'True'

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Restricts target based on whether any unit has < full hp
        from app.engine import evaluate
        try:
            unit = game.board.get_unit(def_pos)
            if unit and evaluate.evaluate(self.value, unit, position=def_pos):
                return True
            for s_pos in splash:
                unit = game.board.get_unit(s_pos)
                if evaluate.evaluate(self.value, unit, position=s_pos):
                    return True
        except:
            return True
        return False

class Steal(ItemComponent):
    nid = 'steal'
    desc = "Steal any unequipped item from target on hit"
    tag = 'special'

    _did_steal = False

    def init(self, item):
        item.data['target_item'] = None

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Unit has item that can be stolen
        attack = equations.parser.steal_atk(unit)
        defender = game.board.get_unit(def_pos)  
        defense = equations.parser.steal_def(defender)
        if attack >= defense:
            for def_item in defender.items:
                if self.item_restrict(unit, item, defender, def_item):
                    return True
        return False

    def ai_targets(self, unit, item):
        positions = set()
        for other in game.units:
            if other.position and skill_system.check_enemy(unit, other):
                for def_item in other.items:
                    if self.item_restrict(unit, item, other, def_item):
                        positions.add(other.position)
                        break
        return positions

    def targets_items(self, unit, item) -> bool:
        return True

    def item_restrict(self, unit, item, defender, def_item) -> bool:
        if item_system.locked(defender, def_item):
            return False
        if item_funcs.inventory_full(unit, def_item):
            return False
        if def_item is defender.get_weapon():
            return False
        return True

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        target_item = item.data.get('target_item')
        if target_item:
            actions.append(action.RemoveItem(target, target_item))
            actions.append(action.DropItem(unit, target_item))
            if unit.team != 'player':
                actions.append(action.MakeItemDroppable(unit, target_item))
            actions.append(action.UpdateRecords('steal', (unit.nid, target.nid, target_item.nid)))
            self._did_steal = True

    def end_combat(self, playback, unit, item, target):
        if self._did_steal:
            target_item = item.data.get('target_item')
            game.alerts.append(banner.StoleItem(unit, target_item))
            game.state.change('alert')
        item.data['target_item'] = None
        self._did_steal = False

    def ai_priority(self, unit, item, target, move):
        if target:
            steal_term = 0.75
            enemy_positions = utils.average_pos({other.position for other in game.units if other.position and skill_system.check_enemy(unit, other)})
            distance_term = utils.calculate_distance(move, enemy_positions)
            return steal_term + 0.01 * distance_term
        return 0

class GBASteal(Steal, ItemComponent):
    nid = 'gba_steal'
    desc = "Steal any non-weapon, non-spell from target on hit"
    tag = 'special'

    def item_restrict(self, unit, item, defender, def_item) -> bool:
        if item_system.locked(defender, def_item):
            return False
        if item_funcs.inventory_full(unit, def_item):
            return False
        if item_system.is_weapon(defender, def_item) or item_system.is_spell(defender, def_item):
            return False
        return True

class Repair(ItemComponent):
    nid = 'repair'
    desc = "Item repairs target item on hit"
    tag = 'special'

    def init(self, item):
        item.data['target_item'] = None

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Unit has item that can be repaired
        defender = game.board.get_unit(def_pos)
        for item in defender.items:
            if item.uses and item.data['uses'] < item.data['starting_uses'] and \
                    not item_system.unrepairable(defender, item):
                return True
        return False

    def targets_items(self, unit, item) -> bool:
        return True

    def item_restrict(self, unit, item, defender, def_item) -> bool:
        if def_item.uses and def_item.data['uses'] < def_item.data['starting_uses'] and \
                not item_system.unrepairable(defender, def_item):
            return True
        return False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        target_item = item.data.get('target_item')
        if target_item:
            actions.append(action.RepairItem(target_item))

    def end_combat(self, playback, unit, item, target):
        item.data['target_item'] = None

class Trade(ItemComponent):
    nid = 'trade'
    desc = "Item allows user to trade with target on hit"
    tag = 'special'

    _did_hit = False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        self._did_hit = True

    def end_combat(self, playback, unit, item, target):
        if self._did_hit and target:
            game.cursor.cur_unit = unit
            game.cursor.set_pos(target.position)
            game.state.change('combat_trade')
        self._did_hit = False

class Promote(ItemComponent):
    nid = 'promote'
    desc = "Item promotes target after hit"
    tag = 'special'

    _did_hit = False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        self._did_hit = True

    def end_combat(self, playback, unit, item, target):
        if self._did_hit and target:
            klass = DB.classes.get(target.klass)
            if len(klass.turns_into) == 0:
                return
            elif len(klass.turns_into) == 1:
                new_klass = klass.turns_into[0]
            else:
                new_klass = None
            game.memory['current_unit'] = target
            game.memory['combat_item'] = item
            game.memory['can_go_back'] = True
            if new_klass:
                game.memory['next_class'] = new_klass
                game.memory['next_state'] = 'promotion'
                game.state.change('transition_to')
            else:
                game.memory['next_state'] = 'promotion_choice'
                game.state.change('transition_to')
        self._did_hit = False

class ForcePromote(Promote, ItemComponent):
    nid = 'force_promote'
    desc = "Item forcibly promotes target to class after hit"
    tag = 'special'

    expose = Type.Class

    def end_combat(self, playback, unit, item, target):
        if self._did_hit and target:
            game.memory['current_unit'] = target
            game.memory['next_class'] = self.value
            game.state.change('promotion')
            game.state.change('transition_out')
        self._did_hit = False

class ClassChange(Promote, ItemComponent):
    nid = 'class_change'
    desc = "Item allows target to change class after hit"
    tag = 'special'

    def end_combat(self, playback, unit, item, target):
        if self._did_hit and target:
            unit_prefab = DB.units.get(target.nid)
            if target.generic or not unit_prefab:
                return
            if not unit_prefab.alternate_classes:
                return
            elif len(unit_prefab.alternate_classes) == 1:
                new_klass = unit_prefab.alternate_classes[0]
            else:
                new_klass = None
            game.memory['current_unit'] = target
            game.memory['combat_item'] = item
            game.memory['can_go_back'] = True
            if new_klass:
                game.memory['next_class'] = new_klass
                game.state.change('class_change')
                game.state.change('transition_out')
            else:
                game.state.change('class_change_choice')
                game.state.change('transition_out')
        self._did_hit = False

class ForceClassChange(Promote, ItemComponent):
    nid = 'force_class_change'
    desc = "Item forcibly changes target's class after hit"
    tag = 'special'

    expose = Type.Class

    def end_combat(self, playback, unit, item, target):
        if self._did_hit and target:
            game.memory['current_unit'] = target
            game.memory['next_class'] = self.value
            game.state.change('class_change')
            game.state.change('transition_out')
        self._did_hit = False

class EventAfterCombat(ItemComponent):
    nid = 'event_after_combat'
    desc = "Item calls an event after hit"
    tag = 'special'

    expose = Type.Event

    _did_hit = False

    def on_hit(self, actions, playback, unit, item, target, target_pos, mode):
        self._did_hit = True

    def end_combat(self, playback, unit, item, target):
        if self._did_hit and target:
            event_prefab = DB.events.get_from_nid(self.value)
            if event_prefab:
                game.events.add_event(event_prefab.nid, event_prefab.commands, unit=unit, unit2=target, item=item, position=unit.position)
        self._did_hit = False
