from enum import Enum, IntEnum, StrEnum, auto
from functools import lru_cache
from math import cos, radians, sin
from typing import Dict, List, Tuple
from app.data.database.klass import Klass
from app.engine.game_menus.animated_options import BasicUnitOption

from app.engine.game_menus.icon_options import ItemOptionUtils


from app.data.database.units import UnitPrefab
from app.engine.persistent_records import RECORDS
from app.engine.unit_sprite import UnitSprite, load_map_sprite

from app.utilities.typing import NID, Point

from app.engine.game_menus.menu_components.generic_menu.grid_choice import GridChoiceMenu

from app.constants import WINHEIGHT, WINWIDTH
from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.engine import (background, combat_calcs, engine, equations, gui,
                        help_menu, icons, image_mods, item_funcs, item_system,
                        skill_system, text_funcs, unit_funcs)
from app.engine.fluid_scroll import FluidScroll
from app.utilities.utils import frames2ms
from app.utilities.algorithms import interpolation
from app.engine.game_menus import menu_options
from app.engine.game_menus.icon_options import BasicItemOption, ItemOptionModes
from app.engine.game_state import game
from app.engine.graphics.ingame_ui.build_groove import build_groove
from app.engine.graphics.text.text_renderer import render_text, text_width
from app.engine.info_menu.info_graph import InfoGraph, info_states
from app.engine.input_manager import get_input_manager
from app.engine.objects.unit import UnitObject
from app.engine.sound import get_sound_thread
from app.engine.sprites import SPRITES
from app.engine.state import State
from app.utilities import utils
from app.utilities.enums import HAlignment
import re

class SlidingWindowUnitList():
    l: List[UnitPrefab]

    def __init__(self, l: List[UnitPrefab]) -> None:
        self.l = l

    def get(self, start_idx, end_idx) -> List[UnitPrefab]:
        while end_idx > len(self.l):
            end_idx -= len(self.l)
        if (start_idx < 0 and end_idx >= 0) or start_idx >= end_idx:
            return self.l[start_idx:] + self.l[:end_idx]
        return self.l[start_idx:end_idx]

    def get_window(self, center_idx, buffer) -> Tuple[List[UnitPrefab], List[UnitPrefab]]:
        buffer = min(buffer, len(self.l))
        return self.get(center_idx - buffer, center_idx), self.get(center_idx + 1, center_idx + buffer + 1)

    def index(self, v):
        return self.l.index(v)

    def __getitem__(self, idx: int):
        return self.l[idx]

    def __len__(self):
        return len(self.l)

class Page(StrEnum):
    VITAL = auto()
    ITEMS = auto()
    SKILL = auto()
    UPGRADE = auto()


colortext_pattern = re.compile("<(.*?)>([^<>]*?)<\/>")

class BaseCopyInfoWindow():
    TRANSITION_DURATION = 250
    MINIMIZED_LEFT = WINWIDTH - 96
    EXPANDED_LEFT = WINWIDTH - 192
    DETAIL_LEFT = WINWIDTH - 96

    PAGE_ORDER = [Page.VITAL, Page.ITEMS, Page.SKILL, Page.UPGRADE]

    def __init__(self, is_hidden_func) -> None:
        self.curr_unit_nid = None
        self.left_side = WINWIDTH - 96
        self.transition_time = 0
        self.state = 'inactive'
        self.info_flag = False
        self.page_idx = 0
        self.bg = background.PanoramaBackground(RESOURCES.panoramas.get('info_menu_background')).panorama.images[0]
        self.sprite = None
        self.is_hidden = is_hidden_func
        self.mode = 'Stat'

    def page(self):
        return self.PAGE_ORDER[self.page_idx]

    def set_current_unit(self, unit_nid: NID):
        self.info_graph = InfoGraph()
        self.info_graph.set_current_state(self.page())
        self.curr_unit_nid = unit_nid
        self.sprite = load_map_sprite(DB.units.get(unit_nid))
        self.create_detail_surf.cache_clear()
    
    def get_help_boxes(self, some_desc):
        help_boxes = []
        dupes = []
        for color, word in colortext_pattern.findall(some_desc):
            text = ''
            name = ''
            nid = ''
            if color in ('green', 'brown'):
                lore_entry = [lore for lore in DB.lore if lore.nid not in dupes and (lore.nid == word or lore.name == word or word in lore.aliases.split(','))]
                if lore_entry:
                    text = lore_entry[0].text
                    name = lore_entry[0].title
                    nid = lore_entry[0].nid
            elif color in ('red', 'indigo'):
                item_entry = [item for item in DB.items if item.nid not in dupes and (item.nid == word or item.name == word)]
                if item_entry:
                    dupes.append(item_entry[0].nid)
                    help_boxes.append(help_menu.ItemHelpDialog(item_entry[0], True))
            elif color == 'blue':
                skill_entry = [skill for skill in DB.skills if skill.nid not in dupes and (skill.nid == word or skill.name == word)]
                if skill_entry:
                    text = skill_entry[0].desc
                    name = skill_entry[0].name
                    nid = skill_entry[0].nid
            if nid:
                dupes.append(nid)
                help_boxes.append(help_menu.HelpDialog(text,'<%s>%s</>' % (color, name)))
        return help_boxes

    def take_input(self, event, first_push, directions):
        if self.state == 'active':
            if self.info_flag:
                if 'RIGHT' in directions:
                    get_sound_thread().play_sfx('Select 6')
                    self.info_graph.move_right()
                elif 'LEFT' in directions:
                    get_sound_thread().play_sfx('Select 6')
                    self.info_graph.move_left()
                elif 'UP' in directions:
                    get_sound_thread().play_sfx('Select 6')
                    self.info_graph.move_up()
                elif 'DOWN' in directions:
                    get_sound_thread().play_sfx('Select 6')
                    self.info_graph.move_down()
                if event == 'AUX':
                    get_sound_thread().play_sfx('Select 6')
                    self.info_graph.switch_info()
                elif event == 'INFO' or event == 'BACK':
                    get_sound_thread().play_sfx('Info Out')
                    self.info_graph.set_transition_out()
                    self.info_flag = False
            else:
                if 'RIGHT' in directions:
                    self.scroll_right()
                elif 'LEFT' in directions:
                    self.scroll_left()
                elif 'UP' in directions:
                    # let the upper menu handle it
                    return True
                elif 'DOWN' in directions:
                    # let the upper menu handle it
                    return True
                if event == 'BACK':
                    self.retract()
                if event == 'INFO':
                    if self.info_graph.registry.get(self.page(), None):
                        get_sound_thread().play_sfx('Info In')
                        self.info_graph.set_transition_in()
                        self.info_flag = True
                if event == 'AUX':
                    get_sound_thread().play_sfx('Select 6')
                    self.change_mode()
        return False

    def scroll_right(self):
        self.page_idx = (self.page_idx + 1) % len(self.PAGE_ORDER)
        self.info_graph.set_current_state(self.page())

    def scroll_left(self):
        self.page_idx = (self.page_idx - 1) % len(self.PAGE_ORDER)
        self.info_graph.set_current_state(self.page())
    
    def change_mode(self):
        if self.mode == 'Stat':
            self.mode = 'Growth'
        else:
            self.mode = 'Stat'
        self.create_detail_surf.cache_clear()

    def update(self):
        self.transition_time = max(self.transition_time - frames2ms(1), 0)
        if self.state == 'expand':
            self.left_side = int(interpolation.lerp(self.EXPANDED_LEFT, self.MINIMIZED_LEFT, self.transition_time / TRANSITION_DURATION))
            if self.transition_time == 0:
                self.state = 'active'
        elif self.state == 'retract':
            self.left_side = int(interpolation.lerp(self.MINIMIZED_LEFT, self.EXPANDED_LEFT, self.transition_time / TRANSITION_DURATION))
            if self.transition_time == 0:
                self.state = 'inactive'

    @lru_cache(1)
    def create_portrait_surf(self, unit_nid):
        unit = DB.units.get(unit_nid)
        surf = engine.create_surface((96, WINHEIGHT), transparent=True)
        im, offset = icons.get_portrait(unit)
        hidden = self.is_hidden(unit_nid)
        if im:
            x_pos = (im.get_width() - 80)//2
            portrait_surf = engine.subsurface(im, (x_pos, offset, 80, 72))
            if hidden:
                portrait_surf = image_mods.make_black_colorkey(portrait_surf, 1.0)
            surf.blit(portrait_surf, (8, 8))

        name = ' ???' if hidden else unit.name
        render_text(surf, ['text'], [name], ['white'], (48, 80), HAlignment.CENTER)

        class_obj = DB.classes.get(unit.klass)
        klass = '???' if hidden else class_obj.name
        render_text(surf, ['text'], [klass], ['white'], (5, 104))
        unit_fields = {key: value for (key, value) in unit.fields}
        creator = unit_fields['Creator'] if 'Creator' in unit_fields else '???'
        render_text(surf, ['text'], [creator], ['white'], (5, 120))
        
        if unit_nid in RECORDS.get('Available_Units') or (unit_nid == 'Yasukage' and RECORDS.get('yasukage_unlocked')):
            render_text(surf, ['text'], ['Recruited!'], ['green'], (5, 136))
        else:
            render_text(surf, ['text'], ['Not Recruited'], ['red'], (5, 136))
        # Blit affinity
        if not hidden:
            affinity = DB.affinities.get(unit.affinity)
            if affinity:
                icons.draw_item(surf, affinity, (78, 80))
        return surf

    @lru_cache(16)
    def create_detail_surf(self, unit_nid: NID, page: Page):
        unit_prefab = DB.units.get(unit_nid)
        klass = DB.classes.get(unit_prefab.klass)
        if not self.is_hidden(unit_nid):
            if page == Page.VITAL:
                return self.create_vital_surf(unit_prefab, klass, self.mode)
            elif page == Page.ITEMS:
                return self.create_item_surf(unit_prefab, klass)
            elif page == Page.SKILL:
                return self.create_skill_surf(unit_prefab, klass)
            elif page == Page.UPGRADE:
                return self.create_upgrade_surf(unit_prefab, klass)
        return self.create_unknown_page()

    def create_unknown_page(self):
        menu_size = 96, WINHEIGHT
        surf = engine.create_surface(menu_size, transparent=True)
        render_text(surf, ['text'], ["Identity"], ['red'], (48, WINHEIGHT // 2 - 16), HAlignment.CENTER)
        render_text(surf, ['text'], ["unknown"], ['red'], (48, WINHEIGHT // 2), HAlignment.CENTER)
        return surf

    def create_vital_surf(self, unit: UnitPrefab, klass: Klass, mode='Stat') -> engine.Surface:
        menu_size = 96, WINHEIGHT
        surf = engine.create_surface(menu_size, transparent=True)
        def write(text, color, pos):
            render_text(surf, ['text'], [str(text)], [color], pos)

        base_stats = unit.get_stat_lists()[0]
        base_growths = unit.get_stat_lists()[1]
        def render_stat(stat_nid: NID, pos: Point):
            num_pos = pos[0] + 24, pos[1]
            write(stat_nid, 'blue', pos)
            if mode == 'Stat':
                write(base_stats.get(stat_nid, 0), 'white', num_pos)
            else:
                write(base_growths.get(stat_nid, 0), 'white', num_pos)
        write("Stat Info", "yellow", (5, 5))
        render_stat('HP', (5, 21));  render_stat('LCK', (46, 21))
        render_stat('STR', (5, 37)); render_stat('MAG', (46, 37))
        render_stat('SKL', (5, 53)); render_stat('DEF', (46, 53))
        render_stat('SPD', (5, 69)); render_stat('RES', (46, 69))
        render_stat('CON', (5, 85)); render_stat('MOV', (46, 85))
        
        
        unit_fields = {key: value for (key, value) in unit.fields}
        start_weapons = unit_fields['Base_Weapons'] if 'Base_Weapons' in unit_fields else None
        end_weapons = unit_fields['Upgrade_Weapons'] if 'Upgrade_Weapons' in unit_fields else None
        offset = 5
        count = 0
        if start_weapons or end_weapons:
            #for weapon, wexp in unit.wexp_gain.items():
            for weapon in ['Sword','Lance','Axe','Bow','Knife','Anima','Light','Dark','Staff','Stone']:
                if start_weapons and weapon in start_weapons.split(','):
                    icons.draw_weapon(surf, weapon, (offset, 105 + (16 * (count // 5))))
                elif end_weapons and weapon in end_weapons.split(','):
                    icons.draw_icon_by_alias(surf, 'promoted_' + weapon, (offset, 105 + (16 * (count // 5))))
                else:
                    image = icons.get_icon_by_name(weapon)
                    image = image_mods.make_black_colorkey(image, 0.5)
                    surf.blit(image, (offset, 105 + (16 * (count // 5))))
                
                count += 1
                if count % 5 == 0:
                    offset = 5
                else:
                    offset += 16
        
        return surf

    def create_item_surf(self, unit: UnitPrefab, klass: Klass):
        menu_size = 96, WINHEIGHT
        surf = engine.create_surface(menu_size, transparent=True)
        page = Page.ITEMS
        def write(text, color, pos):
            render_text(surf, ['text'], [str(text)], [color], pos)

        dummy_unit = UnitObject('dummy')
        def add_item(item_nid: NID, pos: Point):
            x, y = pos
            item = item_funcs.create_item(dummy_unit, item_nid, False, None, False)
            icons.draw_item(surf, item, (x + 2, y + 4), cooldown=False)
            help_boxes = [help_menu.ItemHelpDialog(item, True)] + self.get_help_boxes(item.desc)
            self.info_graph.register((self.DETAIL_LEFT + x + 2, y + 4, 16, 16), help_boxes, page)
        write("Base Items", 'yellow', (5, 5))
        write("Upgrade Items", 'yellow', (5, 72))
        count = 0
        for item in unit.get_items():
            x = (count % 4) * 24 + 1
            y = (count // 4) * 24 + 21
            add_item(item, (x, y))
            count += 1
        upgraded_items = self.get_upgrade_items(self.curr_unit_nid)
        for idx, item in enumerate(upgraded_items):
            x = (idx % 4) * 24 + 1
            y = (idx // 4) * 24 + 93
            add_item(item, (x, y))
        return surf
    
    def get_upgrade_items(self, unit_nid):
        upgrade_items = []
        raw_set = [x for x in game.get_data('Character_Upgrades') if x.unit_nid == unit_nid and x.upgrade_type == 'Item']
        for y in raw_set:
            upgrade_items.append(y.value_1)
        return upgrade_items

    def create_skill_surf(self, unit: UnitPrefab, klass: Klass):
        menu_size = 96, WINHEIGHT
        surf = engine.create_surface(menu_size, transparent=True)
        page = Page.SKILL
        def write(text, color, pos):
            render_text(surf, ['text'], [str(text)], [color], pos)

        dummy_unit = UnitObject('dummy')
        def add_skill(skill_nid: NID, pos: Point):
            x, y = pos
            skill = item_funcs.create_skill(dummy_unit, skill_nid)
            icons.draw_skill(surf, skill, (x + 2, y + 4), compact=False)
            help_boxes = [help_menu.HelpDialog(skill.desc, name=skill.name)] + self.get_help_boxes(skill.desc)
            self.info_graph.register((self.DETAIL_LEFT + x + 2, y + 4, 16, 16), help_boxes, page)
        write("Base Skills", 'yellow', (5, 5))
        write("Upgrade Skills", 'yellow', (5, 72))
        count = 0
        for skill in unit.get_skills():
            if 'hidden' not in [c.nid for c in DB.skills.get(skill).components]:
                x = (count % 4) * 24 + 1
                y = (count // 4) * 24 + 21
                add_skill(skill, (x, y))
                count += 1
        upgraded_skills = self.get_upgrade_skills(self.curr_unit_nid)
        count2 = 0
        for skill in upgraded_skills:
            if 'hidden' not in [c.nid for c in DB.skills.get(skill).components]:
                x = (count2 % 4) * 24 + 1
                y = (count2 // 4) * 24 + 93
                add_skill(skill, (x, y))
                count2 += 1
        return surf
    
    def get_upgrade_skills(self, unit_nid):
        upgrade_skills = []
        raw_set = [x for x in game.get_data('Character_Upgrades') if x.unit_nid == unit_nid and x.upgrade_type == 'Skill']
        for y in raw_set:
            upgrade_skills.append(y.value_1)
        return upgrade_skills
    
    def create_upgrade_surf(self, unit: UnitPrefab, klass: Klass):
        menu_size = 96, WINHEIGHT
        surf = engine.create_surface(menu_size, transparent=True)
        page = Page.UPGRADE
        def write(text, color, pos):
            render_text(surf, ['text'], [str(text)], [color], pos)
        def write_narrow(text, color, pos):
            render_text(surf, ['narrow'], [str(text)], [color], pos)
        
        write("Upgrades", "yellow", (5, 5))
        ms_icon = icons.get_icon_by_name('Master_Seal')
        raw_set = [x for x in game.get_data('Character_Upgrades') if x.unit_nid == unit.nid]
        for offset, y in enumerate(raw_set):
            write_narrow(y.upgrade_name, 'white', (5, 21 + (16 * offset)))
            surf.blit(ms_icon, (66, 21 + (16 * offset)))
            if RECORDS.get(y.nid):
                write_narrow('B', 'green', (82, 21 + (16 * offset)))
            else:
                write_narrow('x' + y.cost, 'red', (82, 21 + (16 * offset)))
        
        return surf

    def expand(self):
        if self.state == 'inactive':
            self.transition_time = TRANSITION_DURATION
            self.state = 'expand'

    def retract(self):
        if self.state == 'active':
            self.transition_time = TRANSITION_DURATION
            self.state = 'retract'

    def draw(self, surf):
        surf.blit(self.bg, (self.left_side, 0))
        surf.blit(self.create_portrait_surf(self.curr_unit_nid), (self.left_side, 0))

        # draw the class icon
        surf.blit(SPRITES.get('status_platform'), (self.left_side + 66, 131))
        active_sprite = self.sprite.create_image('active')
        x_pos = 81 - active_sprite.get_width()//2
        y_pos = WINHEIGHT - 61
        surf.blit(active_sprite, (self.left_side + x_pos, y_pos))
        if self.state != 'inactive':
            page_str = str(self.page_idx + 1) + '/' + str(len(self.PAGE_ORDER))
            render_text(surf, ['small'], [page_str], [], (self.left_side + 96 + 84, 4), HAlignment.RIGHT)
            surf.blit(self.create_detail_surf(self.curr_unit_nid, self.page()), (self.left_side + 96, 0))
        if self.info_flag:
            if self.info_graph.current_bb:
                self.info_graph.draw(surf)

UNIT_CHOICE_HEIGHT = 41
UNIT_CHOICE_BONUS_HEIGHT = 25
TRANSITION_DURATION = 125

class BaseCopyInfoMenu(State):
    name = 'base_info_menu'
    in_level = False
    show_map = False

    faded_unit_surf_cache: Dict[NID, engine.Surface] = {}

    def create_background(self):
        panorama = RESOURCES.panoramas.get('default_background')
        if panorama:
            self.bg = background.ScrollingBackground(panorama)
        else:
            self.bg = None

    def start(self):
        self.create_background()

        self.unit_selector_ring = SPRITES.get("unit_selector_glow")
        self.unit_select_bar = SPRITES.get("unit_select_base")
        self.unit_select_glow = SPRITES.get("unit_select_glow")
        self.glow_timer = [utils.clamp(2 * sin(radians(i)), -1, 1) / 2 + 0.5 for i in range(0, 360, 3)]
        self.glow_idx = 0

        if not RECORDS.get('Density_10_Cleared'):
            all_units = [unit.nid for unit in DB.units if 'Playable' in unit.tags and unit.nid != 'Libra_P']
        else:
            all_units = [unit.nid for unit in DB.units if 'Playable' in unit.tags]
        self.all_units = SlidingWindowUnitList(all_units)
        # Unit to be displayed
        self.initial_unit = game.memory.get('curr_unit_info')
        unit_nid = self.initial_unit or all_units[0]
        self.selected_idx = self.all_units.index(unit_nid)

        self.fluid = FluidScroll(200, 1)

        self.logo = None

        self.transition_time = 0
        self.transition_direction = 0

        self.queued_direction: str = None

        self.state = 'unit_select'

        self.detail_panel = BaseCopyInfoWindow(self.is_hidden)
        self.detail_panel.set_current_unit(self.current_unit())

        game.state.change('transition_in')
        return 'repeat'

    def current_unit(self):
        return self.all_units[self.selected_idx]

    def is_hidden(self, unit_nid: NID):
        if unit_nid == self.initial_unit:
            return False
        if RECORDS.get('Available_Units') and unit_nid in RECORDS.get('Available_Units'):
            return False
        if RECORDS.get('Seen_Units') and unit_nid in RECORDS.get('Seen_Units'):
            return False
        if RECORDS.get('yasukage_unlocked') and unit_nid == 'Yasukage':
            return False
        return True

    def back(self):
        get_sound_thread().play_sfx('Select 4')
        # game.memory['base_info_menu_state'] = self.state
        # game.memory['current_unit'] = self.unit
        game.state.change('transition_pop')

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()
        if self.detail_panel.state == 'active':
            if not self.detail_panel.take_input(event, first_push, directions):
                return

        if self.state == 'unit_select':
            if self.queued_direction:
                directions.append(self.queued_direction)
                self.queued_direction = None
            if event == 'SELECT':
                self.detail_panel.expand()
                self.state = 'detail'
            elif event == 'BACK':
                self.back()
            elif 'UP' in directions:
                get_sound_thread().play_sfx('Select 6')
                self.move_up()
            elif 'DOWN' in directions:
                get_sound_thread().play_sfx('Select 6')
                self.move_down()
        # buffering for fluidity
        elif self.state == 'scroll_transition':
            if 'UP' in directions:
                self.queued_direction = 'UP'
            elif 'DOWN' in directions:
                self.queued_direction = 'DOWN'

    def queue_transition(self, direction):
        self.transition_time = TRANSITION_DURATION
        self.transition_direction = direction
        self.state = 'scroll_transition'

    def move_down(self):
        self.selected_idx = (self.selected_idx + 1) % len(self.all_units)
        self.detail_panel.set_current_unit(self.current_unit())
        self.queue_transition(1)

    def move_up(self):
        self.selected_idx = (self.selected_idx - 1) % len(self.all_units)
        self.detail_panel.set_current_unit(self.current_unit())
        self.queue_transition(-1)

    def update(self):
        self.bg.update()
        self.detail_panel.update()
        self.glow_idx = (self.glow_idx + 1) % len(self.glow_timer)
        self.transition_time = max(self.transition_time - frames2ms(1), 0)
        if self.transition_time == 0:
            self.state = 'unit_select'

    def get_faded_unit_choice(self, unit_nid: NID) -> engine.Surface:
        if unit_nid in self.faded_unit_surf_cache:
            return self.faded_unit_surf_cache[unit_nid]
        unit_prefab = DB.units.get(unit_nid)
        hidden = self.is_hidden(unit_nid)
        
        id_num = self.all_units.index(unit_nid) + 1
        option = BasicUnitOption.from_nid(0, unit_nid, display_value=str(id_num) + ': ???' if hidden else str(id_num) + ': ' + unit_prefab.name, text_color='grey' if hidden else 'white')
        surf = engine.create_surface((option.width(), UNIT_CHOICE_HEIGHT), True)

        option.draw_option(surf, 0, UNIT_CHOICE_BONUS_HEIGHT, stationary=True, darkened_icon=hidden)
        self.faded_unit_surf_cache[unit_nid] = surf
        return surf

    @lru_cache(1)
    def draw_passive_unit_wheel(self, selected_idx, unit_list: Tuple[str], rotation: float) -> Tuple[engine.Surface, Point]:
        """Draws the unit options in a gradual arc. Rotation indicates a degree of transition between options.

        Args:
            unit_list (Tuple[str]): list of units, from top to bottom
            rotation (float): whether or not, and how much, we are rotating up or down.

        Returns:
            Tuple[engine.Surface, Point]: the surface of the passive wheel, as well as the coord of the active unit (if we are not in transition)
        """
        size = len(unit_list) # this should be odd lol
        angles = [90 - ((i + rotation) / (size - 1)) * 180 for i in range(size)]

        CENTER = (-8, WINHEIGHT // 2 - 16)
        X_RADIUS = 32
        Y_RADIUS = WINHEIGHT * 0.8
        x_coords = [X_RADIUS * cos(radians(angle)) + CENTER[0] for angle in angles]
        y_coords = [-Y_RADIUS * sin(radians(angle / 2)) + CENTER[1] for angle in angles]

        # adjustment for height of unit option
        y_coords = [y - UNIT_CHOICE_BONUS_HEIGHT - 8 for y in y_coords]

        surf = engine.create_surface((WINWIDTH, WINHEIGHT), True)

        def draw_faded(idx):
            unit_nid = unit_list[idx]
            faded_unit_surf = self.get_faded_unit_choice(unit_nid)
            unit_surf = image_mods.make_black_colorkey(faded_unit_surf, pow((selected_idx - idx)/2, 2) / len(unit_list) + 0.15)
            unit_surf = image_mods.make_translucent(unit_surf, pow((selected_idx - idx)/2, 2) / len(unit_list))
            engine.blit(surf, unit_surf, (x_coords[idx], y_coords[idx]))

        for idx in range(0, selected_idx):
            draw_faded(idx)
        for idx in range(len(unit_list) - 1, selected_idx, -1):
            draw_faded(idx)

        active_point = x_coords[selected_idx], y_coords[selected_idx]
        return surf, active_point

    def draw_active_unit(self, surf, unit_nid, point):
        hidden = self.is_hidden(unit_nid)
        unit_prefab = DB.units.get(unit_nid)
        option = BasicUnitOption.from_nid(0, unit_nid, str(self.selected_idx + 1) +  ": ???" if hidden else str(self.selected_idx + 1) + ': ' + unit_prefab.name)
        x, y = point
        option.draw_option(surf, x, y + UNIT_CHOICE_BONUS_HEIGHT, True, darkened_icon = hidden)

    def draw_selection(self, surf, y):
        glow_surf = image_mods.make_translucent(self.unit_select_glow, self.glow_timer[self.glow_idx])
        engine.blit(surf, self.unit_select_bar, (0, y + 18))
        engine.blit(surf, glow_surf, (0, y + 18))

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        else:
            # info menu shouldn't be transparent
            surf.blit(SPRITES.get('bg_black'), (0, 0))
        engine.blit(surf, self.unit_selector_ring)

        transition_progress = self.transition_time / TRANSITION_DURATION * self.transition_direction

        top_units, bottom_units = self.all_units.get_window(self.selected_idx, 9)
        drawn_units = top_units[-4:] + [self.current_unit()] + bottom_units[:5]
        wheel_surf, active_point = self.draw_passive_unit_wheel(4, tuple(drawn_units), transition_progress)

        self.draw_selection(surf, active_point[1])
        engine.blit(surf, wheel_surf)
        self.draw_active_unit(surf, self.current_unit(), active_point)

        self.detail_panel.draw(surf)
        return surf