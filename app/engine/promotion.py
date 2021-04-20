from app.constants import WINWIDTH, WINHEIGHT

from app.data.database import DB
from app.resources.resources import RESOURCES
from app.utilities import utils

from app.engine.fonts import FONT
from app.engine.sprites import SPRITES
from app.engine.sound import SOUNDTHREAD
from app.engine.state import State
from app.engine import background, menus, engine, dialog, text_funcs, icons, action, item_system
from app.engine.game_state import game
from app.engine.fluid_scroll import FluidScroll

class PromotionChoiceState(State):
    name = 'promotion_choice'
    bg = None

    def __init__(self, name=None):
        self.name = name
        self.bg = background.create_background('settings_background')

    def _get_choices(self):
        if game.rando_settings['promo_rando']:
            promo_dict = game.rando_settings['klassDictionary']
            self.class_options = promo_dict[self.unit_klass.nid].turns_into
        else:
            self.class_options = self.unit_klass.turns_into
        return [DB.classes.get(c).name for c in self.class_options]

    def _proceed(self, next_class):
        game.memory['current_unit'] = self.unit
        game.memory['next_class'] = next_class
        game.state.change('promotion')
        game.state.change('transition_out')

    def start(self):
        self.fluid = FluidScroll()

        self.can_go_back = game.memory.get('can_go_back', False)
        game.memory['can_go_back'] = None
        self.combat_item = game.memory.get('combat_item')
        game.memory['combat_item'] = None

        self.unit = game.memory['current_unit']
        self.unit_klass = DB.classes.get(self.unit.klass)
        display_options = self._get_choices()

        self.menu = menus.Choice(self.unit, display_options, (14, 13))
        self.child_menu = None

        self.weapon_icons = []
        for option in self.class_options:
            weapons = []
            klass = DB.classes.get(option)
            for weapon_nid, weapon in klass.wexp_gain.items():
                if weapon.usable:
                    weapons.append(weapon_nid)
            self.weapon_icons.append(weapons)

        # Platforms
        if game.tilemap and self.unit.position:
            terrain = game.tilemap.get_terrain(self.unit.position)
            platform_type = DB.terrain.get(terrain).platform
        else:
            platform_type = 'Floor'
        platform = RESOURCES.platforms[platform_type + '-Melee']
        self.left_platform = engine.image_load(platform)
        self.right_platform = engine.flip_horiz(self.left_platform.copy())

        # For anim swoop in
        self.anim_offset = 120
        self.target_anim_offset = False

        self.current_desc = self._get_desc()

        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            if self.child_menu:
                self.child_menu.move_down(first_push)
            else:
                self.menu.move_down(first_push)
                self.target_anim_offset = True
                self.current_desc = self._get_desc()
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            if self.child_menu:
                self.menu.move_up(first_push)
            else:
                self.menu.move_up(first_push)
                self.target_anim_offset = True
                self.current_desc = self._get_desc()

        elif event == 'BACK':
            if self.child_menu:
                SOUNDTHREAD.play_sfx('Select 4')
                self.child_menu = None
            elif self.can_go_back:
                SOUNDTHREAD.play_sfx('Select 4')
                game.state.back()
                if self.combat_item:
                    action.do(action.Reset(self.unit))
                    item_system.reverse_use(self.unit, self.combat_item)
            else:
                # Can't go back...
                SOUNDTHREAD.play_sfx('Error')

        elif event == 'SELECT':
            if self.child_menu:
                selection = self.child_menu.get_current()
                if selection == 'Change':
                    SOUNDTHREAD.play_sfx('Select 1')
                    self._proceed(self.class_options[self.menu.get_current_index()])
                else:
                    SOUNDTHREAD.play_sfx('Select 4')
                    self.child_menu = None
            else:
                SOUNDTHREAD.play_sfx('Select 1')
                selection = self.menu.get_current()
                options = ['Change', 'Cancel']
                self.child_menu = menus.Choice(selection, options, self.menu)

    def _get_desc(self):
        current_klass = self.class_options[self.menu.get_current_index()]
        desc = DB.classes.get(current_klass).desc
        d = dialog.Dialog(text_funcs.translate(desc))
        d.position = (6, 112)
        d.text_width = WINWIDTH - 28
        d.width = d.text_width + 16
        d.font_type = 'convo'
        d.font_color = 'white'
        d.font = FONT['convo-white']
        d.draw_cursor_flag = False
        return d

    def update(self):
        self.menu.update()
        if self.child_menu:
            self.child_menu.update()
        if self.current_desc:
            self.current_desc.update()

        if self.target_anim_offset:
            self.anim_offset += 8
            if self.anim_offset >= 120:
                self.target_anim_offset = False
                self.anim_offset = 120
        elif self.anim_offset > 0:
            self.anim_offset -= 8
            if self.anim_offset < 0:
                self.anim_offset = 0

    def draw(self, surf):
        if not self.started:
            return surf

        self.bg.draw(surf)

        top = 88
        surf.blit(self.left_platform, (WINWIDTH//2 - self.left_platform.get_width() + self.anim_offset + 52, top))
        surf.blit(self.right_platform, (WINWIDTH//2 + self.anim_offset + 52, top))

        # Class Reel
        FONT['class-purple'].blit(self.menu.get_current(), surf, (114, 5))

        # Weapon Icons
        for idx, weapon in enumerate(self.weapon_icons[self.menu.get_current_index()]):
            icons.draw_weapon(surf, weapon, (130 + 16 * idx, 32))

        if self.menu:
            self.menu.draw(surf)
        if self.child_menu:
            self.child_menu.draw(surf)

        surf.blit(SPRITES.get('promotion_description'), (6, 112))
        if self.current_desc:
            self.current_desc.draw(surf)

        return surf

class ClassChangeChoiceState(PromotionChoiceState):
    name = 'class_change_choice'

    def _get_choices(self):
        if not self.unit.generic:
            unit_prefab = DB.units.get(self.unit.nid)
            self.class_options = [c for c in unit_prefab.alternate_classes if c != self.unit.klass]
        else:  # Just every class, lol?
            self.class_options = [c.nid for c in DB.classes.values() if c.nid != self.unit.klass]
        return [DB.classes.get(c).name for c in self.class_options]

    def _proceed(self, next_class):
        game.memory['current_unit'] = self.unit
        game.memory['next_class'] = next_class
        game.state.change('class_change')
        game.state.change('transition_out')

class PromotionState(State):
    name = 'promotion'
    bg = None

    def _finalize(self, current_time):
        self.current_state = 'level_up'
        self.last_update = current_time
        game.exp_instance.append((self.unit, 0, self, 'promote'))
        game.state.change('exp')

    def start(self):
        img = RESOURCES.panoramas.get('promotion_background')
        if img:
            self.bg = background.SpriteBackground(img, fade=False)
        else:
            self.bg = background.create_background('default_background')

        music = 'music_%s' % self.name 
        if DB.constants.value(music):
            SOUNDTHREAD.fade_in(DB.constants.value(music), fade_in=50)

        self.unit = game.memory['current_unit']
        color = utils.get_team_color(self.unit.team)

        # Old Right Animation
        self.right_anim = None
        # New Left Animation
        self.left_anim = None

        self.current_anim = self.right_anim

        platform_type = 'Floor'
        platform = RESOURCES.platforms[platform_type + '-Melee']
        self.left_platform = engine.image_load(platform)
        self.right_platform = engine.flip_horiz(self.left_platform.copy())
        
        # Name tag
        self.name_tag = SPRITES.get('combat_name_right_' + color).copy()
        width = FONT['text-brown'].width(self.unit.name)
        FONT['text-brown'].blit(self.unit.name, self.name_tag, (36 - width // 2, 8))

        # For darken backgrounds and drawing
        self.darken_background = 0
        self.target_dark = 0
        self.darken_ui_background = 0
        self.combat_surf = engine.create_surface((WINWIDTH, WINHEIGHT), transparent=True)
        self.current_state = 'init'

        if not self.right_anim or not self.left_anim:
            self._finalize(engine.get_time())
        else:
            game.state.change('transition_in')
            return 'repeat'

    def begin(self):
        self.last_update = engine.get_time()

    def darken_ui(self):
        self.darken_ui_background = 1

    def lighten_ui(self):
        self.darken_ui_background = -3

    def update(self):
        current_time = engine.get_time()

        if self.current_state == 'level_up':
            self.last_update = current_time
            self.current_state = 'leave'

        elif self.current_state == 'leave':
            if current_time - self.last_update > 166:  # 10 frames
                game.state.change('transition_double_pop')
                self.state = 'done'
                return 'repeat'

        if self.current_anim:
            self.current_anim.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        else:
            return surf

        combat_surf = engine.copy_surface(self.combat_surf)

        # Platforms
        top = 88
        combat_surf.blit(self.left_platform, (WINWIDTH//2 - self.left_platform.get_width(), top))
        combat_surf.blit(self.right_platform, (WINWIDTH//2, top))

        # Name Tag
        combat_surf.blit(self.name_tag, (WINWIDTH + 3 - self.name_tag.get_width(), 0))

        if self.darken_ui_background:
            self.darken_ui_background = min(self.darken_ui_background, 4)
            color = 255 - abs(self.darken_ui_background * 24)
            engine.fill(combat_surf, (color, color, color), None, engine.BLEND_RGB_MULT)
            self.darken_ui_background += 1

        surf.blit(combat_surf, (0, 0))

        if self.current_anim:
            self.current_anim.draw(surf, (0, 0))

        return surf

class ClassChangeState(PromotionState):
    name = 'class_change'

    def _finalize(self, current_time):
        self.current_state = 'level_up'
        self.last_update = current_time
        game.exp_instance.append((self.unit, 0, self, 'class_change'))
        game.state.change('exp')
