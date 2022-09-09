from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from app.constants import WINHEIGHT, WINWIDTH
from app.data.database import DB
from app.data.level_units import GenericUnit, UniqueUnit
from app.engine import (action, background, banner, dialog, engine, evaluate,
                        icons, image_mods, item_funcs, item_system,
                        skill_system, target_system, unit_funcs)
from app.engine.animations import MapAnimation
from app.engine.combat import interaction
from app.engine.game_menus.menu_components.generic_menu.simple_menu_wrapper import \
    SimpleMenuUI
from app.engine.graphics.ui_framework.premade_animations.animation_templates import \
    fade_anim, translate_anim
from app.engine.graphics.ui_framework.ui_framework import UIComponent
from app.engine.graphics.ui_framework.ui_framework_animation import \
    InterpolationType
from app.engine.graphics.ui_framework.ui_framework_layout import HAlignment
from app.engine.objects.item import ItemObject
from app.engine.objects.tilemap import TileMapObject
from app.engine.objects.unit import UnitObject
from app.engine.sound import get_sound_thread
from app.events import event_commands, regions, triggers
from app.events.event_portrait import EventPortrait
from app.events.speak_style import SpeakStyle
from app.events.screen_positions import parse_screen_position
from app.resources.resources import RESOURCES
from app.sprites import SPRITES
from app.utilities import str_utils, utils
from app.utilities.enums import Alignments
from app.utilities.typing import NID

if TYPE_CHECKING:
    from app.events.event import Event

def comment(self: Event, flags=None):
    pass

def finish(self: Event, flags=None):
    self.end()

def wait(self: Event, time, flags=None):
    current_time = engine.get_time()
    self.wait_time = current_time + int(time)
    self.state = 'waiting'

def end_skip(self: Event, flags=None):
    if not self.super_skip:
        self.do_skip = False

def music(self: Event, music, fade_in=400, flags=None):
    if self.do_skip:
        fade_in = 0
    if music == 'None':
        get_sound_thread().fade_to_pause(fade_out=fade_in)
    else:
        get_sound_thread().fade_in(music, fade_in=fade_in)

def music_clear(self: Event, fade_out=0, flags=None):
    if self.do_skip:
        fade_out = 0
    if fade_out > 0:
        get_sound_thread().fade_clear(fade_out)
    else:
        get_sound_thread().clear()

def sound(self: Event, sound, volume=1.0, flags=None):
    get_sound_thread().play_sfx(sound, volume=float(volume))

def change_music(self: Event, phase, music, flags=None):
    if music == 'None':
        action.do(action.ChangePhaseMusic(phase, None))
    else:
        action.do(action.ChangePhaseMusic(phase, music))

def add_portrait(self: Event, portrait, screen_position, slide=None, expression_list=None, flags=None):
    flags = flags or set()

    name = portrait
    unit = self._get_unit(name)
    if unit:
        name = unit.nid
    if unit and unit.portrait_nid:
        portrait = RESOURCES.portraits.get(unit.portrait_nid)
    elif name in DB.units.keys():
        portrait = RESOURCES.portraits.get(DB.units.get(name).portrait_nid)
    else:
        portrait = RESOURCES.portraits.get(name)
    if not portrait:
        self.logger.error("add_portrait: Couldn't find portrait %s" % name)
        return False
    # If already present, don't add
    if name in self.portraits and not self.portraits[name].remove:
        return False

    position, mirror = parse_screen_position(screen_position)

    priority = self.priority_counter
    if 'low_priority' in flags:
        priority -= 1000
    self.priority_counter += 1

    if 'mirror' in flags:
        mirror = not mirror

    transition = True
    if 'immediate' in flags or self.do_skip:
        transition = False

    new_portrait = EventPortrait(portrait, position, priority, transition, slide, mirror)
    self.portraits[name] = new_portrait

    if expression_list:
        expression_list = expression_list.split(',')
        new_portrait.set_expression(expression_list)

    if 'immediate' in flags or 'no_block' in flags or self.do_skip:
        pass
    else:
        self.wait_time = engine.get_time() + new_portrait.transition_speed + 33  # 16 frames
        self.state = 'waiting'

    return True

def multi_add_portrait(self: Event, portrait1, screen_position1, portrait2, screen_position2,
                       portrait3=None, screen_position3=None, portrait4=None, screen_position4=None, flags=None):
    commands = []
    # Portrait1
    commands.append(event_commands.AddPortrait({'Portrait': portrait1, 'ScreenPosition': screen_position1}, {'no_block'}))
    # Portrait2
    flags = {'no_block'} if portrait3 else set()
    commands.append(event_commands.AddPortrait({'Portrait': portrait2, 'ScreenPosition': screen_position2}, flags))
    if portrait3:
        flags = {'no_block'} if portrait4 else set()
        commands.append(event_commands.AddPortrait({'Portrait': portrait3, 'ScreenPosition': screen_position3}, flags))
    if portrait4:
        commands.append(event_commands.AddPortrait({'Portrait': portrait4, 'ScreenPosition': screen_position4}, set()))
    for command in reversed(commands):
        # Done backwards to preserve order upon insertion
        self.commands.insert(self.command_idx + 1, command)

def remove_portrait(self: Event, portrait, flags=None):
    flags = flags or set()

    name = portrait
    unit = self._get_unit(name)
    if unit:
        name = unit.nid
    if name not in self.portraits:
        return False

    if 'immediate' in flags or self.do_skip:
        portrait = self.portraits.pop(name)
    else:
        portrait = self.portraits[name]
        portrait.end()

    if 'immediate' in flags or 'no_block' in flags or self.do_skip:
        pass
    else:
        self.wait_time = engine.get_time() + portrait.transition_speed + 33
        self.state = 'waiting'

def multi_remove_portrait(self: Event, portrait1, portrait2, portrait3=None, portrait4=None, flags=None):
    commands = []
    commands.append(event_commands.RemovePortrait({'Portrait': portrait1}, {'no_block'}))
    flags = {'no_block'} if portrait3 else set()
    commands.append(event_commands.RemovePortrait({'Portrait': portrait2}, flags))
    if portrait3:
        flags = {'no_block'} if portrait4 else set()
        commands.append(event_commands.RemovePortrait({'Portrait': portrait3}, flags))
    if portrait4:
        commands.append(event_commands.RemovePortrait({'Portrait': portrait4}, set()))

    for command in reversed(commands):
        # Done backwards to preserve order upon insertion
        self.commands.insert(self.command_idx + 1, command)

def move_portrait(self: Event, portrait, screen_position, flags=None):
    flags = flags or set()

    name = portrait
    unit = self._get_unit(name)
    if unit:
        name = unit.nid
    portrait = self.portraits.get(name)
    if not portrait:
        return False

    position, _ = parse_screen_position(screen_position)

    if 'immediate' in flags or self.do_skip:
        portrait.quick_move(position)
    else:
        portrait.move(position)

    if 'immediate' in flags or 'no_block' in flags or self.do_skip:
        pass
    else:
        self.wait_time = engine.get_time() + portrait.travel_time + 66
        self.state = 'waiting'

def mirror_portrait(self: Event, portrait, flags=None):
    flags = flags or set()

    name = portrait
    unit = self._get_unit(name)
    if unit:
        name = unit.nid
    portrait = self.portraits.get(name)
    if not portrait:
        return False

    self.portraits[name] = \
        EventPortrait(
            self.portraits[name].portrait,
            self.portraits[name].position,
            self.portraits[name].priority,
            False, None, not self.portraits[name].mirror)

    if 'no_block' in flags or self.do_skip:
        pass
    else:
        self.wait_time = engine.get_time() + portrait.transition_speed + 33
        self.state = 'waiting'

def bop_portrait(self: Event, portrait, flags=None):
    flags = flags or set()

    name = portrait
    unit = self._get_unit(name)
    if unit:
        name = unit.nid
    _portrait = self.portraits.get(name)
    if not _portrait:
        return False
    _portrait.bop()
    if 'no_block' in flags:
        pass
    else:
        self.wait_time = engine.get_time() + 666
        self.state = 'waiting'

def expression(self: Event, portrait, expression_list, flags=None):
    name = portrait
    unit = self._get_unit(name)
    if unit:
        name = unit.nid
    _portrait = self.portraits.get(name)
    if not _portrait:
        return False
    expression_list = expression_list.split(',')
    _portrait.set_expression(expression_list)

def speak_style(self: Event, style, speaker=None, text_position=None, width=None, text_speed=None,
                font_color=None, font_type=None, dialog_box=None, num_lines=None, draw_cursor=None, message_tail=None, flags=None):
    flags = flags or set()
    style_nid = style
    if style_nid in self.game.speak_styles:
        style = self.game.speak_styles[style_nid]
    else:
        style = SpeakStyle(nid=style_nid)
    # parse everything
    if speaker:
        style.speaker = speaker
    if text_position:
        if text_position == 'center':
            style.text_position = text_position
        else:
            style.text_position = self._parse_pos(text_position)
    if width:
        style.width = int(width)
    if text_speed:
        style.text_speed = float(text_speed)
    if font_color:
        style.font_color = font_color
    if font_type:
        style.font_type = font_type
    if dialog_box:
        style.dialog_box = dialog_box
    if num_lines:
        style.num_lines = int(num_lines)
    if draw_cursor:
        style.draw_cursor = bool(draw_cursor)
    if message_tail:
        style.message_tail = message_tail
    if flags:
        style.flags = flags
    self.game.speak_styles[style.nid] = style

def speak(self: Event, speaker, text, text_position=None, width=None, style_nid=None, text_speed=None,
          font_color=None, font_type=None, dialog_box=None, num_lines=None, draw_cursor=None,
          message_tail=None, flags=None):
    flags = flags or set()
    # special char: this is a unicode single-line break.
    # basically equivalent to {br}
    # the first char shouldn't be one of these
    if text[0] == '\u2028':
        text = text[1:]
    text = text.replace('\u2028', '{sub_break}')  # sub break to distinguish it

    if 'no_block' in flags:
        text += '{no_wait}'

    speak_style = None
    if style_nid and style_nid in self.game.speak_styles:
        speak_style = self.game.speak_styles[style_nid]

    if not speaker and speak_style:
        speaker = speak_style.speaker
    unit = self._get_unit(speaker)
    if unit:
        speaker = unit.nid
    portrait = self.portraits.get(speaker)

    if text_position:
        if text_position == 'center':
            position = 'center'
        else:
            position = self._parse_pos(text_position)
    elif speak_style and speak_style.text_position:
        position = speak_style.text_position
    else:
        position = None

    if width:
        box_width = int(width)
    elif speak_style and speak_style.width:
        box_width = speak_style.width
    else:
        box_width = None

    if text_speed:
        speed = float(text_speed)
    elif speak_style and speak_style.text_speed:
        speed = speak_style.text_speed
    else:
        speed = 1

    if font_color:
        fcolor = font_color
    elif speak_style and speak_style.font_color:
        fcolor = speak_style.font_color
    else:
        fcolor = None

    if font_type:
        ftype = font_type
    elif speak_style and speak_style.font_type:
        ftype = speak_style.font_type
    else:
        ftype = 'convo'

    if dialog_box:
        bg = dialog_box
    elif speak_style and speak_style.dialog_box:
        bg = speak_style.dialog_box
    else:
        bg = 'message_bg_base'

    if num_lines:
        lines = int(num_lines)
    elif speak_style and speak_style.num_lines:
        lines = speak_style.num_lines
    else:
        lines = 2

    if draw_cursor:
        cursor = bool(draw_cursor)
    elif speak_style and speak_style.draw_cursor:
        cursor = speak_style.draw_cursor
    else:
        cursor = True

    if message_tail:
        tail = message_tail
    elif speak_style and speak_style.message_tail:
        tail = speak_style.message_tail
    else:
        tail = "message_bg_tail"

    if speak_style and speak_style.flags:
        flags = speak_style.flags.union(flags)

    autosize = 'fit' in flags
    new_dialog = \
        dialog.Dialog(text, portrait, bg, position, box_width, speaker=speaker,
                      style_nid=style_nid, autosize=autosize, speed=speed,
                      font_color=fcolor, font_type=ftype, num_lines=lines,
                      draw_cursor=cursor, message_tail=tail)
    new_dialog.hold = 'hold' in flags
    if 'no_popup' in flags:
        new_dialog.last_update = engine.get_time() - 10000
    self.text_boxes.append(new_dialog)
    if 'no_block' not in flags:
        self.state = 'dialog'
    # Bring portrait to forefront
    if portrait and 'low_priority' not in flags:
        portrait.priority = self.priority_counter
        self.priority_counter += 1

def unhold(self: Event, nid, flags=None):
    for box in self.text_boxes:
        if box.style_nid == nid:
            box.hold = False

def transition(self: Event, direction=None, speed=None, color3=None, flags=None):
    current_time = engine.get_time()
    if direction:
        self.transition_state = direction.lower()
    elif self.transition_state == 'close':
        self.transition_state = 'open'
    else:
        self.transition_state = 'close'
    self.transition_speed = max(1, int(speed)) if speed else self._transition_speed
    self.transition_color = tuple(int(_) for _ in color3.split(',')) if color3 else self._transition_color

    if not self.do_skip:
        self.transition_update = current_time
        self.wait_time = current_time + int(self.transition_speed * 1.33)
        self.state = 'waiting'

def change_background(self: Event, panorama=None, flags=None):
    flags = flags or set()
    if panorama:
        panorama = RESOURCES.panoramas.get(panorama)
        if not panorama:
            return
        self.background = background.PanoramaBackground(panorama)
    else:
        self.background = None
    if 'keep_portraits' in flags:
        pass
    else:
        self.portraits.clear()

def disp_cursor(self: Event, show_cursor, flags=None):
    if show_cursor.lower() in self.true_vals:
        self.game.cursor.show()
    else:
        self.game.cursor.hide()

def move_cursor(self: Event, position, speed=None, flags=None):
    flags = flags or set()

    _position = self._parse_pos(position)
    if not _position:
        self.logger.error("move_cursor: Could not determine position from %s" % position)
        return
    position = _position

    self.game.cursor.set_pos(position)
    if 'immediate' in flags or self.do_skip:
        self.game.camera.force_xy(*position)
    else:
        if speed:
            # we are using a custom camera speed
            duration = int(speed)
            self.game.camera.do_slow_pan(duration)
        self.game.camera.set_xy(*position)
        self.game.state.change('move_camera')
        self.state = 'paused'  # So that the message will leave the update loop

def center_cursor(self: Event, position, speed=None, flags=None):
    flags = flags or set()

    _position = self._parse_pos(position)
    if not _position:
        self.logger.error("center_cursor: Could not determine position from %s" % position)
        return
    position = _position

    self.game.cursor.set_pos(position)
    if 'immediate' in flags or self.do_skip:
        self.game.camera.force_center(*position)
    else:
        if speed:
            # we are using a custom camera speed
            duration = int(speed)
            self.game.camera.do_slow_pan(duration)
            self.game.camera.set_center(*position)
        self.game.state.change('move_camera')
        self.state = 'paused'  # So that the message will leave the update loop

def flicker_cursor(self: Event, position, flags=None):
    # This is a macro that just adds new commands to command list
    move_cursor_command = event_commands.MoveCursor({'Position': position}, flags)
    disp_cursor_command1 = event_commands.DispCursor({'ShowCursor': '1'})
    wait_command = event_commands.Wait({'Time': '1000'})
    disp_cursor_command2 = event_commands.DispCursor({'ShowCursor': '0'})
    # Done backwards to presever order upon insertion
    self.commands.insert(self.command_idx + 1, disp_cursor_command2)
    self.commands.insert(self.command_idx + 1, wait_command)
    self.commands.insert(self.command_idx + 1, disp_cursor_command1)
    self.commands.insert(self.command_idx + 1, move_cursor_command)

def game_var(self: Event, nid, expression, flags=None):
    try:
        val = self.text_evaluator.direct_eval(expression)
        action.do(action.SetGameVar(nid, val))
    except Exception as e:
        self.logger.error("game_var: Could not evaluate %s (%s)" % (expression, e))

def inc_game_var(self: Event, nid, expression=None, flags=None):
    if expression:
        try:
            val = self.text_evaluator.direct_eval(expression)
            action.do(action.SetGameVar(nid, self.game.game_vars.get(nid, 0) + val))
        except Exception as e:
            self.logger.error("inc_game_var: Could not evaluate %s (%s)" % (expression, e))
    else:
        action.do(action.SetGameVar(nid, self.game.game_vars.get(nid, 0) + 1))

def level_var(self: Event, nid, expression, flags=None):
    try:
        val = self.text_evaluator.direct_eval(expression)
        action.do(action.SetLevelVar(nid, val))
    except Exception as e:
        self.logger.error("level_var: Could not evaluate %s (%s)" % (expression, e))
        return

def inc_level_var(self: Event, nid, expression=None, flags=None):
    if expression:
        try:
            val = self.text_evaluator.direct_eval(expression)
            action.do(action.SetLevelVar(nid, self.game.level_vars.get(nid, 0) + val))
        except Exception as e:
            self.logger.error("inc_level_var: Could not evaluate %s (%s)" % (expression, e))
    else:
        action.do(action.SetLevelVar(nid, self.game.level_vars.get(nid, 0) + 1))

def set_next_chapter(self: Event, chapter, flags=None):
    if chapter not in DB.levels.keys():
        self.logger.error("set_next_chapter: %s is not a valid chapter nid" % chapter)
        return
    action.do(action.SetGameVar("_goto_level", chapter))

def enable_supports(self: Event, activated: str, flags=None):
    state = activated.lower() in self.true_vals
    action.do(action.SetGameVar("_supports", activated))

def set_fog_of_war(self: Event, fog_of_war_type, radius, ai_radius=None, other_radius=None, flags=None):
    fowt = fog_of_war_type.lower()
    if fowt == 'gba':
        fowt = 1
    elif fowt == 'thracia':
        fowt = 2
    else:
        fowt = 0
    action.do(action.SetLevelVar('_fog_of_war', fowt))
    radius = int(radius)
    action.do(action.SetLevelVar('_fog_of_war_radius', radius))
    if ai_radius is not None:
        ai_radius = int(ai_radius)
        action.do(action.SetLevelVar('_ai_fog_of_war_radius', ai_radius))
    if other_radius is not None:
        other_radius = int(ai_radius)
        action.do(action.SetLevelVar('_ai_fog_of_war_radius', other_radius))

def win_game(self: Event, flags=None):
    self.game.level_vars['_win_game'] = True

def lose_game(self: Event, flags=None):
    self.game.level_vars['_lose_game'] = True

def main_menu(self: Event, flags=None):
    self.game.level_vars['_main_menu'] = True

def skip_save(self: Event, true_or_false: str, flags=None):
    state = true_or_false.lower() in self.true_vals
    action.do(action.SetLevelVar('_skip_save', state))

def activate_turnwheel(self: Event, force=None, flags=None):
    if force and force.lower() not in self.true_vals:
        self.turnwheel_flag = 1
    else:
        self.turnwheel_flag = 2

def battle_save(self: Event, flags=None):
    self.battle_save_flag = True

def clear_turnwheel(self: Event, flags=None):
    self.game.action_log.set_first_free_action()

def change_tilemap(self: Event, tilemap, position_offset=None, load_tilemap=None, flags=None):
    """
    Cannot be turnwheeled
    """
    flags = flags or set()

    tilemap_nid = tilemap
    tilemap_prefab = RESOURCES.tilemaps.get(tilemap_nid)
    if not tilemap_prefab:
        self.logger.error("change_tilemap: Couldn't find tilemap %s" % tilemap_nid)
        return

    if position_offset:
        position_offset = tuple(str_utils.intify(position_offset))
    else:
        position_offset = (0, 0)
    if load_tilemap:
        reload_map_nid = load_tilemap
    else:
        reload_map_nid = tilemap_nid

    reload_map = 'reload' in flags
    if reload_map and self.game.is_displaying_overworld(): # just go back to the level
        from app.engine import level_cursor, map_view, movement
        self.game.cursor = level_cursor.LevelCursor(self.game)
        self.game.movement = movement.MovementManager()
        self.game.map_view = map_view.MapView()
        self.game.boundary = self.prev_game_boundary
        self.game.board = self.prev_board
        if reload_map and self.game.level_vars.get('_prev_pos_%s' % reload_map_nid):
            for unit_nid, pos in self.game.level_vars['_prev_pos_%s' % reload_map_nid].items():
                # Reload unit's position with position offset
                final_pos = pos[0] + position_offset[0], pos[1] + position_offset[1]
                if self.game.tilemap.check_bounds(final_pos):
                    unit = self.game.get_unit(unit_nid)
                    act = action.ArriveOnMap(unit, final_pos)
                    act.execute()
        return

    # Reset cursor position
    self.game.cursor.set_pos((0, 0))

    # Remove all units from the map
    # But remember their original positions for later
    previous_unit_pos = {}
    for unit in self.game.units:
        if unit.position:
            previous_unit_pos[unit.nid] = unit.position
            act = action.LeaveMap(unit)
            act.execute()
    current_tilemap_nid = self.game.level.tilemap.nid
    self.game.level_vars['_prev_pos_%s' % current_tilemap_nid] = previous_unit_pos

    tilemap = TileMapObject.from_prefab(tilemap_prefab)
    self.game.level.tilemap = tilemap
    if self.game.is_displaying_overworld():
        # we were in the overworld before this, so we should probably reset cursor and such
        from app.engine import level_cursor, map_view, movement
        self.game.cursor = level_cursor.LevelCursor(self.game)
        self.game.movement = movement.MovementManager()
        self.game.map_view = map_view.MapView()
    self.game.set_up_game_board(self.game.level.tilemap)

    # If we're reloading the map
    if reload_map and self.game.level_vars.get('_prev_pos_%s' % reload_map_nid):
        for unit_nid, pos in self.game.level_vars['_prev_pos_%s' % reload_map_nid].items():
            # Reload unit's position with position offset
            final_pos = pos[0] + position_offset[0], pos[1] + position_offset[1]
            if self.game.tilemap.check_bounds(final_pos):
                unit = self.game.get_unit(unit_nid)
                act = action.ArriveOnMap(unit, final_pos)
                act.execute()

    # Can't use turnwheel to go any further back
    self.game.action_log.set_first_free_action()

def change_bg_tilemap(self: Event, tilemap=None, flags=None):
    flags = flags or set()

    tilemap_nid = tilemap
    tilemap_prefab = RESOURCES.tilemaps.get(tilemap_nid)
    if not tilemap_prefab:
        self.game.level.bg_tilemap = None
        return

    tilemap = TileMapObject.from_prefab(tilemap_prefab)
    action.do(action.ChangeBGTileMap(tilemap))

def set_game_board_bounds(self: Event, min_x, min_y, max_x, max_y, flags=None):
    min_x = int(min_x)
    max_x = int(max_x)
    min_y = int(min_y)
    max_y = int(max_y)
    if not self.game.board:
        self.logger.warning("set_game_board_bounds: No game board available")
    elif max_x <= min_x:
        self.logger.warning("set_game_board_bounds: MaxX must be strictly greater than MinX, (MinX: %d, MaxX: %d)", min_x, max_x)
    elif max_y <= min_y:
        self.logger.warning("set_game_board_bounds: MaxY must be strictly greater than MinY, (MinY: %d, MaxY: %d)", min_y, max_y)
    else:
        bounds = (min_x, min_y, max_x, max_y)
        action.do(action.SetGameBoardBounds(bounds))

def remove_game_board_bounds(self: Event, flags=None):
    if self.game.board:
        bounds = (0, 0, self.game.tilemap.width - 1, self.game.tilemap.height - 1)
        action.do(action.SetGameBoardBounds(bounds))
    else:
        self.logger.warning("remove_game_board_bounds: No game board available")

def load_unit(self: Event, unique_unit, team=None, ai=None, flags=None):
    unit_nid = unique_unit
    if self.game.get_unit(unit_nid):
        self.logger.error("load_unit: Unit with NID %s already exists!" % unit_nid)
        return
    unit_prefab = DB.units.get(unit_nid)
    if not unit_prefab:
        self.logger.error("load_unit: Could not find unit %s in database" % unit_nid)
        return
    if not team:
        team = 'player'
    if not ai:
        ai = 'None'
    level_unit_prefab = UniqueUnit(unit_nid, team, ai, None)
    new_unit = UnitObject.from_prefab(level_unit_prefab, self.game.current_mode)
    new_unit.party = self.game.current_party
    self.game.full_register(new_unit)

def make_generic(self: Event, nid, klass, level, team, ai=None, faction=None, animation_variant=None, item_list=None, flags=None):
    assign_unit = False
    # Get input
    unit_nid = nid
    if not unit_nid:
        unit_nid = str_utils.get_next_int('201', [unit.nid for unit in self.game.units])
        assign_unit = True
    elif self.game.get_unit(unit_nid):
        self.logger.error("make_generic: Unit with NID %s already exists!" % unit_nid)
        return

    if klass not in DB.classes.keys():
        self.logger.error("make_generic: Class %s doesn't exist in database " % klass)
        return
    level = int(level)
    if not ai:
        ai = 'None'
    if not faction:
        faction = DB.factions[0].nid
    if item_list:
        starting_items = item_list.split(',')
    else:
        starting_items = []
    level_unit_prefab = GenericUnit(unit_nid, animation_variant, level, klass, faction, starting_items, team, ai)
    new_unit = UnitObject.from_prefab(level_unit_prefab)
    new_unit.party = self.game.current_party
    #self.game.full_register(new_unit)
    action.do(action.RegisterUnit(new_unit))

    if assign_unit:
        self.created_unit = new_unit
        self.text_evaluator.created_unit = new_unit

def create_unit(self: Event, unit, nid=None, level=None, position=None, entry_type=None, placement=None, flags=None):
    flags = flags or set()

    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("create_unit: Couldn't find unit %s" % unit)
        return
    unit = new_unit
    # Get input
    assign_unit = False
    unit_nid = nid
    if not unit_nid:
        unit_nid = str_utils.get_next_int('201', [unit.nid for unit in self.game.units])
        assign_unit = True
    elif self.game.get_unit(unit_nid):
        self.logger.error("create_unit: Unit with NID %s already exists!" % unit_nid)
        return

    if not level:
        level = unit.level
    if position:
        position = self._parse_pos(position)
    else:
        position = unit.starting_position
    if not position:
        self.logger.error("create_unit: No position found!")
        return
    if not entry_type:
        entry_type = 'fade'
    if not placement:
        placement = 'giveup'

    faction = unit.faction
    if not faction:
        faction = DB.factions[0].nid
    level_unit_prefab = GenericUnit(
        unit_nid, unit.variant, int(level), unit.klass, faction, [item.nid for item in unit.items], unit.team, unit.ai)
    new_unit = UnitObject.from_prefab(level_unit_prefab, self.game.current_mode)

    if 'copy_stats' in flags:
        new_unit.stats = unit.stats.copy()

    position = self._check_placement(new_unit, position, placement)
    if not position:
        self.logger.error("create_unit: Couldn't get a good position %s %s %s" % (position, entry_type, placement))
        return None
    new_unit.party = self.game.current_party
    # self.game.full_register(new_unit)
    action.do(action.RegisterUnit(new_unit))
    if assign_unit:
        self.created_unit = new_unit
        self.text_evaluator.created_unit = new_unit
    if DB.constants.value('initiative'):
        action.do(action.InsertInitiative(new_unit))

    self._place_unit(new_unit, position, entry_type)

def add_unit(self: Event, unit, position=None, entry_type=None, placement=None, animation_type=None, flags=None):
    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("add_unit: Couldn't find unit %s" % unit)
        return
    unit = new_unit
    if unit.position:
        self.logger.error("add_unit: Unit already on map!")
        return
    if unit.dead:
        self.logger.error("add_unit: Unit is dead!")
        return
    if position:
        position = self._parse_pos(position)
    else:
        position = unit.starting_position
    if not position:
        self.logger.error("add_unit: No position found!")
        return
    if not entry_type:
        entry_type = 'fade'
    if not placement:
        placement = 'giveup'

    if not animation_type or animation_type == 'fade':
        fade_direction = None
    else:
        fade_direction = animation_type

    position = self._check_placement(unit, position, placement)
    if not position:
        self.logger.error("add_unit: Couldn't get a good position %s %s %s" % (position, entry_type, placement))
        return None
    if DB.constants.value('initiative'):
        action.do(action.InsertInitiative(unit))
    self._place_unit(unit, position, entry_type, fade_direction)

def move_unit(self: Event, unit, position=None, movement_type=None, placement=None, flags=None):
    flags = flags or set()

    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("move_unit: Couldn't find unit %s" % unit)
        return
    unit = new_unit
    if not unit.position:
        self.logger.error("move_unit: Unit not on map!")
        return

    if position:
        position = self._parse_pos(position)
    else:
        position = unit.starting_position
    if not position:
        self.logger.error("move_unit: No position found!")
        return

    if not movement_type:
        movement_type = 'normal'
    if not placement:
        placement = 'giveup'
    follow = 'no_follow' not in flags

    position = self._check_placement(unit, position, placement)
    if not position:
        self.logger.error("move_unit: Couldn't get a good position %s %s %s" % (position, movement_type, placement))
        return None

    if movement_type == 'immediate' or self.do_skip:
        action.do(action.Teleport(unit, position))
    elif movement_type == 'warp':
        action.do(action.Warp(unit, position))
    elif movement_type == 'swoosh':
        action.do(action.Swoosh(unit, position))
    elif movement_type == 'fade':
        action.do(action.FadeMove(unit, position))
    elif movement_type == 'normal':
        path = target_system.get_path(unit, position)
        action.do(action.Move(unit, position, path, event=True, follow=follow))

    if 'no_block' in flags or self.do_skip:
        pass
    else:
        self.state = 'paused'
        self.game.state.change('movement')

def remove_unit(self: Event, unit, remove_type=None, animation_type=None, flags=None):
    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("remove_unit: Couldn't find unit %s" % unit)
        return
    unit = new_unit
    if not unit.position:
        self.logger.error("remove_unit: Unit not on map!")
        return
    if not remove_type:
        remove_type = 'fade'
    if not animation_type or animation_type == 'fade':
        fade_direction = None
    else:
        fade_direction = animation_type
    if DB.constants.value('initiative'):
        action.do(action.RemoveInitiative(unit))
    if self.do_skip:
        action.do(action.LeaveMap(unit))
    elif remove_type == 'warp':
        action.do(action.WarpOut(unit))
    elif remove_type == 'swoosh':
        action.do(action.SwooshOut(unit))
    elif remove_type == 'fade':
        action.do(action.FadeOut(unit, fade_direction))
    else:  # immediate
        action.do(action.LeaveMap(unit))

def kill_unit(self: Event, unit, flags=None):
    flags = flags or set()

    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("kill_unit: Couldn't find unit %s" % unit)
        return
    unit = new_unit

    if DB.constants.value('initiative'):
        action.do(action.RemoveInitiative(unit))

    if not unit.position:
        unit.dead = True
    elif 'immediate' in flags:
        unit.dead = True
        action.do(action.LeaveMap(unit))
    else:
        self.game.death.should_die(unit)
        self.game.state.change('dying')
    self.game.events.trigger(triggers.UnitDeath(unit, None, unit.position))
    skill_system.on_death(unit)
    self.state = 'paused'

def remove_all_units(self: Event, flags=None):
    for unit in self.game.units:
        if unit.position:
            action.do(action.LeaveMap(unit))

def remove_all_enemies(self: Event, flags=None):
    for unit in self.game.units:
        if unit.position and unit.team.startswith('enemy'):
            action.do(action.FadeOut(unit))

def interact_unit(self: Event, unit, position, combat_script=None, ability=None, rounds=None, flags=None):
    flags = flags or set()

    actor = self._get_unit(unit)
    if not actor or not actor.position:
        self.logger.error("interact_unit: Couldn't find %s" % unit)
        return
    target = self._parse_pos(position)
    if not target:
        self.logger.error("interact_unit: Couldn't find target %s" % position)
        return

    if combat_script:
        script = combat_script.split(',')
    else:
        script = None

    if rounds:
        total_rounds = utils.clamp(int(rounds), 1, 99)
    else:
        total_rounds = 1

    items = item_funcs.get_all_items(actor)
    item = None
    # Get item
    if ability:
        item_nid = ability
        for i in items:
            if item_nid == i.nid:
                item = i
                break
        else:  # Create item on the fly
            item_prefab = DB.items.get(ability)
            if not item_prefab:
                self.logger.error("interact_unit: Couldn't find item with nid %s" % ability)
                return
            # Create item
            item = ItemObject.from_prefab(item_prefab)
            item_system.init(item)
            self.game.register_item(item)
    else:
        if actor.get_weapon():
            item = actor.get_weapon()
        elif items:
            item = items[0]
        else:
            self.logger.error("interact_unit: Unit does not have item!")
            return

    interaction.start_combat(
        actor, target, item, event_combat=True, script=script, total_rounds=total_rounds,
        arena='arena' in flags, force_animation='force_animation' in flags)
    self.state = "paused"

def recruit_generic(self: Event, unit, nid, name, flags=None):
    new_unit = self.game.get_unit(unit)
    if not new_unit:
        self.logger.error("recruit_generic: Couldn't find unit with nid %s" % unit)
        return
    unit = new_unit
    action.do(action.SetPersistent(unit))
    action.do(action.SetNid(unit, nid))
    action.do(action.SetName(unit, name))

def set_name(self: Event, unit, string, flags=None):
    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("set_name: Couldn't find unit %s" % unit)
        return
    action.do(action.SetName(actor, string))

def set_current_hp(self: Event, unit, hp, flags=None):
    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("set_current_hp: Couldn't find unit %s" % unit)
        return
    action.do(action.SetHP(actor, int(hp)))

def set_current_mana(self: Event, unit, mana, flags=None):
    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("set_current_mana: Couldn't find unit %s" % unit)
        return
    action.do(action.SetMana(actor, int(mana)))

def add_fatigue(self: Event, unit, fatigue, flags=None):
    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("add_fatigue: Couldn't find unit %s" % unit)
        return
    action.do(action.ChangeFatigue(actor, int(fatigue)))

def set_unit_field(self: Event, unit, key, value, flags=None):
    flags = flags or set()

    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("set_unit_field: Couldn't find unit %s" % unit)
        return
    try:
        value = self.text_evaluator.direct_eval(value)
    except:
        self.logger.error("set_unit_field: Could not evaluate {%s}" % value)
        return
    should_increment = False
    if 'increment_mode' in flags:
        should_increment = True
    action.do(action.ChangeField(actor, key, value, should_increment))

def resurrect(self: Event, global_unit, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("resurrect: Couldn't find unit %s" % global_unit)
        return
    if unit.dead:
        action.do(action.Resurrect(unit))
    action.do(action.Reset(unit))
    action.do(action.SetHP(unit, 1000))

def reset(self: Event, unit, flags=None):
    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("reset: Couldn't find unit %s" % unit)
        return
    action.do(action.Reset(actor))

def has_attacked(self: Event, unit, flags=None):
    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("has_attacked: Couldn't find unit %s" % unit)
        return
    action.do(action.HasAttacked(actor))

def has_traded(self: Event, unit, flags=None):
    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("has_traded: Couldn't find unit %s" % unit)
        return
    action.do(action.HasTraded(actor))

def has_finished(self: Event, unit, flags=None):
    actor = self._get_unit(unit)
    if not actor:
        self.logger.error("has_finished: Couldn't find unit %s" % unit)
        return
    action.do(action.Wait(actor))

def add_group(self: Event, group, starting_group=None, entry_type=None, placement=None, flags=None):
    flags = flags or set()

    new_group = self.game.level.unit_groups.get(group)
    if not new_group:
        self.logger.error("add_group: Couldn't find group %s" % group)
        return
    group = new_group
    next_pos = starting_group
    if not entry_type:
        entry_type = 'fade'
    if not placement:
        placement = 'giveup'
    create = 'create' in flags
    for unit_nid in group.units:
        unit = self.game.get_unit(unit_nid)
        if create:
            unit = self._copy_unit(unit_nid)
            if not unit:
                continue
        elif unit.position or unit.dead:
            continue
        position = self._get_position(next_pos, unit, group, unit_nid)
        if not position:
            continue
        position = tuple(position)
        position = self._check_placement(unit, position, placement)
        if not position:
            self.logger.warning("add_group: Couldn't determine valid position for %s?", unit.nid)
            continue
        if DB.constants.value('initiative'):
            action.do(action.InsertInitiative(unit))
        self._place_unit(unit, position, entry_type)

def spawn_group(self: Event, group, cardinal_direction, starting_group, movement_type=None, placement=None, flags=None):
    flags = flags or set()

    new_group = self.game.level.unit_groups.get(group)
    if not new_group:
        self.logger.error("spawn_group: Couldn't find group %s", group)
        return
    group = new_group
    cardinal_direction = cardinal_direction.lower()
    if cardinal_direction not in ('east', 'west', 'north', 'south'):
        self.logger.error("spawn_group: %s not a legal cardinal direction", cardinal_direction)
        return
    next_pos = starting_group
    if not movement_type:
        movement_type = 'normal'
    if not placement:
        placement = 'giveup'
    create = 'create' in flags
    follow = 'no_follow' not in flags

    for unit_nid in group.units:
        unit = self.game.get_unit(unit_nid)
        if create:
            unit = self._copy_unit(unit_nid)
            if not unit:
                continue
        elif unit.position or unit.dead:
            self.logger.warning("spawn_group: Unit %s in group %s already on map or dead", unit.nid, group.nid)
            continue
        position = self._get_position(next_pos, unit, group, unit_nid)
        if not position:
            continue

        if self._add_unit_from_direction(unit, position, cardinal_direction, placement):
            if DB.constants.value('initiative'):
                action.do(action.InsertInitiative(unit))
            self._move_unit(movement_type, placement, follow, unit, position)
        else:
            self.logger.error("spawn_group: Couldn't add unit %s to position %s" % (unit.nid, position))

    if 'no_block' in flags or self.do_skip:
        pass
    else:
        self.state = 'paused'
        self.game.state.change('movement')

def move_group(self: Event, group, starting_group, movement_type=None, placement=None, flags=None):
    flags = flags or set()

    new_group = self.game.level.unit_groups.get(group)
    if not new_group:
        self.logger.error("move_group: Couldn't find group %s" % group)
        return
    group = new_group
    next_pos = starting_group
    if not movement_type:
        movement_type = 'normal'
    if not placement:
        placement = 'giveup'
    follow = 'no_follow' not in flags

    for unit_nid in group.units:
        unit = self.game.get_unit(unit_nid)
        if not unit.position:
            continue
        position = self._get_position(next_pos, unit, group)
        if not position:
            continue
        self._move_unit(movement_type, placement, follow, unit, position)

    if 'no_block' in flags or self.do_skip:
        pass
    else:
        self.state = 'paused'
        self.game.state.change('movement')

def remove_group(self: Event, group, remove_type=None, flags=None):
    new_group = self.game.level.unit_groups.get(group)
    if not new_group:
        self.logger.error("remove_group: Couldn't find group %s" % group)
        return
    group = new_group
    if not remove_type:
        remove_type = 'fade'
    for unit_nid in group.units:
        unit = self.game.get_unit(unit_nid)
        if DB.constants.value('initiative'):
            action.do(action.RemoveInitiative(unit))
        if unit.position:
            if self.do_skip:
                action.do(action.LeaveMap(unit))
            elif remove_type == 'warp':
                action.do(action.WarpOut(unit))
            elif remove_type == 'fade':
                action.do(action.FadeOut(unit))
            else:  # immediate
                action.do(action.LeaveMap(unit))

def give_item(self: Event, global_unit_or_convoy, item, flags=None):
    flags = flags or set()
    global_unit = global_unit_or_convoy

    if global_unit.lower() == 'convoy':
        unit = None
    else:
        unit = self._get_unit(global_unit)
        if not unit:
            self.logger.error("give_item: Couldn't find unit with nid %s" % global_unit)
            return
    item_id = item
    if item_id in DB.items.keys():
        item = item_funcs.create_item(None, item_id)
        self.game.register_item(item)
    elif str_utils.is_int(item_id) and int(item_id) in self.game.item_registry:
        item = self.game.item_registry[int(item_id)]
    else:
        self.logger.error("give_item: Couldn't find item with nid %s" % item_id)
        return
    banner_flag = 'no_banner' not in flags
    item.droppable = 'droppable' in flags

    if unit:
        if item_funcs.inventory_full(unit, item):
            if 'no_choice' in flags:
                action.do(action.PutItemInConvoy(item))
                if banner_flag:
                    self.game.alerts.append(banner.SentToConvoy(item))
                    self.game.state.change('alert')
                    self.state = 'paused'
            else:
                action.do(action.GiveItem(unit, item))
                self.game.cursor.cur_unit = unit
                self.game.state.change('item_discard')
                self.state = 'paused'
                if banner_flag:
                    self.game.alerts.append(banner.AcquiredItem(unit, item))
                    self.game.state.change('alert')
        else:
            action.do(action.GiveItem(unit, item))
            if banner_flag:
                self.game.alerts.append(banner.AcquiredItem(unit, item))
                self.game.state.change('alert')
                self.state = 'paused'
    else:
        action.do(action.PutItemInConvoy(item))
        if banner_flag:
            self.game.alerts.append(banner.SentToConvoy(item))
            self.game.state.change('alert')
            self.state = 'paused'

def equip_item(self: Event, global_unit, item, flags=None):
    flags = flags or set()
    recursive_flag = 'recursive' in flags
    item_input = item
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("equip_item: Couldn't find unit with nid %s" % global_unit)
        return
    unit, item = self._get_item_in_inventory(global_unit, item, recursive=recursive_flag)
    if not unit or not item:
        self.logger.error("equip_item: Item %s was invalid, see above" % item_input)
        return
    if item.multi_item:
        for subitem in item.subitems:
            if item_system.equippable(unit, subitem) and item_system.available(unit, subitem):
                equip_action = action.EquipItem(unit, subitem)
                action.do(equip_action)
                return
        self.logger.error("equip_item: No valid subitem to equip in %s" % item.nid)
    else:
        if not item_system.equippable(unit, item):
            self.logger.error("equip_item: %s is not an item that can be equipped" % item.nid)
            return
        if not item_system.available(unit, item):
            self.logger.error("equip_item: %s is unable to equip %s" % (unit.nid, item.nid))
            return
    equip_action = action.EquipItem(unit, item)
    action.do(equip_action)


def remove_item(self: Event, global_unit_or_convoy, item, flags=None):
    flags = flags or set()
    global_unit = global_unit_or_convoy

    unit, item = self._get_item_in_inventory(global_unit, item)
    if not unit or not item:
        self.logger.error("remove_item: Either unit or item was invalid, see above")
        return
    banner_flag = 'no_banner' not in flags

    if global_unit.lower() == 'convoy':
        action.do(action.RemoveItemFromConvoy(item))
    else:
        action.do(action.RemoveItem(unit, item))
        if banner_flag:
            item = DB.items.get(item.nid)
            b = banner.TakeItem(unit, item)
            self.game.alerts.append(b)
            self.game.state.change('alert')
            self.state = 'paused'

def set_item_uses(self: Event, global_unit_or_convoy, item, uses, flags=None):
    flags = flags or set()
    global_unit = global_unit_or_convoy

    unit, item = self._get_item_in_inventory(global_unit, item)
    if not unit or not item:
        self.logger.error("set_item_uses: Either unit or item was invalid, see above")
        return
    uses = int(uses)
    if 'additive' in flags:
        if 'starting_uses' in item.data:
            uses = item.data['uses'] + uses
        elif 'starting_c_uses' in item.data:
            uses = item.data['c_uses'] + uses

    if 'starting_uses' in item.data:
        action.do(action.SetObjData(item, 'uses', utils.clamp(uses, 0, item.data['starting_uses'])))
    elif 'starting_c_uses' in item.data:
        action.do(action.SetObjData(item, 'c_uses', utils.clamp(uses, 0, item.data['starting_c_uses'])))
    else:
        self.logger.error("set_item_uses: Item %s does not have uses!" % item.nid)

def set_item_data(self: Event, global_unit_or_convoy, item, nid, expression, flags=None):
    flags = flags or set()
    global_unit = global_unit_or_convoy

    unit, item = self._get_item_in_inventory(global_unit, item)
    if not unit or not item:
        self.logger.error("set_item_data: Either unit or item was invalid, see above")
        return

    try:
        data_value = self.text_evaluator.direct_eval(expression)
    except Exception as e:
        self.logger.error("set_item_data: %s: Could not evaluate {%s}" % (e, expression))
        return

    action.do(action.SetObjData(item, nid, data_value))

def change_item_name(self: Event, global_unit_or_convoy, item, string, flags=None):
    unit, item = self._get_item_in_inventory(global_unit_or_convoy, item)
    if not unit or not item:
        self.logger.error("change_item_name: Either unit or item was invalid, see above")
        return
    action.do(action.ChangeItemName(item, string))

def change_item_desc(self: Event, global_unit_or_convoy, item, string, flags=None):
    unit, item = self._get_item_in_inventory(global_unit_or_convoy, item)
    if not unit or not item:
        self.logger.error("change_item_desc: Either unit or item was invalid, see above")
        return
    action.do(action.ChangeItemDesc(item, string))

def add_item_to_multiitem(self: Event, global_unit_or_convoy, multi_item, child_item, flags=None):
    unit, item = self._get_item_in_inventory(global_unit_or_convoy, multi_item)
    if not unit or not item:
        self.logger.error("add_item_to_multiitem: Either unit or item was invalid, see above")
        return
    if not item.multi_item:
        self.logger.error("add_item_to_muliitem: Item %s is not a multi-item!" % item.nid)
        return
    subitem_prefab = DB.items.get(child_item)
    if not subitem_prefab:
        self.logger.error("add_item_to_multiitem: Couldn't find item with nid %s" % child_item)
        return
    if 'no_duplicate' in flags:
        children = {item.nid for item in item.subitems}
        if child_item in children:
            self.logger.info("add_item_to_multiitem: Item %s already exists on multi-item %s on unit %s" % (child_item, item.nid, unit.nid))
            return
    # Create subitem
    subitem = ItemObject.from_prefab(subitem_prefab)
    for component in subitem.components:
        component.item = item
    item_system.init(subitem)
    self.game.register_item(subitem)
    owner_nid = None
    if unit:
        owner_nid = unit.nid
    action.do(action.AddItemToMultiItem(owner_nid, item, subitem))
    if 'equip' in flags and owner_nid:
        action.do(action.EquipItem(unit, subitem))

def remove_item_from_multiitem(self: Event, global_unit_or_convoy, multi_item, child_item=None, flags=None):
    unit, item = self._get_item_in_inventory(global_unit_or_convoy, multi_item)
    if not unit or not item:
        self.logger.error("remove_item_from_multiitem: Either unit or item was invalid, see above")
        return
    if not item.multi_item:
        self.logger.error("remove_item_from_multiitem: Item %s is not a multi-item!" % item.nid)
        return
    if global_unit_or_convoy.lower() == 'convoy':
        owner_nid = None
    else:
        owner_nid = unit.nid
    if not child_item:
        # remove all subitems
        subitems = [subitem for subitem in item.subitems]
        for subitem in subitems:
            if owner_nid:
                action.do(action.UnequipItem(unit, subitem))
            action.do(action.RemoveItemFromMultiItem(owner_nid, item, subitem))
    else:
        # Check if item in multiitem
        subitem_nids = [subitem.nid for subitem in item.subitems]
        if child_item not in subitem_nids:
            self.logger.error("remove_item_from_multiitem: Couldn't find subitem with nid %s" % child_item)
            return
        subitem = [subitem for subitem in item.subitems if subitem.nid == child_item][0]
        # Unequip subitem if necessary
        if owner_nid:
            action.do(action.UnequipItem(unit, subitem))
        action.do(action.RemoveItemFromMultiItem(owner_nid, item, subitem))

def add_item_component(self: Event, global_unit_or_convoy, item, item_component, expression=None, flags=None):
    flags = flags or set()
    global_unit = global_unit_or_convoy
    component_nid = item_component

    unit, item = self._get_item_in_inventory(global_unit, item)
    if not unit or not item:
        self.logger.error("add_item_component: Either unit or item was invalid, see above")
        return

    if expression is not None:
        try:
            component_value = self.text_evaluator.direct_eval(expression)
        except Exception as e:
            self.logger.error("add_item_component: %s: Could not evalute {%s}" % (e, expression))
            return
    else:
        component_value = None

    action.do(action.AddItemComponent(item, component_nid, component_value))


def remove_item_component(self: Event, global_unit_or_convoy, item, item_component, flags=None):
    flags = flags or set()
    global_unit = global_unit_or_convoy
    component_nid = item_component

    unit, item = self._get_item_in_inventory(global_unit, item)
    if not unit or not item:
        self.logger.error("remove_item_component: Either unit or item was invalid, see above")
        return

    action.do(action.RemoveItemComponent(item, component_nid))

def give_money(self: Event, money, party=None, flags=None):
    flags = flags or set()

    money = int(money)
    if party:
        party_nid = party
    else:
        party_nid = self.game.current_party
    banner_flag = 'no_banner' not in flags

    action.do(action.GainMoney(party_nid, money))
    if banner_flag:
        if money >= 0:
            b = banner.Advanced('Got <blue>{money}</> gold.'.format(money = str(money)), 'Item')
        else:
            b = banner.Advanced('Lost <blue>{money}</> gold.'.format(money = str(money)), 'ItemBreak')
        self.game.alerts.append(b)
        self.game.state.change('alert')
        self.state = 'paused'

def give_bexp(self: Event, bexp, party=None, string=None, flags=None):
    flags = flags or set()

    bexp = int(bexp)
    if party:
        party_nid = party
    else:
        party_nid = self.game.current_party
    banner_flag = 'no_banner' not in flags

    action.do(action.GiveBexp(party_nid, bexp))

    if banner_flag:
        if string:
            b = banner.Advanced('<blue>{val2}</>: <blue>{val}</> BEXP.'.format(val2=string, val=bexp), 'Item')
        else:
            b = banner.Advanced('Got <blue>{val}</> BEXP.'.format(val=str(bexp)), 'Item')
        self.game.alerts.append(b)
        self.game.state.change('alert')
        self.state = 'paused'

def give_exp(self: Event, global_unit, experience, flags=None):
    flags = flags or set()

    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("give_exp: Couldn't find unit with nid %s" % global_unit)
        return
    exp = utils.clamp(int(experience), -100, 100)
    if 'silent' in flags:
        old_exp = unit.exp
        if old_exp + exp >= 100:
            if unit.level < DB.classes.get(unit.klass).max_level:
                action.do(action.GainExp(unit, exp))
                autolevel_to(self, global_unit, unit.level + 1)
            else:
                action.do(action.SetExp(unit, 99))
        elif old_exp + exp < 0:
            if unit.level > 1:
                action.do(action.SetExp(unit, 100 + old_exp - exp))
                autolevel_to(self, global_unit, unit.level - 1)
            else:
                action.do(action.SetExp(unit, 0))
        else:
            action.do(action.SetExp(unit, old_exp + exp))
    else:
        self.game.exp_instance.append((unit, exp, None, 'init'))
        self.game.state.change('exp')
        self.state = 'paused'

def set_exp(self: Event, global_unit, experience, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("set_exp: Couldn't find unit with nid %s" % global_unit)
        return
    exp = utils.clamp(int(experience), 0, 100)
    action.do(action.SetExp(unit, exp))

def give_wexp(self: Event, global_unit, weapon_type, positive_integer, flags=None):
    flags = flags or set()

    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("give_wexp: Couldn't find unit with nid %s" % global_unit)
        return
    wexp = int(positive_integer)
    if 'no_banner' in flags:
        action.execute(action.AddWexp(unit, weapon_type, wexp))
    else:
        action.do(action.AddWexp(unit, weapon_type, wexp))
        self.state = 'paused'

def give_skill(self: Event, global_unit, skill, initiator=None, flags=None):
    flags = flags or set()

    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("give_skill: Couldn't find unit with nid %s" % global_unit)
        return
    skill_nid = skill
    if skill_nid not in DB.skills.keys():
        self.logger.error("give_skill: Couldn't find skill with nid %s" % skill)
        return
    if initiator is not None:
        initiator = self._get_unit(initiator)
        if not initiator:
            self.logger.error("Couldn't find unit with nid %s" % initiator)
            return
    banner_flag = 'no_banner' not in flags
    action.do(action.AddSkill(unit, skill_nid, initiator))
    if banner_flag:
        skill = DB.skills.get(skill_nid)
        b = banner.GiveSkill(unit, skill)
        self.game.alerts.append(b)
        self.game.state.change('alert')
        self.state = 'paused'

def remove_skill(self: Event, global_unit, skill, count='-1', flags=None):
    flags = flags or set()
    count = int(count)

    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("remove_skill: Couldn't find unit with nid %s" % global_unit)
        return
    skill_nid = skill
    if skill_nid not in [skill.nid for skill in unit.skills]:
        self.logger.error("remove_skill: Couldn't find skill with nid %s" % skill)
        return
    banner_flag = 'no_banner' not in flags

    action.do(action.RemoveSkill(unit, skill_nid, count))
    if banner_flag:
        skill = DB.skills.get(skill_nid)
        b = banner.TakeSkill(unit, skill)
        self.game.alerts.append(b)
        self.game.state.change('alert')
        self.state = 'paused'

def change_ai(self: Event, global_unit, ai, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("change_ai: Couldn't find unit %s" % global_unit)
        return
    if ai in DB.ai.keys():
        action.do(action.ChangeAI(unit, ai))
    else:
        self.logger.error("change_ai: Couldn't find AI %s" % ai)
        return

def change_party(self: Event, global_unit, party, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("change_party: Couldn't find unit %s" % global_unit)
        return
    if party in DB.parties.keys():
        action.do(action.ChangeParty(unit, party))
    else:
        self.logger.error("change_party: Couldn't find Party %s" % party)
        return

def change_team(self: Event, global_unit, team, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("change_team: Couldn't find unit %s" % global_unit)
        return
    if team in DB.teams:
        action.do(action.ChangeTeam(unit, team))
    else:
        self.logger.error("change_team: Not a valid team: %s" % team)
        return

def change_portrait(self: Event, global_unit, portrait_nid, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("change_portrait: Couldn't find unit %s" % global_unit)
        return
    portrait = RESOURCES.portraits.get(portrait_nid)
    if not portrait:
        self.logger.error("change_portrait: Couldn't find portrait %s" % portrait_nid)
        return
    action.do(action.ChangePortrait(unit, portrait_nid))

def change_stats(self: Event, global_unit, stat_list, flags=None):
    flags = flags or set()

    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("change_stats: Couldn't find unit %s" % global_unit)
        return

    s_list = stat_list.split(',')
    stat_changes = {}
    for idx in range(len(s_list)//2):
        stat_nid = s_list[idx*2]
        stat_value = int(s_list[idx*2 + 1])
        stat_changes[stat_nid] = stat_value

    self._apply_stat_changes(unit, stat_changes, flags)

def set_stats(self: Event, global_unit, stat_list, flags=None):
    flags = flags or set()

    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("set_stats: Couldn't find unit %s" % global_unit)
        return

    s_list = stat_list.split(',')
    stat_changes = {}
    for idx in range(len(s_list)//2):
        stat_nid = s_list[idx*2]
        stat_value = int(s_list[idx*2 + 1])
        if stat_nid in unit.stats:
            current = unit.stats[stat_nid]
            stat_changes[stat_nid] = stat_value - current

    self._apply_stat_changes(unit, stat_changes, flags)

def change_growths(self: Event, global_unit, stat_list, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("change_growths: Couldn't find unit %s" % global_unit)
        return

    s_list = stat_list.split(',')
    growth_changes = {}
    for idx in range(len(s_list)//2):
        stat_nid = s_list[idx*2]
        stat_value = int(s_list[idx*2 + 1])
        growth_changes[stat_nid] = stat_value

    self._apply_growth_changes(unit, growth_changes)

def set_growths(self: Event, global_unit, stat_list, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("set_growths: Couldn't find unit %s" % global_unit)
        return

    s_list = stat_list.split(',')
    growth_changes = {}
    for idx in range(len(s_list)//2):
        stat_nid = s_list[idx*2]
        stat_value = int(s_list[idx*2 + 1])
        if stat_nid in unit.growths:
            current = unit.growths[stat_nid]
            growth_changes[stat_nid] = stat_value - current

    self._apply_growth_changes(unit, growth_changes)

def autolevel_to(self: Event, global_unit, level, growth_method=None, flags=None):
    flags = flags or set()

    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("autolevel_to: Couldn't find unit %s" % global_unit)
        return
    final_level = int(level)
    current_level = unit.level
    diff = final_level - current_level
    if diff == 0:
        self.logger.warning("autolevel_to: Unit %s is already that level!" % global_unit)
        return

    action.do(action.AutoLevel(unit, diff, growth_method))
    if 'hidden' in flags:
        pass
    else:
        action.do(action.SetLevel(unit, max(1, final_level)))
    if not unit.generic and DB.units.get(unit.nid):
        unit_prefab = DB.units.get(unit.nid)
        personal_skills = unit_funcs.get_personal_skills(unit, unit_prefab)
        for personal_skill in personal_skills:
            action.do(action.AddSkill(unit, personal_skill))
    class_skills = unit_funcs.get_starting_skills(unit)
    for class_skill in class_skills:
        action.do(action.AddSkill(unit, class_skill))

def set_mode_autolevels(self: Event, level, flags=None):
    flags = flags or set()

    autolevel = int(level)
    if 'hidden' in flags:
        if 'boss' in flags:
            self.game.current_mode.boss_autolevels = autolevel
        else:
            self.game.current_mode.enemy_autolevels = autolevel
    else:
        if 'boss' in flags:
            self.game.current_mode.boss_truelevels = autolevel
        else:
            self.game.current_mode.enemy_truelevels = autolevel

def promote(self: Event, global_unit, klass_list=None, flags=None):
    flags = flags or set()
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("promote: Couldn't find unit %s" % global_unit)
        return
    if klass_list:
        s_klass = klass_list.split(',')
        if len(s_klass) == 1:
            new_klass = s_klass[0]
        else:
            self.game.memory['promo_options'] = s_klass
            new_klass = None
    else:
        klass = DB.classes.get(unit.klass)
        if len(klass.turns_into) == 0:
            self.logger.error("promote: No available promotions for %s" % klass)
            return
        elif len(klass.turns_into) == 1:
            new_klass = klass.turns_into[0]
        else:
            new_klass = None

    self.game.memory['current_unit'] = unit
    silent = 'silent' in flags
    if self.game.memory.get('promo_options', False):
        if silent:
            self.logger.warning("promote: silent flag set with multiple klass options. Silent will be ignored.")
        self.game.state.change('promotion_choice')
        self.game.state.change('transition_out')
        self.state = 'paused'
    elif silent and new_klass:
        swap_class = action.Promote(unit, new_klass)
        action.do(swap_class)
        #check for new class skill
        unit_klass = DB.classes.get(unit.klass)
        for level_needed, class_skill_nid in unit_klass.learned_skills:
            if unit.level == level_needed:
                if class_skill_nid == 'Feat':
                    self.game.memory['current_unit'] = unit
                    self.game.state.change('feat_choice')
                    self.state = 'paused'
                else:
                    if class_skill_nid not in [skill.nid for skill in unit.skills]:
                        act = action.AddSkill(unit, class_skill_nid)
                        action.do(act)
        _, new_wexp = swap_class.get_data()
        # check for weapon experience gain
        if new_wexp:
            for weapon_nid, value in new_wexp.items():
                # Execute for silent mode
                action.execute(action.AddWexp(unit, weapon_nid, value))
        action.do(action.UpdateRecords('level_gain', (unit.nid, unit.level, unit.klass)))
    elif new_klass:
        self.game.memory['next_class'] = new_klass
        self.game.state.change('promotion')
        self.game.state.change('transition_out')
        self.state = 'paused'
    else:
        self.game.state.change('promotion_choice')
        self.game.state.change('transition_out')
        self.state = 'paused'

def change_class(self: Event, global_unit, klass=None, flags=None):
    flags = flags or set()

    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("change_class: Couldn't find unit %s" % global_unit)
        return
    if klass:
        new_klass = klass
    elif not unit.generic:
        unit_prefab = DB.units.get(unit.nid)
        if not unit_prefab.alternate_classes:
            self.logger.error("change_class: No available alternate classes for %s" % unit)
            return
        elif len(unit_prefab.alternate_classes) == 1:
            new_klass = unit_prefab.alternate_classes[0]
        else:
            new_klass = None

    if new_klass == unit.klass:
        self.logger.error("change_class: No need to change classes")
        return

    self.game.memory['current_unit'] = unit
    silent = 'silent' in flags
    if silent and new_klass:
        swap_class = action.ClassChange(unit, new_klass)
        action.do(swap_class)
        #check for new class skill
        unit_klass = DB.classes.get(unit.klass)
        for level_needed, class_skill_nid in unit_klass.learned_skills:
            if unit.level == level_needed:
                if class_skill_nid == 'Feat':
                    self.game.memory['current_unit'] = unit
                    self.game.state.change('feat_choice')
                    self.state = 'paused'
                else:
                    if class_skill_nid not in [skill.nid for skill in unit.skills]:
                        act = action.AddSkill(unit, class_skill_nid)
                        action.do(act)
        _, new_wexp = swap_class.get_data()
        # check for weapon experience gain
        if new_wexp:
            for weapon_nid, value in new_wexp.items():
                # Execute for silent mode
                action.execute(action.AddWexp(unit, weapon_nid, value))
        action.do(action.UpdateRecords('level_gain', (unit.nid, unit.level, unit.klass)))
    elif new_klass:
        self.game.memory['next_class'] = new_klass
        self.game.state.change('class_change')
        self.game.state.change('transition_out')
        self.state = 'paused'
    else:
        self.game.state.change('class_change_choice')
        self.game.state.change('transition_out')
        self.state = 'paused'

def add_tag(self: Event, global_unit, tag, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("add_tag: Couldn't find unit %s" % global_unit)
        return
    if tag in DB.tags.keys():
        action.do(action.AddTag(unit, tag))

def remove_tag(self: Event, global_unit, tag, flags=None):
    unit = self._get_unit(global_unit)
    if not unit:
        self.logger.error("add_tag: Couldn't find unit %s" % global_unit)
        return
    if tag in DB.tags.keys():
        action.do(action.RemoveTag(unit, tag))

def add_talk(self: Event, unit1, unit2, flags=None):
    action.do(action.AddTalk(unit1, unit2))

def remove_talk(self: Event, unit1, unit2, flags=None):
    action.do(action.RemoveTalk(unit1, unit2))

def add_lore(self: Event, lore, flags=None):
    action.do(action.AddLore(lore))

def remove_lore(self: Event, lore, flags=None):
    action.do(action.RemoveLore(lore))

def add_base_convo(self: Event, nid, flags=None):
    self.game.base_convos[nid] = False

def ignore_base_convo(self: Event, nid, ignore=None, flags=None):
    if nid in self.game.base_convos:
        if ignore is not None:
            ignore = ignore.lower() in self.true_vals
        else:
            ignore = True
        self.game.base_convos[nid] = ignore

def remove_base_convo(self: Event, nid, flags=None):
    if nid in self.game.base_convos:
        del self.game.base_convos[nid]

def increment_support_points(self: Event, unit1, unit2, support_points, flags=None):
    _unit1 = self._get_unit(unit1)
    if not _unit1:
        _unit1 = DB.units.get(unit1)
    if not _unit1:
        self.logger.error("increment_support_points: Couldn't find unit %s" % unit1)
        return
    unit1 = _unit1
    _unit2 = self._get_unit(unit2)
    if not _unit2:
        _unit2 = DB.units.get(unit2)
    if not _unit2:
        self.logger.error("increment_support_points: Couldn't find unit %s" % unit2)
        return
    unit2 = _unit2
    inc = int(support_points)
    prefabs = DB.support_pairs.get_pairs(unit1.nid, unit2.nid)
    if prefabs:
        prefab = prefabs[0]
        action.do(action.IncrementSupportPoints(prefab.nid, inc))
    else:
        self.logger.error("increment_support_points: Couldn't find prefab for units %s and %s" % (unit1.nid, unit2.nid))
        return

def unlock_support_rank(self: Event, unit1, unit2, support_rank, flags=None):
    _unit1 = self._get_unit(unit1)
    if not _unit1:
        _unit1 = DB.units.get(unit1)
    if not _unit1:
        self.logger.error("unlock_support_rank: Couldn't find unit %s" % unit1)
        return
    _unit2 = self._get_unit(unit2)
    if not _unit2:
        _unit2 = DB.units.get(unit2)
    if not _unit2:
        self.logger.error("unlock_support_rank: Couldn't find unit %s" % unit2)
        return
    rank = support_rank
    if rank not in DB.support_ranks.keys():
        self.logger.error("unlock_support_rank: Support rank %s not a valid rank!" % rank)
        return
    prefabs = DB.support_pairs.get_pairs(_unit1.nid, _unit2.nid)
    if prefabs:
        prefab = prefabs[0]
        action.do(action.UnlockSupportRank(prefab.nid, rank))
    else:
        self.logger.error("unlock_support_rank: Couldn't find prefab for units %s and %s" % (_unit1.nid, _unit2.nid))
        return

def add_market_item(self: Event, item, stock=None, flags=None):
    if item not in DB.items.keys():
        self.logger.warning("add_market_item: %s is not a legal item nid", item)
        return
    stock = int(stock) if stock else 0
    if stock:
        if item in self.game.market_items:
            self.game.market_items[item] += stock
        else:
            self.game.market_items[item] = stock
    else:
        self.game.market_items[item] = -1  # Any negative number means infinite

def remove_market_item(self: Event, item, stock=None, flags=None):
    if item not in DB.items.keys():
        self.logger.warning("remove_market_item: %s is not a legal item nid", item)
        return
    stock = int(stock) if stock else 0
    if stock and item in self.game.market_items:
        self.game.market_items[item] -= stock
        if self.game.market_items[item] <= 0:
            self.game.market_items.pop(item, None)
    else:
        self.game.market_items.pop(item, None)

def clear_market_items(self: Event, flags=None):
    self.game.market_items.clear()

def add_region(self: Event, region, position, size, region_type, string=None, flags=None):
    flags = flags or set()

    if region in self.game.level.regions.keys():
        self.logger.error("add_region: Region nid %s already present!" % region)
        return
    position = self._parse_pos(position)
    size = self._parse_pos(size)
    if not size:
        size = (1, 1)
    region_type = region_type.lower()
    sub_region_type = string

    new_region = regions.Region(region)
    new_region.region_type = regions.RegionType(region_type)
    new_region.position = position
    new_region.size = size
    new_region.sub_nid = sub_region_type

    if 'only_once' in flags:
        new_region.only_once = True
    if 'interrupt_move' in flags:
        new_region.interrupt_move = True

    self.game.register_region(new_region)
    action.do(action.AddRegion(new_region))

def region_condition(self: Event, region, expression, flags=None):
    if region in self.game.level.regions.keys():
        region = self.game.level.regions.get(region)
        action.do(action.ChangeRegionCondition(region, expression))
    else:
        self.logger.error("region_condition: Couldn't find Region %s" % region)

def remove_region(self: Event, region, flags=None):
    if region in self.game.level.regions.keys():
        region = self.game.level.regions.get(region)
        action.do(action.RemoveRegion(region))
    else:
        self.logger.error("remove_region: Couldn't find Region %s" % region)

def show_layer(self: Event, layer, layer_transition=None, flags=None):
    if layer not in self.game.level.tilemap.layers.keys():
        self.logger.error("show_layer: Could not find layer %s in tilemap" % layer)
        return
    if not layer_transition:
        layer_transition = 'fade'

    if self.game.level.tilemap.layers.get(layer).visible:
        self.logger.warning("show_layer: Layer %s is already visible!" % layer)
        return
    action.do(action.ShowLayer(layer, layer_transition))

def hide_layer(self: Event, layer, layer_transition=None, flags=None):
    if layer not in self.game.level.tilemap.layers.keys():
        self.logger.error("hide_layer: Could not find layer %s in tilemap" % layer)
        return
    if not layer_transition:
        layer_transition = 'fade'

    if not self.game.level.tilemap.layers.get(layer).visible:
        self.logger.warning("hide_layer: Layer %s is already hidden!" % layer)
        return
    action.do(action.HideLayer(layer, layer_transition))

def add_weather(self: Event, weather, position=None, flags=None):
    nid = weather.lower()
    if position:
        pos = self._parse_pos(position)
    else:
        pos = None
    action.do(action.AddWeather(nid, pos))

def remove_weather(self: Event, weather, position=None, flags=None):
    nid = weather.lower()
    if position:
        pos = self._parse_pos(position)
    else:
        pos = None
    action.do(action.RemoveWeather(nid, pos))

def change_objective_simple(self: Event, string, flags=None):
    action.do(action.ChangeObjective('simple', string))

def change_objective_win(self: Event, string, flags=None):
    action.do(action.ChangeObjective('win', string))

def change_objective_loss(self: Event, string, flags=None):
    action.do(action.ChangeObjective('loss', string))

def set_position(self: Event, position, flags=None):
    pos = self._parse_pos(position)
    self.position = pos
    self.text_evaluator.position = pos

def map_anim(self: Event, map_anim, float_position, speed=None, flags=None):
    flags = flags or set()

    if map_anim not in RESOURCES.animations.keys():
        self.logger.error("map_anim: Could not find map animation %s" % map_anim)
        return
    pos = self._parse_pos(float_position, True)
    assert(pos is not None)
    if speed:
        speed_mult = float(speed)
    else:
        speed_mult = 1
    mode = engine.BlendMode.NONE
    if 'blend' in flags:
        mode = engine.BlendMode.BLEND_RGB_ADD
    elif 'multiply' in flags:
        mode = engine.BlendMode.BLEND_RGB_MULT
    if 'permanent' in flags:
        action.do(action.AddMapAnim(map_anim, pos, speed_mult, mode, 'overlay' in flags))
    else:
        anim = RESOURCES.animations.get(map_anim)
        anim = MapAnimation(anim, pos, speed_adj=speed_mult)
        anim.set_tint(mode)
        self.animations.append(anim)

    if 'no_block' in flags or self.do_skip or 'permanent' in flags:
        pass
    else:
        self.wait_time = engine.get_time() + anim.get_wait()
        self.state = 'waiting'

def remove_map_anim(self: Event, map_anim, position, flags=None):
    pos = self._parse_pos(position, True)
    action.do(action.RemoveMapAnim(map_anim, pos))

def add_unit_map_anim(self: Event, map_anim: NID, unit: NID, speed=None, flags=None):
    flags = flags or set()

    if map_anim not in RESOURCES.animations.keys():
        self.logger.error("add_unit_map_anim: Could not find map animation %s" % map_anim)
        return
    unit_nid = unit
    unit = self._get_unit(unit_nid)
    if not unit:
        self.logger.error("add_unit_map_anim: Could not find unit %s" % unit_nid)
        return
    if speed:
        speed_mult = float(speed)
    else:
        speed_mult = 1
    if 'permanent' in flags:
        action.do(action.AddAnimToUnit(map_anim, unit, speed_mult, 'blend' in flags))
    else:
        anim = RESOURCES.animations.get(map_anim)
        pos = unit.position
        if pos:
            anim = MapAnimation(anim, pos, speed_adj=speed_mult)
            anim.set_tint('blend' in flags)
            self.animations.append(anim)

    if 'no_block' in flags or self.do_skip or 'permanent' in flags:
        pass
    else:
        self.wait_time = engine.get_time() + anim.get_wait()
        self.state = 'waiting'

def remove_unit_map_anim(self: Event, map_anim, unit, flags=None):
    unit = self._get_unit(unit)
    if not unit:
        self.logger.error("remove_unit_map_anim: Could not find unit %s" % unit)
        return
    action.do(action.RemoveAnimFromUnit(map_anim, unit))

def merge_parties(self: Event, party1, party2, flags=None):
    host, guest = party1, party2
    if host not in DB.parties.keys():
        self.logger.error("merge_parties: Could not locate party %s" % host)
        return
    if guest not in DB.parties.keys():
        self.logger.error("merge_parties: Could not locate party %s" % guest)
        return
    guest_party = self.game.get_party(guest)
    # Merge units
    for unit in self.game.units:
        if unit.party == guest:
            action.do(action.ChangeParty(unit, host))
    # Merge items
    for item in guest_party.convoy:
        action.do(action.RemoveItemFromConvoy(item, guest))
        action.do(action.PutItemInConvoy(item, host))
    # Merge money
    action.do(action.GainMoney(host, guest_party.money))
    action.do(action.GainMoney(guest, -guest_party.money))
    # Merge bexp
    action.do(action.GiveBexp(host, guest_party.bexp))
    action.do(action.GiveBexp(guest, -guest_party.bexp))

def arrange_formation(self: Event, flags=None):
    player_units = self.game.get_units_in_party()
    stuck_units = [unit for unit in player_units if unit.position and not self.game.check_for_region(unit.position, 'formation')]
    unstuck_units = [unit for unit in player_units if unit not in stuck_units and not self.game.check_for_region(unit.position, 'formation')]
    unstuck_units = [unit for unit in unstuck_units if 'Blacklist' not in unit.tags]
    if DB.constants.value('fatigue') and self.game.game_vars.get('_fatigue') == 1:
        unstuck_units = [unit for unit in unstuck_units if unit.get_fatigue() < unit.get_max_fatigue()]
    # Place required units first
    unstuck_units = list(sorted(unstuck_units, key=lambda u: 'Required' in u.tags, reverse=True))
    num_slots = self.game.level_vars.get('_prep_slots')
    all_formation_spots = self.game.get_open_formation_spots()
    if num_slots is None:
        num_slots = len(all_formation_spots)
    assign_these = unstuck_units[:num_slots]
    for idx, unit in enumerate(assign_these):
        position = all_formation_spots[idx]
        action.execute(action.ArriveOnMap(unit, position))
        action.execute(action.Reset(unit))

def prep(self: Event, pick_units_enabled: str = None, music: str = None, other_options: str = None,
         other_options_enabled: str = None, other_options_on_select: str = None, flags=None):
    if pick_units_enabled and pick_units_enabled.lower() in self.true_vals:
        b = True
    else:
        b = False
    action.do(action.SetLevelVar('_prep_pick', b))
    if music:
        action.do(action.SetGameVar('_prep_music', music))

    if other_options:
        options_list = other_options.split(',')
        options_enabled = [False for option in options_list]
        options_events = [None for option in options_list]

        enabled_strs = other_options_enabled.split(',') if other_options_enabled else []
        if len(enabled_strs) <= len(options_enabled):
            for idx, is_enabled in enumerate(enabled_strs):
                if is_enabled in self.true_vals:
                    options_enabled[idx] = True
            action.do(action.SetGameVar('_prep_options_enabled', options_enabled))
        else:
            self.logger.error("prep: too many bools in option enabled list: ", other_options_enabled)
            return

        event_nids = other_options_on_select.split(',') if other_options_on_select else []
        if len(event_nids) <= len(options_events):
            for idx, event_nid in enumerate(event_nids):
                options_events[idx] = event_nid
            action.do(action.SetGameVar('_prep_options_events', options_events))
        else:
            self.logger.error("prep: too many events in option event list: ", other_options_on_select)
            return
        action.do(action.SetGameVar('_prep_additional_options', options_list))
    else:
        action.do(action.SetGameVar('_prep_options_enabled', []))
        action.do(action.SetGameVar('_prep_options_events', []))
        action.do(action.SetGameVar('_prep_additional_options', []))

    self.game.state.change('prep_main')
    self.state = 'paused'  # So that the message will leave the update loop

def base(self: Event, background: str, music: str = None, other_options: str = None,
         other_options_enabled: str = None, other_options_on_select: str = None, flags=None):
    flags = flags or set()

    # set panorama
    action.do(action.SetGameVar('_base_bg_name', background))
    # set music
    if music:
        action.do(action.SetGameVar('_base_music', music))

    if other_options:
        options_list = other_options.split(',')
        options_enabled = [False for option in options_list]
        options_events = [None for option in options_list]

        enabled_strs = other_options_enabled.split(',') if other_options_enabled else []
        if len(enabled_strs) <= len(options_enabled):
            for idx, is_enabled in enumerate(enabled_strs):
                if is_enabled in self.true_vals:
                    options_enabled[idx] = True
            action.do(action.SetGameVar('_base_options_disabled', [not enabled for enabled in options_enabled]))
        else:
            self.logger.error("base: too many bools in option enabled list: ", other_options_enabled)
            return

        event_nids = other_options_on_select.split(',') if other_options_on_select else []
        if len(event_nids) <= len(options_events):
            for idx, event_nid in enumerate(event_nids):
                options_events[idx] = event_nid
            action.do(action.SetGameVar('_base_options_events', options_events))
        else:
            self.logger.error("base: too many events in option event list: ", other_options_on_select)
            return
        action.do(action.SetGameVar('_base_additional_options', options_list))
    else:
        action.do(action.SetGameVar('_base_options_disabled', []))
        action.do(action.SetGameVar('_base_options_events', []))
        action.do(action.SetGameVar('_base_additional_options', []))


    if 'show_map' in flags:
        action.do(action.SetGameVar('_base_transparent', True))
    else:
        action.do(action.SetGameVar('_base_transparent', False))

    self.game.state.change('base_main')
    self.state = 'paused'

def shop(self: Event, unit, item_list, shop_flavor=None, stock_list=None, flags=None):
    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("shop: Must have a unit visit the shop!")
        return
    unit = new_unit
    shop_id = self.nid
    self.game.memory['shop_id'] = shop_id
    self.game.memory['current_unit'] = unit
    if shop_flavor == 'market':
        self.game.state.change('big_shop')
        self.state = 'paused'

    else:
        item_list = item_list.split(',') if item_list else []
        shop_items = item_funcs.create_items(unit, item_list)
        self.game.memory['shop_items'] = shop_items

        if shop_flavor:
            self.game.memory['shop_flavor'] = shop_flavor.lower()
        else:
            self.game.memory['shop_flavor'] = 'armory'

        if stock_list:
            stock_list = str_utils.intify(stock_list)
            # Remember which items have already been bought for this shop...
            for idx, item in enumerate(item_list):
                item_history = '__shop_%s_%s' % (shop_id, item)
                if item_history in self.game.level_vars:
                    stock_list[idx] -= self.game.level_vars[item_history]
            self.game.memory['shop_stock'] = stock_list
        else:
            self.game.memory['shop_stock'] = None

        self.game.state.change('shop')
        self.state = 'paused'

def choice(self: Event, nid: NID, title: str, choices: str, row_width: str = None, orientation: str = None,
           alignment: str = None, bg: str = None, event_nid: str = None, entry_type: str = None,
           dimensions: str = None, text_align: str = None, flags=None):
    flags = flags or set()

    nid = nid
    header = title

    if not row_width:
        row_width = '-1'
    if not bg:
        bg = 'menu_bg_base'
    if 'no_bg' in flags:
        bg = None

    # determine data type
    dtype = 'str'
    if entry_type:
        dtype = entry_type

    # figure out function or list of NIDs
    if 'expression' in flags:
        try:
            ast.parse(choices)
            def tryexcept(callback_expr):
                try:
                    val = self.text_evaluator.direct_eval(self.text_evaluator._evaluate_all(callback_expr))
                    if isinstance(val, list):
                        return val
                    else:
                        return [self._object_to_str(val)]
                except Exception as e:
                    self.logger.error("choice: Choice %s failed to evaluate expression %s with error %s", nid, callback_expr, str(e))
                    return [""]
            data = lambda: tryexcept(choices)
        except:
            self.logger.error('choice: %s is not a valid python expression' % choices)
    else: # list of NIDs
        choices = self.text_evaluator._evaluate_all(choices)
        data = choices.split(',')
        data = [s.strip().replace('{comma}', ',') for s in data]

    row_width = int(row_width)

    if not orientation:
        orientation = 'vertical'
    else:
        if orientation in ('h', 'horiz', 'horizontal'):
            orientation = 'horizontal'
        else:
            orientation = 'vertical'

    if not alignment:
        align = Alignments.CENTER
    else:
        align = Alignments(alignment)

    talign = HAlignment.LEFT
    if text_align:
        talign = HAlignment(text_align)

    size = None
    if dimensions:
        size = tuple([int(x) for x in dimensions.split(',')])

    should_persist = 'persist' in flags
    no_cursor = 'no_cursor' in flags
    arrows = 'arrows' in flags and orientation == 'horizontal'
    scroll_bar = 'scroll_bar' in flags and orientation == 'vertical'
    backable = 'backable' in flags

    event_context = {
        'unit': self.unit,
        'unit2': self.unit2,
        'position': self.position,
        'local_args': self.local_args
    }

    self.game.memory['player_choice'] = (nid, header, data, row_width,
                                    orientation, dtype, should_persist,
                                    align, bg, event_nid, size, no_cursor,
                                    arrows, scroll_bar, talign, backable, event_context)
    self.game.state.change('player_choice')
    self.state = 'paused'

def unchoice(self: Event, flags=None):
    try:
        prev_state = self.game.state.get_prev_state()
        if prev_state.name == 'player_choice':
            prev_state_nid = prev_state.nid
            unchoose_prev_state = self.game.memory[prev_state_nid + '_unchoice']
            if unchoose_prev_state:
                unchoose_prev_state()
    except Exception as e:
        self.logger.error("unchoice: Unchoice failed: " + e)

def table(self: Event, nid: NID, table_data: str, title: str = None,
          dimensions: str = None, row_width: str = None, alignment: str = None,
          bg: str = None, entry_type: str = None, text_align: str = None, flags=None):
    flags = flags or set()

    box_nids = [nid for nid, _ in self.other_boxes]
    if nid in box_nids:
        self.logger.error("table: UI element with nid %s already exists" % nid)
        return

    # default args
    if not dimensions:
        dimensions = "0, 1"
    if not row_width:
        row_width = '-1'
    if not bg:
        bg = 'menu_bg_base'
    if 'no_bg' in flags:
        bg = None

    rows, cols = tuple(int(i) for i in dimensions.split(','))
    row_width = int(row_width)

    # determine data type
    dtype = 'str'
    if entry_type:
        dtype = entry_type

    # figure out function or list of NIDs
    if 'expression' in flags:
        try:
            # eval once to make sure it's eval-able
            ast.parse(table_data)
            def tryexcept(callback_expr):
                try:
                    val = self.text_evaluator.direct_eval(self.text_evaluator._evaluate_all(callback_expr))
                    if isinstance(val, list):
                        return val
                    else:
                        return [self._object_to_str(val)]
                except:
                    self.logger.error("table: failed to eval %s", callback_expr)
                    return [""]
            data = lambda: tryexcept(table_data)
        except:
            self.logger.error('table: %s is not a valid python expression' % table_data)
    else: # list of NIDs
        table_data = self.text_evaluator._evaluate_all(table_data)
        data = table_data.split(',')
        data = [s.strip().replace('{comma}', ',') for s in data]

    align = Alignments.TOP_LEFT
    if alignment:
        align = Alignments(alignment)

    talign = HAlignment.LEFT
    if text_align:
        talign = HAlignment(text_align)

    table_ui = SimpleMenuUI(
        data, dtype, title=title, rows=rows, cols=cols,
        row_width=row_width, alignment=align, bg=bg,
        text_align=talign)
    self.other_boxes.append((nid, table_ui))

def remove_table(self: Event, nid, flags=None):
    self.other_boxes = [(bnid, box) for (bnid, box) in self.other_boxes if bnid != nid]

def text_entry(self: Event, nid, string, positive_integer=None, illegal_character_list=None, flags=None):
    flags = flags or set()

    header = string
    limit = 16
    illegal_characters = []
    force_entry = False
    if positive_integer:
        limit = int(positive_integer)
    if illegal_character_list:
        illegal_characters = illegal_character_list.split(',')
    force_entry = 'force_entry' in flags

    self.game.memory['text_entry'] = (nid, header, limit, illegal_characters, force_entry)
    self.game.state.change('text_entry')
    self.state = 'paused'

def chapter_title(self: Event, music=None, string=None, flags=None):
    custom_string = string
    self.game.memory['chapter_title_music'] = music
    self.game.memory['chapter_title_title'] = custom_string
    # End the skip here
    self.do_skip = False
    self.super_skip = False
    self.game.state.change('chapter_title')
    self.state = 'paused'

def draw_overlay_sprite(self: Event, nid, sprite_id, position=None, z_level=None, animation=None, flags=None):
    flags = flags or set()

    name = nid
    sprite_nid = sprite_id
    z = 0
    pos = (0, 0)
    if position:
        pos = tuple(str_utils.intify(position))
    if z_level:
        z = int(z_level)
    anim_dir = animation

    sprite = SPRITES.get(sprite_nid)
    component = UIComponent.from_existing_surf(sprite)
    component.name = name
    component.disable()
    x, y = pos
    if anim_dir:
        if anim_dir == 'fade':
            enter_anim = fade_anim(0, 1, 1000)
            exit_anim = fade_anim(1, 0, 1000)
            component.margin = (x, y, 0, 0)
        else:
            if anim_dir == 'west':
                start_x = -component.width
                start_y = y
            elif anim_dir == 'east':
                start_x = WINWIDTH
                start_y = y
            elif anim_dir == 'north':
                start_x = x
                start_y = -component.height
            elif anim_dir == 'south':
                start_x = x
                start_y = WINHEIGHT
            enter_anim = translate_anim((start_x, start_y), (x, y), 750, interp_mode=InterpolationType.CUBIC)
            exit_anim = translate_anim((x, y), (start_x, start_y), 750, disable_after=True, interp_mode=InterpolationType.CUBIC)
        component.save_animation(enter_anim, '!enter')
        component.save_animation(exit_anim, '!exit')
    else:
        component.margin = (x, y, 0, 0)
    self.overlay_ui.add_child(component)
    if self.do_skip:
        component.enable()
        return
    else:
        component.enter()

    if anim_dir and 'no_block' not in flags:
        self.wait_time = engine.get_time() + 750
        self.state = 'waiting'

def remove_overlay_sprite(self: Event, nid, flags=None):
    flags = flags or set()
    component = self.overlay_ui.get_child(nid)
    if component:
        if self.do_skip:
            component.disable()
        else:
            component.exit()
            if component.is_animating() and 'no_block' not in flags:
                self.wait_time = engine.get_time() + 750
                self.state = 'waiting'

def alert(self: Event, string, item=None, skill=None, icon=None, flags=None):
    if item and item in DB.items.keys():
        custom_item = DB.items.get(item)
        self.game.alerts.append(banner.CustomIcon(string, custom_item))
    elif skill and skill in DB.skills.keys():
        custom_skill = DB.skills.get(skill)
        self.game.alerts.append(banner.CustomIcon(string, custom_skill))
    elif icon and any([sheet.get_index(icon) for sheet in RESOURCES.icons16]):
        self.game.alerts.append(banner.CustomIcon(string, icon))
    else:
        self.game.alerts.append(banner.Custom(string))
    self.game.state.change('alert')
    self.state = 'paused'

def victory_screen(self: Event, flags=None):
    self.game.state.change('victory')
    self.state = 'paused'

def records_screen(self: Event, flags=None):
    self.game.state.change('base_records')
    self.state = 'paused'

def location_card(self: Event, string, flags=None):
    new_location_card = dialog.LocationCard(string)
    self.other_boxes.append((None, new_location_card))

    self.wait_time = engine.get_time() + new_location_card.exist_time
    self.state = 'waiting'

def credits(self: Event, role, credits, flags=None):
    flags = flags or set()

    title = role or ''
    credits = credits.split(',') if 'no_split' not in flags else [credits]
    wait = 'wait' in flags
    center = 'center' in flags

    new_credits = dialog.Credits(title, credits, wait, center)
    self.other_boxes.append((None, new_credits))

    self.wait_time = engine.get_time() + new_credits.wait_time()
    self.state = 'waiting'

def ending(self: Event, portrait, title, text, flags=None):
    unit = self._get_unit(portrait)
    if unit and unit.portrait_nid:
        portrait, _ = icons.get_portrait(unit)
        portrait = portrait.convert_alpha()
        portrait = image_mods.make_translucent(portrait, 0.2)
    else:
        self.logger.error("ending: Couldn't find unit or portrait %s" % portrait)
        return False

    new_ending = dialog.Ending(portrait, title, text, unit)
    self.text_boxes.append(new_ending)
    self.state = 'dialog'

def pop_dialog(self: Event, flags=None):
    if self.text_boxes:
        self.text_boxes.pop()

def unlock(self: Event, unit, flags=None):
    # This is a macro that just adds new commands to command list
    find_unlock_command = event_commands.FindUnlock({'Unit': unit})
    spend_unlock_command = event_commands.SpendUnlock({'Unit': unit})
    # Done backwards to preseve order upon insertion
    self.commands.insert(self.command_idx + 1, spend_unlock_command)
    self.commands.insert(self.command_idx + 1, find_unlock_command)

def find_unlock(self: Event, unit, flags=None):
    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("find_unlock: Couldn't find unit with nid %s" % unit)
        return
    unit = new_unit
    region = self.local_args.get('region')
    if not region:
        self.logger.error("find_unlock: Can only find_unlock within a region's event script")
        return
    if skill_system.can_unlock(unit, region):
        self.game.memory['unlock_item'] = None
        return  # We're done here

    all_items = []
    for item in item_funcs.get_all_items(unit):
        if item_funcs.available(unit, item) and \
                item_system.can_unlock(unit, item, region):
            all_items.append(item)

    if len(all_items) > 1:
        self.game.memory['current_unit'] = unit
        self.game.memory['all_unlock_items'] = all_items
        self.game.state.change('unlock_select')
        self.state = 'paused'
    elif len(all_items) == 1:
        self.game.memory['unlock_item'] = all_items[0]
    else:
        self.logger.debug("find_unlock: Somehow unlocked event without being able to")
        self.game.memory['unlock_item'] = None

def spend_unlock(self: Event, unit, flags=None):
    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("spend_unlock: Couldn't find unit with nid %s" % unit)
        return
    unit = new_unit

    chosen_item = self.game.memory.get('unlock_item')
    self.game.memory['unlock_item'] = None
    if not chosen_item:
        return

    actions, playback = [], []
    # In order to proc uses, c_uses etc.
    item_system.start_combat(playback, unit, chosen_item, None, None)
    item_system.on_hit(actions, playback, unit, chosen_item, None, self.position, None, (0, 0), True)
    for act in actions:
        action.do(act)
    item_system.end_combat(playback, unit, chosen_item, None, None)

    if unit.get_hp() <= 0:
        # Force can't die unlocking stuff, because I don't want to deal with that nonsense
        action.do(action.SetHP(unit, 1))

    # Check to see if we broke the item we were using
    if item_system.is_broken(unit, chosen_item):
        alert = item_system.on_broken(unit, chosen_item)
        if alert and unit.team == 'player':
            self.game.alerts.append(banner.BrokenItem(unit, chosen_item))
            self.game.state.change('alert')
            self.state = 'paused'

def trigger_script(self: Event, event, unit1=None, unit2=None, flags=None):
    if unit1:
        unit = self._get_unit(unit1)
    else:
        unit = self.unit
    if unit2:
        unit2 = self._get_unit(unit2)
    else:
        unit2 = self.unit2

    valid_events = DB.events.get_by_nid_or_name(event, self.game.level.nid)
    for event_prefab in valid_events:
        self.game.events.trigger_specific_event(event_prefab.nid, unit, unit2, self.position, self.local_args)
        self.state = 'paused'

    if not valid_events:
        self.logger.error("trigger_script: Couldn't find any valid events matching name %s" % event)

def trigger_script_with_args(self: Event, event: str, arg_list: str = None, flags=None):
    trigger_script = event
    valid_events = DB.events.get_by_nid_or_name(trigger_script, self.game.level.nid)

    # Process Arg List into local args directory
    a_list = arg_list.split(',')
    local_args = {}
    for idx in range(len(a_list)//2):
        arg_nid = a_list[idx*2]
        arg_value = a_list[idx*2 + 1]
        local_args[arg_nid] = arg_value

    for event_prefab in valid_events:
        self.game.events.trigger_specific_event(event_prefab.nid, local_args=local_args)
        self.state = 'paused'
    if not valid_events:
        self.logger.error("trigger_script_with_args: Couldn't find any valid events matching name %s" % trigger_script)
        return

def loop_units(self: Event, expression, event, flags=None):
    unit_list_str = expression
    try:
        unit_list = self.text_evaluator.direct_eval(unit_list_str)
    except Exception as e:
        self.logger.error("loop_units: %s: Could not evalute {%s}" % (e, unit_list_str))
        return
    if not unit_list:
        self.logger.warning("loop_units: No units returned for list: %s" % (unit_list_str))
        return
    if not all((isinstance(unit_nid, str) or isinstance(unit_nid, UnitObject)) for unit_nid in unit_list):
        self.logger.error("loop_units: %s: could not evaluate to NID list {%s}" % ('loop_units', unit_list_str))
        return
    for unit_nid in reversed(unit_list):
        if not isinstance(unit_nid, str):
            unit_nid = unit_nid.nid  # Try this!
        macro_command = event_commands.TriggerScript({'Event': event, 'Unit1': unit_nid})
        self.commands.insert(self.command_idx + 1, macro_command)

def change_roaming(self: Event, free_roam_enabled, flags=None):
    val = free_roam_enabled.lower()
    if self.game.level:
        self.game.action_log.set_first_free_action()
        self.game.level.roam = val in self.true_vals

def change_roaming_unit(self: Event, unit, flags=None):
    if self.game.level:
        unit = self._get_unit(unit)
        if unit:
            self.game.level.roam_unit = unit.nid
        else:
            self.game.level.roam_unit = None

def clean_up_roaming(self: Event, flags=None):
    # Not turnwheel compatible
    for unit in self.game.units:
        if unit.position and not unit == self.game.level.roam_unit:
            action.do(action.FadeOut(unit))
    if DB.constants.value('initiative'):
        self.game.initiative.clear()
        self.game.initiative.insert_unit(self.game.level.roam_unit)

def add_to_initiative(self: Event, unit, integer, flags=None):
    # NOT CURRENTLY TURNWHEEL COMPATIBLE
    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("add_to_initiative: Couldn't find unit with nid %s" % unit)
        return
    unit = new_unit
    pos = int(integer)
    if DB.constants.value('initiative'):
        self.game.initiative.remove_unit(unit)
        self.game.initiative.insert_at(unit, self.game.initiative.current_idx + pos)

def move_in_initiative(self: Event, unit, integer, flags=None):
    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("move_in_initiative: Couldn't find unit with nid %s" % unit)
        return
    unit = new_unit
    offset = int(integer)
    action.do(action.MoveInInitiative(unit, offset))

def pair_up(self: Event, unit1, unit2, flags=None):
    new_unit1 = self._get_unit(unit1)
    if not new_unit1:
        self.logger.error("pair_up: Couldn't find unit with nid %s" % unit1)
        return
    unit1 = new_unit1
    new_unit2 = self._get_unit(unit2)
    if not new_unit2:
        self.logger.error("pair_up: Couldn't find unit with nid %s" % unit2)
        return
    unit2 = new_unit2
    action.do(action.PairUp(unit1, unit2))

def separate(self: Event, unit, flags=None):
    new_unit = self._get_unit(unit)
    if not new_unit:
        self.logger.error("separate: Couldn't find unit with nid %s" % unit)
        return
    unit = new_unit
    action.do(action.RemovePartner(unit))
