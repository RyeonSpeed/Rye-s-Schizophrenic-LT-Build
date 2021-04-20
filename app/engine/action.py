import sys

from app.utilities import utils
from app.constants import TILEWIDTH, TILEHEIGHT
from app.data.database import DB

from app.engine import banner, static_random, unit_funcs, equations, \
    skill_system, item_system, item_funcs, particles
from app.engine.objects.unit import UnitObject
from app.engine.objects.item import ItemObject
from app.engine.objects.skill import SkillObject
from app.events.regions import Region
from app.engine.game_state import game

import logging

class Action():
    def __init__(self):
        pass

    # When used normally
    def do(self):
        pass

    # When put in forward motion by the turnwheel
    def execute(self):
        self.do()

    # When put in reverse motion by the turnwheel
    def reverse(self):
        pass

    def __repr__(self):
        s = "action.%s: " % self.__class__.__name__
        for attr in self.__dict__.items():
            name, value = attr
            s += '%s: %s, ' % (name, value)
        s = s[:-2]
        return s

    def save_obj(self, value):
        if isinstance(value, UnitObject):
            value = ('unit', value.nid)
        elif isinstance(value, ItemObject):
            value = ('item', value.uid)
        elif isinstance(value, SkillObject):
            value = ('skill', value.uid)
        elif isinstance(value, Region):
            value = ('region', value.nid)
        elif isinstance(value, list):
            value = ('list', [self.save_obj(v) for v in value])
        elif isinstance(value, Action):
            value = ('action', value.save())
        else:
            value = ('generic', value)
        return value

    def save(self):
        ser_dict = {}
        for attr in self.__dict__.items():
            name, value = attr
            value = self.save_obj(value)
            ser_dict[name] = value
        return (self.__class__.__name__, ser_dict)

    def restore_obj(self, value):
        if value[0] == 'unit':
            return game.get_unit(value[1])
        elif value[0] == 'item':
            return game.get_item(value[1])
        elif value[0] == 'skill':
            return game.get_skill(value[1])
        elif value[0] == 'region':
            return game.get_region(value[1])
        elif value[0] == 'list':
            return [self.restore_obj(v) for v in value[1]]
        elif value[0] == 'action':
            name, value = value[1][0], value[1][1]
            action = getattr(sys.modules[__name__], name)
            return action.restore(value)
        else:
            return value[1]

    @classmethod
    def restore(cls, ser_dict):
        self = cls.__new__(cls)
        for name, value in ser_dict.items():
            setattr(self, name, self.restore_obj(value))
        return self

class Move(Action):
    """
    A basic, user-directed move
    """
    def __init__(self, unit, new_pos, path=None, event=False, follow=True):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos

        self.prev_movement_left = self.unit.movement_left
        self.new_movement_left = None

        self.path = path
        self.has_moved = self.unit.has_moved
        self.event = event
        self.follow = follow

    def do(self):
        if self.path is None:
            self.path = game.cursor.path
        game.movement.begin_move(self.unit, self.path, self.event, self.follow)

    def execute(self):
        game.leave(self.unit)
        if self.new_movement_left is not None:
            self.unit.movement_left = self.new_movement_left
        self.unit.has_moved = True
        self.unit.position = self.new_pos
        game.arrive(self.unit)

    def reverse(self):
        game.leave(self.unit)
        self.new_movement_left = self.unit.movement_left
        self.unit.movement_left = self.prev_movement_left
        self.unit.has_moved = self.has_moved
        self.unit.position = self.old_pos
        game.arrive(self.unit)

# Just another name for move
class CantoMove(Move):
    pass

class SimpleMove(Move):
    """
    A script directed move, no animation
    """
    def __init__(self, unit, new_pos):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos
        self.update_fow_action = UpdateFogOfWar(self.unit)

    def do(self):
        game.leave(self.unit)
        self.unit.position = self.new_pos
        game.arrive(self.unit)
        self.update_fow_action.do()

    def execute(self):
        game.leave(self.unit)
        self.unit.position = self.new_pos
        game.arrive(self.unit)
        self.update_fow_action.execute()

    def reverse(self):
        self.update_fow_action.reverse()
        game.leave(self.unit)
        self.unit.position = self.old_pos
        game.arrive(self.unit)

class Teleport(SimpleMove):
    pass

class ForcedMovement(SimpleMove):
    def do(self):
        # Sprite transition
        x_offset = (self.old_pos[0] - self.new_pos[0]) * TILEWIDTH
        y_offset = (self.old_pos[1] - self.new_pos[1]) * TILEHEIGHT
        self.unit.sprite.offset = [x_offset, y_offset]
        self.unit.sprite.set_transition('fake_in')

        game.leave(self.unit)
        self.unit.position = self.new_pos
        game.arrive(self.unit)
        self.update_fow_action.do()

class Swap(Action):
    def __init__(self, unit1, unit2):
        self.unit1 = unit1
        self.unit2 = unit2
        self.pos1 = unit1.position
        self.pos2 = unit2.position
        self.update_fow_action1 = UpdateFogOfWar(self.unit)
        self.update_fow_action2 = UpdateFogOfWar(self.unit)

    def do(self):
        game.leave(self.unit1)
        game.leave(self.unit2)
        self.unit1.position, self.unit2.position = self.pos2, self.pos1
        game.arrive(self.unit2)
        game.arrive(self.unit1)
        self.update_fow_action1.do()
        self.update_fow_action2.do()

    def reverse(self):
        self.update_fow_action1.reverse()
        self.update_fow_action2.reverse()
        game.leave(self.unit1)
        game.leave(self.unit2)
        self.unit1.position, self.unit2.position = self.pos1, self.pos2
        game.arrive(self.unit2)
        game.arrive(self.unit1)

class Warp(SimpleMove):
    def do(self):
        self.unit.sprite.set_transition('warp_move')

        game.leave(self.unit)
        self.unit.position = self.new_pos
        game.arrive(self.unit)
        self.update_fow_action.do()

class Swoosh(SimpleMove):
    def do(self):
        self.unit.sprite.set_transition('swoosh_move')

        game.leave(self.unit)
        self.unit.position = self.new_pos
        game.arrive(self.unit)
        self.update_fow_action.do()

class FadeMove(SimpleMove):
    def do(self):
        self.unit.sprite.set_transition('fade_move')

        game.leave(self.unit)
        self.unit.position = self.new_pos
        game.arrive(self.unit)
        self.update_fow_action.do()

class ArriveOnMap(Action):
    def __init__(self, unit, pos):
        self.unit = unit
        self.place_on_map = PlaceOnMap(unit, pos)

    def do(self):
        self.place_on_map.do()
        game.arrive(self.unit)

    def reverse(self):
        game.leave(self.unit)
        self.place_on_map.reverse()

class WarpIn(ArriveOnMap):
    def do(self):
        self.place_on_map.do()
        self.unit.sprite.set_transition('warp_in')
        game.arrive(self.unit)

class SwooshIn(ArriveOnMap):
    def do(self):
        self.place_on_map.do()
        self.unit.sprite.set_transition('swoosh_in')
        game.arrive(self.unit)

class FadeIn(ArriveOnMap):
    def do(self):
        self.place_on_map.do()
        if game.tilemap.on_border(self.unit.position):
            if self.unit.position[0] == 0:
                self.unit.sprite.offset = [-TILEWIDTH, 0]
            elif self.unit.position[0] == game.tilemap.width - 1:
                self.unit.sprite.offset = [TILEWIDTH, 0]
            elif self.unit.position[1] == 0:
                self.unit.sprite.offset = [0, -TILEHEIGHT]
            elif self.unit.position[1] == game.tilemap.height - 1:
                self.unit.sprite.offset = [0, TILEHEIGHT]
            self.unit.sprite.set_transition('fake_in')
        else:
            self.unit.sprite.set_transition('fade_in')
        game.arrive(self.unit)

class PlaceOnMap(Action):
    def __init__(self, unit, pos):
        self.unit = unit
        self.pos = pos
        self.update_fow_action = UpdateFogOfWar(self.unit)

    def do(self):
        self.unit.position = self.pos
        if self.unit.position:
            self.unit.previous_position = self.unit.position
        self.update_fow_action.do()

    def reverse(self):
        self.update_fow_action.reverse()
        self.unit.position = None

class LeaveMap(Action):
    def __init__(self, unit):
        self.unit = unit
        self.remove_from_map = RemoveFromMap(self.unit)

    def do(self):
        game.leave(self.unit)
        self.remove_from_map.do()

    def execute(self):
        game.leave(self.unit)
        self.remove_from_map.do()

    def reverse(self):
        self.remove_from_map.reverse()
        game.arrive(self.unit)

class WarpOut(LeaveMap):
    def do(self):
        game.leave(self.unit)
        self.unit.sprite.set_transition('warp_out')
        self.remove_from_map.do()

class SwooshOut(LeaveMap):
    def do(self):
        game.leave(self.unit)
        self.unit.sprite.set_transition('swoosh_out')
        self.remove_from_map.do()

class FadeOut(LeaveMap):
    def do(self):
        game.leave(self.unit)
        if game.tilemap.on_border(self.unit.position):
            if self.unit.position[0] == 0:
                self.unit.sprite.offset = [-2, 0]
            elif self.unit.position[0] == game.tilemap.width - 1:
                self.unit.sprite.offset = [2, 0]
            elif self.unit.position[1] == 0:
                self.unit.sprite.offset = [0, -2]
            elif self.unit.position[1] == game.tilemap.height - 1:
                self.unit.sprite.offset = [0, 2]
            self.unit.sprite.set_transition('fake_out')
        else:
            self.unit.sprite.set_transition('fade_out')
        self.remove_from_map.do()

class RemoveFromMap(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_pos = self.unit.position
        self.update_fow_action = UpdateFogOfWar(self.unit)

    def do(self):
        self.unit.position = None
        self.update_fow_action.do()

    def reverse(self):
        self.update_fow_action.reverse()
        self.unit.position = self.old_pos
        if self.unit.position:
            self.unit.previous_position = self.unit.position

class IncrementTurn(Action):
    def do(self):
        from app.engine.game_state import game
        game.turncount += 1

    def reverse(self):
        game.turncount -= 1

class MarkPhase(Action):
    def __init__(self, phase_name):
        self.phase_name = phase_name

class LockTurnwheel(Action):
    def __init__(self, lock):
        self.lock = lock

class ChangePhaseMusic(Action):
    def __init__(self, phase, music):
        self.phase = phase
        self.old_music = game.level.music[phase]
        self.new_music = music

    def do(self):
        game.level.music[self.phase] = self.new_music

    def reverse(self):
        game.level.music[self.phase] = self.old_music

class Message(Action):
    def __init__(self, message):
        self.message = message

class SetGameVar(Action):
    def __init__(self, nid, val):
        self.nid = nid
        self.val = val
        self.old_val = game.game_vars[self.nid]

    def do(self):
        game.game_vars[self.nid] = self.val

    def reverse(self):
        game.game_vars[self.nid] = self.old_val

class SetLevelVar(Action):
    def __init__(self, nid, val):
        self.nid = nid
        self.val = val
        self.old_val = game.level_vars[self.nid]

    def do(self):
        game.level_vars[self.nid] = self.val

    def reverse(self):
        game.level_vars[self.nid] = self.old_val

class Wait(Action):
    def __init__(self, unit):
        self.unit = unit
        self.action_state = self.unit.get_action_state()
        self.update_fow_action = UpdateFogOfWar(self.unit)

    def do(self):
        self.unit.has_moved = True
        self.unit.has_traded = True
        self.unit.has_attacked = True
        self.unit.finished = True
        self.unit.current_move = None
        self.unit.sprite.change_state('normal')
        self.update_fow_action.do()

    def reverse(self):
        self.unit.set_action_state(self.action_state)
        self.update_fow_action.reverse()

class UpdateFogOfWar(Action):
    def __init__(self, unit):
        self.unit = unit
        self.prev_pos = None

    def do(self):
        # Handle fog of war
        if game.level_vars.get('_fog_of_war'):
            self.prev_pos = game.board.fow_vantage_point.get(self.unit.nid)
            if self.unit.team == 'player':
                fog_of_war_radius = game.level_vars.get('_fog_of_war_radius', 0)
            else:
                fog_of_war_radius = game.level_vars.get('_ai_fog_of_war_radius', game.level_vars.get('_fog_of_war_radius', 0))
            sight_range = skill_system.sight_range(self.unit) + fog_of_war_radius
            game.board.update_fow(self.unit.position, self.unit, sight_range)
            game.boundary.reset_fog_of_war()

    def reverse(self):
        # Handle fog of war
        if game.level_vars.get('_fog_of_war'):
            if self.unit.team == 'player':
                fog_of_war_radius = game.level_vars.get('_fog_of_war_radius', 0)
            else:
                fog_of_war_radius = game.level_vars.get('_ai_fog_of_war_radius', game.level_vars.get('_fog_of_war_radius', 0))
            sight_range = skill_system.sight_range(self.unit) + fog_of_war_radius
            game.board.update_fow(self.prev_pos, self.unit, sight_range)
            game.boundary.reset_fog_of_war()

class ResetUnitVars(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_current_hp = self.unit.get_hp()
        self.old_current_mana = self.unit.get_mana()
        self.old_current_fatigue = self.unit.get_fatigue()
        self.old_movement_left = self.unit.movement_left

    def do(self):
        self.unit.set_hp(min(self.unit.get_hp(), equations.parser.hitpoints(self.unit)))
        self.unit.set_mana(min(self.unit.get_mana(), equations.parser.get_mana(self.unit)))
        self.unit.set_fatigue(min(self.unit.get_fatigue(), equations.parser.get_fatigue(self.unit)))
        self.unit.movement_left = min(self.unit.movement_left, equations.parser.movement(self.unit))

    def reverse(self):
        self.unit.set_hp(self.old_current_hp)
        self.unit.set_mana(self.old_current_mana)
        self.unit.set_fatigue(self.old_current_fatigue)
        self.unit.movement_left = self.old_movement_left

class Reset(Action):
    def __init__(self, unit):
        self.unit = unit
        self.movement_left = self.unit.movement_left
        self.action_state = self.unit.get_action_state()

    def do(self):
        self.unit.reset()
        self.unit.movement_left = equations.parser.movement(self.unit)

    def reverse(self):
        self.unit.set_action_state(self.action_state)
        self.unit.movement_left = self.movement_left

class ResetAll(Action):
    def __init__(self, units):
        self.actions = [Reset(unit) for unit in units]

    def do(self):
        for action in self.actions:
            action.do()

    def reverse(self):
        for action in self.actions:
            action.reverse()

class HasAttacked(Reset):
    def do(self):
        self.unit.has_attacked = True

class HasTraded(Reset):
    def do(self):
        self.unit.has_traded = True

# === RESCUE ACTIONS ========================================================
class Rescue(Action):
    def __init__(self, unit, rescuee):
        self.unit = unit
        self.rescuee = rescuee
        self.old_pos = self.rescuee.position
        self.subactions = []

    def do(self):
        self.subactions.clear()
        self.unit.traveler = self.rescuee.nid
        # TODO Add transition

        game.leave(self.rescuee)
        self.rescuee.position = None
        self.unit.has_rescued = True

        if not skill_system.ignore_rescue_penalty(self.unit) and 'Rescue' in DB.skills.keys():
            self.subactions.append(AddSkill(self.unit, 'Rescue'))

        for action in self.subactions:
            action.do()

    def execute(self):
        self.unit.traveler = self.rescuee.nid

        game.leave(self.rescuee)
        self.rescuee.position = None
        self.unit.has_rescued = True

        for action in self.subactions:
            action.execute()

    def reverse(self):
        self.rescuee.position = self.old_pos
        game.arrive(self.rescuee)
        self.unit.traveler = None
        self.unit.has_rescued = False

        for action in self.subactions:
            action.reverse()

class Drop(Action):
    def __init__(self, unit, droppee, pos):
        self.unit = unit
        self.droppee = droppee
        self.pos = pos
        self.droppee_wait_action = Wait(self.droppee)
        self.subactions = []

    def do(self):
        self.subactions.clear()
        self.droppee.position = self.pos
        game.arrive(self.droppee)
        self.droppee.sprite.change_state('normal')
        self.droppee_wait_action.do()

        self.unit.traveler = None
        self.unit.has_dropped = True

        self.subactions.append(RemoveSkill(self.unit, "Rescue"))
        for action in self.subactions:
            action.do()

        if utils.calculate_distance(self.unit.position, self.pos) == 1:
            self.droppee.sprite.set_transition('fake_in')
            self.droppee.sprite.offset = [(self.unit.position[0] - self.pos[0]) * TILEWIDTH, 
                                          (self.unit.position[1] - self.pos[1]) * TILEHEIGHT]

    def execute(self):
        self.droppee.position = self.pos
        game.arrive(self.droppee)
        self.droppee.sprite.change_state('normal')
        self.droppee_wait_action.execute()

        for action in self.subactions:
            action.execute()

        self.unit.traveler = None
        self.unit.has_dropped = True

    def reverse(self):
        self.unit.traveler = self.droppee.nid

        self.droppee_wait_action.reverse()
        game.leave(self.droppee)
        self.droppee.position = None
        self.unit.has_dropped = False

        for action in self.subactions:
            action.reverse()

class Give(Action):
    def __init__(self, unit, other):
        self.unit = unit
        self.other = other
        self.subactions = []

    def do(self):
        self.subactions.clear()

        self.other.traveler = self.unit.traveler
        if not skill_system.ignore_rescue_penalty(self.other) and 'Rescue' in DB.skills.keys():
            self.subactions.append(AddSkill(self.other, 'Rescue'))

        self.unit.traveler = None
        self.subactions.append(RemoveSkill(self.unit, "Rescue"))

        self.unit.has_given = True

        for action in self.subactions:
            action.do()
        
    def reverse(self):
        self.unit.traveler = self.other.traveler
        self.other.traveler = None
        self.unit.has_given = False

        for action in self.subactions:
            action.reverse()

class Take(Action):
    def __init__(self, unit, other):
        self.unit = unit
        self.other = other
        self.subactions = []

    def do(self):
        self.subactions.clear()

        self.unit.traveler = self.other.traveler
        if not skill_system.ignore_rescue_penalty(self.unit) and 'Rescue' in DB.skills.keys():
            self.subactions.append(AddSkill(self.unit, 'Rescue'))

        self.other.traveler = None
        self.subactions.append(RemoveSkill(self.other, "Rescue"))

        self.unit.has_taken = True

        for action in self.subactions:
            action.do()
        
    def reverse(self):
        self.other.traveler = self.unit.traveler
        self.unit.traveler = None
        self.unit.has_taken = False

        for action in self.subactions:
            action.reverse()

# === ITEM ACTIONS ==========================================================
class PutItemInConvoy(Action):
    def __init__(self, item):
        self.item = item
        self.owner_nid = self.item.owner_nid

    def do(self):
        self.item.owner_nid = None
        game.party.convoy.append(self.item)

    def reverse(self, gameStateObj):
        game.party.convoy.remove(self.item)
        self.item.owner_nid = self.owner_nid

class TakeItemFromConvoy(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item

    def do(self):
        game.party.convoy.remove(self.item)
        self.unit.add_item(self.item)

    def reverse(self):
        self.unit.remove_item(self.item)
        game.party.convoy.append(self.item)

class MoveItem(Action):
    def __init__(self, owner, unit, item):
        self.owner = owner
        self.unit = unit
        self.item = item

    def do(self):
        self.owner.remove_item(self.item)
        self.unit.add_item(self.item)

    def reverse(self):
        self.unit.remove_item(self.item)
        self.owner.add_item(self.item)

class TradeItemWithConvoy(Action):
    def __init__(self, unit, convoy_item, unit_item):
        self.unit = unit
        self.convoy_item = convoy_item
        self.unit_item = unit_item
        self.unit_idx = self.unit.items.index(self.unit_item)

    def do(self):
        self.unit.remove_item(self.unit_item)
        game.party.convoy.remove(self.convoy_item)
        game.party.convoy.append(self.unit_item)
        self.unit.insert_item(self.unit_idx, self.convoy_item)

    def reverse(self):
        self.unit.remove_item(self.convoy_item)
        game.party.convoy.remove(self.unit_item)
        game.party.convoy.append(self.convoy_item)
        self.unit.insert_item(self.unit_idx, self.unit_item)

class GiveItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item

    def do(self):
        if self.unit.team == 'player' or not item_funcs.inventory_full(self.unit, self.item):
            self.unit.add_item(self.item)

    def reverse(self):
        if self.item in self.unit.items:
            self.unit.remove_item(self.item)

class DropItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.is_droppable: bool = item.droppable

    def do(self):
        self.item.droppable = False
        self.unit.add_item(self.item)

    def reverse(self):
        self.item.droppable = self.is_droppable
        self.unit.remove_item(self.item)

class StoreItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.item_index = self.unit.items.index(self.item)

    def do(self):
        self.unit.remove_item(self.item)
        game.party.convoy.append(self.item)

    def reverse(self):
        game.party.convoy.remove(self.item)
        self.unit.insert_item(self.item_index, self.item)

class RemoveItem(StoreItem):
    def do(self):
        self.unit.remove_item(self.item)

    def reverse(self):
        self.unit.insert_item(self.item_index, self.item)

class EquipItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        if item_system.is_accessory(unit, item):
            self.current_equipped = self.unit.equipped_accessory
        else:
            self.current_equipped = self.unit.equipped_weapon

    def do(self):
        self.unit.equip(self.item)

    def reverse(self):
        self.unit.unequip(self.item)
        if self.current_equipped:
            self.unit.equip(self.current_equipped)

class UnequipItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.is_equipped_weapon = self.item is self.unit.equipped_weapon

    def do(self):
        if self.is_equipped_weapon:
            self.unit.unequip(self.item)

    def reverse(self):
        if self.is_equipped_weapon:
            self.unit.equip(self.item)

class BringToTopItem(Action):
    """
    Assumes item is in inventory
    """
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.old_idx = unit.items.index(item)

    def do(self):
        self.unit.bring_to_top_item(self.item)

    def reverse(self):
        self.unit.insert_item(self.old_idx, self.item)

class TradeItem(Action):
    def __init__(self, unit1, unit2, item1, item2):
        self.unit1 = unit1
        self.unit2 = unit2
        self.item1 = item1
        self.item2 = item2
        self.item_index1 = unit1.items.index(item1) if item1 else DB.constants.total_items() - 1
        self.item_index2 = unit2.items.index(item2) if item2 else DB.constants.total_items() - 1

    def swap(self, unit1, unit2, item1, item2, item_index1, item_index2):
        # Do the swap
        if item1:
            unit1.remove_item(item1)
            unit2.insert_item(item_index2, item1)
        if item2:
            unit2.remove_item(item2)
            unit1.insert_item(item_index1, item2)

    def do(self):
        self.swap(self.unit1, self.unit2, self.item1, self.item2, self.item_index1, self.item_index2)

    def reverse(self):
        self.swap(self.unit1, self.unit2, self.item2, self.item1, self.item_index2, self.item_index1)

class RepairItem(Action):
    def __init__(self, item):
        self.item = item
        self.old_uses = self.item.data.get('uses')
        self.old_c_uses = self.item.data.get('c_uses')

    def do(self):
        if self.old_uses is not None and self.item.uses:
            self.item.data['uses'] = self.item.data['starting_uses']
        if self.old_c_uses is not None and self.item.c_uses:
            self.item.data['c_uses'] = self.item.data['starting_c_uses']

    def reverse(self):
        if self.old_uses is not None and self.item.uses:
            self.item.data['uses'] = self.old_uses
        if self.old_c_uses is not None and self.item.c_uses:
            self.item.data['c_uses'] = self.old_c_uses

class SetObjData(Action):
    def __init__(self, obj, keyword, value):
        self.obj = obj
        self.keyword = keyword
        self.value = value
        self.old_value = None

    def do(self):
        if self.keyword in self.obj.data:
            self.old_value = self.obj.data[self.keyword]
            self.obj.data[self.keyword] = self.value

    def reverse(self):
        if self.keyword in self.obj.data:
            self.obj.data[self.keyword] = self.old_value

class GainMoney(Action):
    def __init__(self, party_nid, money):
        self.party_nid = party_nid
        self.money = money
        self.old_money = None

    def do(self):
        party = game.parties.get(self.party_nid)
        self.old_money = party.money
        # Can't go below zero
        if party.money + self.money < 0:
            self.money = -party.money
        party.money += self.money

    def reverse(self):
        party = game.parties.get(self.party_nid)
        party.money = self.old_money

class GainExp(Action):
    def __init__(self, unit, exp_gain):
        self.unit = unit
        self.old_exp = self.unit.exp
        self.exp_gain = exp_gain

    def do(self):
        self.unit.set_exp((self.old_exp + self.exp_gain) % 100)

    def reverse(self):
        self.unit.set_exp(self.old_exp)

class SetExp(GainExp):
    def do(self):
        self.unit.set_exp(self.exp_gain)

class IncLevel(Action):
    """
    Assumes unit did not promote
    """
    def __init__(self, unit):
        self.unit = unit

    def do(self):
        self.unit.level += 1

    def reverse(self):
        self.unit.level -= 1

class SetLevel(Action):
    def __init__(self, unit, level):
        self.unit = unit
        self.old_level = unit.level
        self.new_level = level

    def do(self):
        self.unit.level = self.new_level

    def reverse(self):
        self.unit.level = self.old_level

class AutoLevel(Action):
    def __init__(self, unit, diff):
        self.unit = unit
        self.diff = diff
        self.old_stats = self.unit.stats
        self.old_growth_points = self.unit.growth_points
        self.old_hp = self.unit.get_hp()

    def do(self):
        unit_funcs.auto_level(self.unit, self.diff, self.unit.get_internal_level())

    def reverse(self):
        self.unit.stats = self.old_stats
        self.unit.growth_points = self.old_growth_points
        self.unit.set_hp(self.old_hp)

class ApplyStatChanges(Action):
    def __init__(self, unit, stat_changes):
        self.unit = unit
        self.stat_changes = stat_changes

    def do(self):
        unit_funcs.apply_stat_changes(self.unit, self.stat_changes)

    def reverse(self):
        negative_changes = {k: -v for k, v in self.stat_changes.items()}
        unit_funcs.apply_stat_changes(self.unit, negative_changes)

class ApplyGrowthChanges(Action):
    def __init__(self, unit, stat_changes):
        self.unit = unit
        self.stat_changes = stat_changes

    def do(self):
        unit_funcs.apply_growth_changes(self.unit, self.stat_changes)

    def reverse(self):
        negative_changes = {k: -v for k, v in self.stat_changes.items()}
        unit_funcs.apply_growth_changes(self.unit, negative_changes)

class Promote(Action):
    def __init__(self, unit, new_class_nid, rando_promo = False):
        self.unit = unit
        self.old_exp = self.unit.exp
        self.old_level = self.unit.level
        self.old_klass = self.unit.klass
        self.new_klass = new_class_nid

        promotion_gains = DB.classes.get(self.new_klass).promotion
        current_stats = self.unit.stats
        new_klass_maxes = DB.classes.get(self.new_klass).max_stats
        new_klass_bases = DB.classes.get(self.new_klass).bases

        self.stat_changes = {nid: 0 for nid in DB.stats.keys()}
        for stat_nid in DB.stats.keys():
            stat_value = promotion_gains.get(stat_nid, 0)
            if stat_value == -99:  # Just use the new klass base
                self.stat_changes[stat_nid] = new_klass_bases.get(stat_nid, 0) - current_stats[stat_nid]
            elif stat_value == -98:  # Use the new klass base only if it's bigger
                self.stat_changes[stat_nid] = max(0, new_klass_bases.get(stat_nid, 0) - current_stats[stat_nid])
            else:
                max_gain_possible = new_klass_maxes.get(stat_nid, 0) - current_stats[stat_nid]
                self.stat_changes[stat_nid] = min(stat_value, max_gain_possible)

        wexp_gain = DB.classes.get(self.new_klass).wexp_gain
        self.new_wexp = {nid: 0 for nid in DB.weapons.keys()}
        for weapon in DB.weapons:
            self.new_wexp[weapon.nid] = wexp_gain[weapon.nid].wexp_gain

        if rando_promo:
            self.wexp_base = DB.classes.get(self.old_klass).wexp_gain
            self.wexp_total = 0
            for weapon in DB.weapons:
                if wexp_gain[weapon.nid].wexp_gain <= 0 and self.wexp_base[weapon.nid].wexp_gain > 0: #Our old class has a weapon that our new class doesn't
                    #logger.warning("The weapon type is %s, old class has %s WEXP, new class has %s WEXP", weapon.nid, self.wexp_base[weapon.nid].wexp_gain, wexp_gain[weapon.nid].wexp_gain)
                    self.wexp_total += unit.wexp[weapon.nid]
                    self.new_wexp[weapon.nid] -= unit.wexp[weapon.nid]
                    #logger.warning("%s", self.new_wexp[weapon.nid])
            while self.wexp_total > 0:
                for weapon in DB.weapons:
                    if wexp_gain[weapon.nid].wexp_gain > 0:
                        if self.wexp_total > 0:
                            self.new_wexp[weapon.nid] += 1
                            self.wexp_total -= 1

        self.subactions = []

    def get_data(self):
        return self.stat_changes, self.new_wexp

    def do(self):
        self.subactions.clear()
        for act in self.subactions:
            act.do()

        self.unit.reset_sprite()
        self.unit.klass = self.new_klass
        self.unit.set_exp(0)
        self.unit.level = 1

        unit_funcs.apply_stat_changes(self.unit, self.stat_changes)

    def reverse(self):
        self.unit.reset_sprite()
        self.unit.klass = self.old_klass
        self.unit.set_exp(self.old_exp)
        self.unit.level = self.old_level

        reverse_stat_changes = {k: -v for k, v in self.stat_changes.items()}
        unit_funcs.apply_stat_changes(self.unit, reverse_stat_changes)

        for act in self.subactions:
            act.reverse()
        self.subactions.clear()

class ClassChange(Action):
    def __init__(self, unit, new_class_nid):
        self.unit = unit
        self.old_klass = self.unit.klass
        self.new_klass = new_class_nid

        current_stats = self.unit.stats
        old_klass_bases = DB.classes.get(self.old_klass).bases
        new_klass_bases = DB.classes.get(self.new_klass).bases
        new_klass_maxes = DB.classes.get(self.new_klass).max_stats

        self.stat_changes = {nid: 0 for nid in DB.stats.keys()}
        for stat_nid in self.stat_changes.keys():
            change = new_klass_bases.get(stat_nid, 0) - old_klass_bases.get(stat_nid, 0)
            current_stat = current_stats.get(stat_nid)
            new_value = utils.clamp(change, -current_stat, new_klass_maxes.get(stat_nid, 0) - current_stat)
            self.stat_changes[stat_nid] = new_value

        wexp_gain = DB.classes.get(self.new_klass).wexp_gain
        self.new_wexp = {nid: 0 for nid in DB.weapons.keys()}
        for weapon_nid in self.new_wexp.keys():
            weapon_info = wexp_gain.get(weapon_nid, DB.weapons.default())
            self.new_wexp[weapon_nid] = weapon_info.wexp_gain

        self.subactions = []

    def get_data(self):
        return self.stat_changes, self.new_wexp

    def do(self):
        self.subactions.clear()
        for act in self.subactions:
            act.do()

        self.unit.reset_sprite()
        self.unit.klass = self.new_klass

        unit_funcs.apply_stat_changes(self.unit, self.stat_changes)

    def reverse(self):
        self.unit.reset_sprite()
        self.unit.klass = self.old_klass

        reverse_stat_changes = {k: -v for k, v in self.stat_changes.items()}
        unit_funcs.apply_stat_changes(self.unit, reverse_stat_changes)

        for act in self.subactions:
            act.reverse()
        self.subactions.clear()

class GainWexp(Action):
    def __init__(self, unit, item, wexp_gain):
        self.unit = unit
        self.item = item
        self.wexp_gain = wexp_gain

    def increase_wexp(self):
        weapon_type = item_system.weapon_type(self.unit, self.item)
        if not weapon_type:
            return 0, 0
        self.unit.wexp[weapon_type] += self.wexp_gain
        return self.unit.wexp[weapon_type] - self.wexp_gain, self.unit.wexp[weapon_type]

    def do(self):
        self.old_value, self.current_value = self.increase_wexp()
        for weapon_rank in reversed(DB.weapon_ranks):
            if self.old_value < weapon_rank.requirement and self.current_value >= weapon_rank.requirement:
                weapon_type = item_system.weapon_type(self.unit, self.item)
                game.alerts.append(banner.GainWexp(self.unit, weapon_rank.rank, weapon_type))
                game.state.change('alert')
                break

    def execute(self):
        self.old_value, self.current_value = self.increase_wexp()

    def reverse(self):
        weapon_type = item_system.weapon_type(self.unit, self.item)
        if not weapon_type:
            return
        self.unit.wexp[weapon_type] = self.old_value

class AddWexp(Action):
    def __init__(self, unit, weapon_type, wexp_gain):
        self.unit = unit
        self.weapon_type = weapon_type
        self.wexp_gain = wexp_gain

    def increase_wexp(self):
        self.unit.wexp[self.weapon_type] += self.wexp_gain
        return self.unit.wexp[self.weapon_type] - self.wexp_gain, self.unit.wexp[self.weapon_type]

    def do(self):
        self.old_value, self.current_value = self.increase_wexp()
        for weapon_rank in reversed(DB.weapon_ranks):
            if self.old_value < weapon_rank.requirement and self.current_value >= weapon_rank.requirement:
                game.alerts.append(banner.GainWexp(self.unit, weapon_rank.rank, self.weapon_type))
                game.state.change('alert')
                break

    def execute(self):
        self.old_value, self.current_value = self.increase_wexp()

    def reverse(self):
        self.unit.wexp[self.weapon_type] = self.old_value

class ChangeHP(Action):
    def __init__(self, unit, num):
        self.unit = unit
        self.num = num
        self.old_hp = self.unit.get_hp()

    def do(self):
        self.unit.set_hp(self.old_hp + self.num)

    def reverse(self):
        self.unit.set_hp(self.old_hp)

class SetHP(Action):
    def __init__(self, unit, new_hp):
        self.unit = unit
        self.new_hp = new_hp
        self.old_hp = self.unit.get_hp()

    def do(self):
        self.unit.set_hp(self.new_hp)

    def reverse(self):
        self.unit.set_hp(self.old_hp)

class Die(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_pos = unit.position
        self.leave_map = LeaveMap(self.unit)
        self.drop = None

    def do(self):
        if self.unit.traveler:
            drop_me = game.get_unit(self.unit.traveler)
            self.drop = Drop(self.unit, drop_me, self.unit.position)
            self.drop.do()
            # TODO Drop Sound

        self.leave_map.do()
        self.unit.dead = True
        self.unit.is_dying = False

    def reverse(self):
        self.unit.dead = False
        self.unit.sprite.set_transition('normal')
        self.unit.sprite.change_state('normal')

        self.leave_map.reverse()
        if self.drop:
            self.drop.reverse()

class Resurrect(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_dead = self.unit.dead

    def do(self):
        self.unit.dead = False

    def reverse(self):
        self.unit.dead = self.old_dead

class UpdateRecords(Action):
    def __init__(self, record_type, data):
        self.record_type = record_type
        self.data = data

    def do(self):
        game.records.append(self.record_type, self.data)

    def reverse(self):
        game.records.pop(self.record_type)

class ReverseRecords(Action):
    def __init__(self, record_type, data):
        self.record_type = record_type
        self.data = data

    def do(self):
        game.records.pop(self.record_type)

    def reverse(self):
        game.records.append(self.record_type, self.data)        

class ChangeAI(Action):
    def __init__(self, unit, ai):
        self.unit = unit
        self.ai = ai
        self.old_ai = self.unit.ai

    def do(self):
        self.unit.ai = self.ai
        if game.boundary:
            game.boundary.recalculate_unit(self.unit)

    def reverse(self):
        self.unit.ai = self.old_ai
        if game.boundary:
            game.boundary.recalculate_unit(self.unit)

class ChangeAIGroup(Action):
    def __init__(self, unit, ai_group):
        self.unit = unit
        self.ai_group = ai_group
        self.old_ai = self.unit.ai_group

    def do(self):
        self.unit.ai_group = self.ai_group

    def reverse(self):
        self.unit.ai_group = self.old_ai_group

class AIGroupPing(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_ai_group_state = unit.ai_group_active

    def do(self):
        self.unit.ai_group_active = True

    def reverse(self):
        self.unit.ai_group_active = self.old_ai_group_state

class ChangeTeam(Action):
    def __init__(self, unit, team):
        self.unit = unit
        self.team = team
        self.old_team = self.unit.team
        self.action = Reset(self.unit)
        self.ai_action = ChangeAI(self.unit, 'None')

    def do(self):
        if self.unit.position:
            game.leave(self.unit)
        self.unit.team = self.team
        self.action.do()
        if self.team == 'player':
            # Make sure player unit's don't keep their AI 
            self.ai_action.do()
        if self.unit.position:
            game.arrive(self.unit)
        if game.boundary:
            game.boundary.reset_unit(self.unit)
        self.unit.sprite.load_sprites()

    def reverse(self):
        if self.unit.position:
            game.leave(self.unit)
        self.unit.team = self.old_team
        if self.team == 'player':
            self.ai_action.reverse()
        self.action.reverse()
        if self.unit.position:
            game.arrive(self.unit)
        if game.boundary:
            game.boundary.reset_unit(self.unit)
        self.unit.sprite.load_sprites()

class ChangePortrait(Action):
    def __init__(self, unit, portrait_nid):
        self.unit = unit
        self.old_portrait = self.unit.portrait_nid
        self.new_portrait = portrait_nid

    def do(self):
        self.unit.portrait_nid = self.new_portrait

    def reverse(self):
        self.unit.portrait.nid = self.old_portrait

class AddTag(Action):
    def __init__(self, unit, tag):
        self.unit = unit
        self.tag = tag

    def do(self):
        self.unit._tags.append(self.tag)

    def reverse(self):
        if self.tag in self.unit._tags:
            self.unit._tags.remove(self.tag)

class RemoveTag(Action):
    def __init__(self, unit, tag):
        self.unit = unit
        self.tag = tag
        self.did_remove = False

    def do(self):
        if self.tag in self.unit._tags:
            self.unit._tags.remove(self.tag)
            self.did_remove = True

    def reverse(self):
        if self.did_remove:
            self.unit._tags.append(self.tag)

class AddTalk(Action):
    def __init__(self, unit1_nid, unit2_nid):
        self.unit1 = unit1_nid
        self.unit2 = unit2_nid

    def do(self):
        game.talk_options.append((self.unit1, self.unit2))

    def reverse(self):
        if (self.unit1, self.unit2) in game.talk_options:
            game.talk_options.remove((self.unit1, self.unit2))

class RemoveTalk(Action):
    def __init__(self, unit1_nid, unit2_nid):
        self.unit1 = unit1_nid
        self.unit2 = unit2_nid
        self.did_remove = False

    def do(self):
        if (self.unit1, self.unit2) in game.talk_options:
            game.talk_options.remove((self.unit1, self.unit2))
            self.did_remove = True

    def reverse(self):
        if self.did_remove:
            game.talk_options.append((self.unit1, self.unit2))

class AddLore(Action):
    def __init__(self, lore_nid):
        self.lore_nid = lore_nid

    def do(self):
        game.unlocked_lore.append(self.lore_nid)

    def reverse(self):
        if self.lore_nid in game.unlocked_lore:
            game.unlocked_lore.remove(self.lore_nid)

class RemoveLore(Action):
    def __init__(self, lore_nid):
        self.lore_nid = lore_nid
        self.did_remove = False

    def do(self):
        if self.lore_nid in game.unlocked_lore:
            game.unlocked_lore.remove(self.lore_nid)
            self.did_remove = True

    def reverse(self):
        if self.did_remove:
            game.unlocked_lore.append(self.lore_nid)

class AddRegion(Action):
    def __init__(self, region):
        self.region = region
        self.did_add = False
        self.subactions = []

    def do(self):
        if self.region.nid in game.level.regions:
            pass
        else:
            game.level.regions.append(self.region)
            self.did_add = True
            # Remember to add the status from the unit
            if self.region.region_type == 'status':
                for unit in game.units:
                    if unit.position and self.region.contains(unit.position):
                        new_skill = DB.skills.get(self.region.sub_nid)
                        self.subactions.append(AddSkill(unit, new_skill))
            for act in self.subactions:
                act.do()

    def reverse(self):
        if self.did_add:
            for act in self.subactions:
                act.reverse()
            self.subactions.clear()

            game.level.regions.delete(self.region)

class ChangeRegionCondition(Action):
    def __init__(self, region, condition):
        self.region = region
        self.old_condition = self.region.condition
        self.new_condition = condition

    def do(self):
        self.region.condition = self.new_condition

    def reverse(self):
        self.region.condition = self.old_condition

class RemoveRegion(Action):
    def __init__(self, region):
        self.region = region
        self.did_remove = False
        self.subactions = []

    def do(self):
        if self.region.nid in game.level.regions.keys():
            # Remember to remove the status from the unit
            if self.region.region_type == 'status':
                for unit in game.units:
                    if unit.position and self.region.contains(unit.position):
                        self.subactions.append(RemoveSkill(unit, self.region.sub_nid))

            for act in self.subactions:
                act.do()

            game.level.regions.delete(self.region)
            self.did_remove = True

    def reverse(self):
        if self.did_remove:
            game.level.regions.append(self.region)

            for act in self.subactions:
                act.reverse()
            self.subactions.clear()

class ShowLayer(Action):
    def __init__(self, layer_nid, transition):
        self.layer_nid = layer_nid
        self.transition = transition

    def do(self):
        layer = game.level.tilemap.layers.get(self.layer_nid)
        if self.transition == 'immediate':
            layer.quick_show()
            game.level.tilemap.reset()
        else:
            layer.show()
        game.board.reset_grid(game.level.tilemap)
        game.boundary.reset()

    def execute(self):
        layer = game.level.tilemap.layers.get(self.layer_nid)
        layer.quick_show()
        game.level.tilemap.reset()
        game.board.reset_grid(game.level.tilemap)
        game.boundary.reset()

    def reverse(self):
        layer = game.level.tilemap.layers.get(self.layer_nid)
        layer.quick_hide()
        game.level.tilemap.reset()
        game.board.reset_grid(game.level.tilemap)
        game.boundary.reset()

class HideLayer(Action):
    def __init__(self, layer_nid, transition):
        self.layer_nid = layer_nid
        self.transition = transition

    def do(self):
        layer = game.level.tilemap.layers.get(self.layer_nid)
        if self.transition == 'immediate':
            layer.quick_hide()
            game.level.tilemap.reset()
        else:
            layer.hide()
        game.board.reset_grid(game.level.tilemap)
        game.boundary.reset()

    def execute(self):
        layer = game.level.tilemap.layers.get(self.layer_nid)
        layer.quick_hide()
        game.level.tilemap.reset()
        game.board.reset_grid(game.level.tilemap)
        game.boundary.reset()

    def reverse(self):
        layer = game.level.tilemap.layers.get(self.layer_nid)
        layer.quick_show()
        game.level.tilemap.reset()
        game.board.reset_grid(game.level.tilemap)
        game.boundary.reset()

class AddWeather(Action):
    def __init__(self, weather_nid):
        self.weather_nid = weather_nid

    def do(self):
        new_ps = particles.create_system(self.weather_nid, game.tilemap.width, game.tilemap.height)
        game.tilemap.weather.append(new_ps)

    def reverse(self):
        if any(ps.nid == self.weather_nid for ps in game.tilemap.weather):
            bad_weather = [ps for ps in game.tilemap.weather if ps.nid == self.weather_nid]
            game.tilemap.weather.remove(bad_weather[0])

class RemoveWeather(Action):
    def __init__(self, weather_nid):
        self.weather_nid = weather_nid
        self.did_remove = False

    def do(self):
        if any(ps.nid == self.weather_nid for ps in game.tilemap.weather):
            bad_weather = [ps for ps in game.tilemap.weather if ps.nid == self.weather_nid]
            game.tilemap.weather.remove(bad_weather[0])
            self.did_remove = True

    def reverse(self):
        if self.did_remove:
            new_ps = particles.create_system(self.weather_nid, game.tilemap.width, game.tilemap.height)
            game.tilemap.weather.append(new_ps)

class ChangeObjective(Action):
    def __init__(self, key, string):
        self.key = key
        self.string = string
        self.old_objective = game.level.objective[self.key]

    def do(self):
        game.level.objective[self.key] = self.string

    def reverse(self):
        game.level.objective[self.key] = self.old_objective

class OnlyOnceEvent(Action):
    def __init__(self, event_nid):
        self.event_nid = event_nid

    def do(self):
        game.already_triggered_events.append(self.event_nid)

    def reverse(self):
        game.already_triggered_events.remove(self.event_nid)

class RecordRandomState(Action):
    def __init__(self, old, new):
        self.old = old
        self.new = new

    def do(self):
        pass

    def execute(self):
        static_random.set_combat_random_state(self.new)

    def reverse(self):
        static_random.set_combat_random_state(self.old)

class TriggerCharge(Action):
    def __init__(self, unit, skill):
        self.unit = unit
        self.skill = skill

    def do(self):
        self.old_charge = self.skill.data.get('charge', None)
        skill_system.trigger_charge(self.unit, self.skill)
        self.new_charge = self.skill.data.get('charge', None)

    def reverse(self):
        if self.new_charge is not None:
            self.skill.data['charge'] = self.old_charge

class AddSkill(Action):
    def __init__(self, unit, skill, initiator=None):
        self.unit = unit
        self.initiator = initiator
        # Check if we just passed in the skill nid to create
        if isinstance(skill, str):
            skill_obj = item_funcs.create_skill(unit, skill)
        else:
            skill_obj = skill
        if skill_obj:
            if self.initiator:
                skill_obj.initiator_nid = self.initiator.nid
            skill_system.init(skill_obj)
            if skill_obj.uid not in game.skill_registry:
                game.register_skill(skill_obj)
        self.skill_obj = skill_obj
        self.subactions = []
        self.reset_action = ResetUnitVars(self.unit)

    def do(self):
        if not self.skill_obj:
            return
        # Remove any skills with previous name
        if not self.skill_obj.stack and self.skill_obj.nid in [skill.nid for skill in self.unit.skills]:
            logging.info("Skill %s already present" % self.skill_obj.nid)
            for skill in self.unit.skills:
                if skill.nid == self.skill_obj.nid:
                    self.subactions.append(RemoveSkill(self.unit, skill))
        for action in self.subactions:
            action.execute()
        self.skill_obj.owner_nid = self.unit.nid
        self.unit.skills.append(self.skill_obj)
        skill_system.on_add(self.unit, self.skill_obj)

        # Handle affects movement
        self.reset_action.execute()
        if game.boundary:
            game.boundary.recalculate_unit(self.unit)

    def reverse(self):
        self.reset_action.reverse()
        if self.skill_obj in self.unit.skills:
            self.unit.skills.remove(self.skill_obj)
            skill_system.on_remove(self.unit, self.skill_obj)
            self.skill_obj.owner_nid = None
        else:
            logging.error("Skill %s not in %s's skills", self.skill_obj.nid, self.unit)
        for action in self.subactions:
            action.reverse()

class RemoveSkill(Action):
    def __init__(self, unit, skill):
        self.unit = unit
        self.skill = skill # Skill obj or skill nid str
        self.removed_skills = []
        self.old_owner_nid = None
        self.reset_action = ResetUnitVars(self.unit)

    def do(self):
        if isinstance(self.skill, str):
            for skill in self.unit.skills[:]:
                if skill.nid == self.skill:
                    self.unit.skills.remove(skill)
                    skill_system.on_remove(self.unit, skill)
                    skill.owner_nid = None
                    self.removed_skills.append(skill)
        else:
            if self.skill in self.unit.skills:
                self.unit.skills.remove(self.skill)
                skill_system.on_remove(self.unit, self.skill)
                self.skill.owner_nid = None
                self.removed_skills.append(self.skill)
            else:
                logging.warning("Skill %s not in %s's skills", self.skill.nid, self.unit)

        # Handle affects movement
        self.reset_action.execute()
        if game.boundary:
            game.boundary.recalculate_unit(self.unit)

    def reverse(self):
        self.reset_action.reverse()
        for skill in self.removed_skills:
            skill.owner_nid = self.unit.nid
            self.unit.skills.append(skill)
            skill_system.on_add(self.unit, skill)

# === Master Functions for adding to the action log ===
def do(action):
    from app.engine.game_state import game
    game.action_log.action_depth += 1
    action.do()
    game.action_log.action_depth -= 1
    if game.action_log.record and game.action_log.action_depth <= 0:
        game.action_log.append(action)

def execute(action):
    game.action_log.action_depth += 1
    action.execute()
    game.action_log.action_depth -= 1
    if game.action_log.record and game.action_log.action_depth <= 0:
        game.action_log.append(action)

def reverse(action):
    game.action_log.action_depth += 1
    action.reverse()
    game.action_log.action_depth -= 1
    if game.action_log.record and game.action_log.action_depth <= 0:
        game.action_log.remove(action)
