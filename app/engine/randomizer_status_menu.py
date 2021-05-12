from app.constants import WINWIDTH, WINHEIGHT

from app.engine import config as cf
from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine.sound import SOUNDTHREAD
from app.engine.input_manager import INPUT
from app.engine.state import State
from app.engine import engine, background, banner, menus, randomizer_menu_options, base_surf, text_funcs
from app.engine.game_state import game
from app.engine.randomizer import Rando
import logging

properties = [('brave', 'weapon_properties', 0, ([], 'Null'), True),
          ('lifelink', 'weapon_properties', 0, ([], 'Null'), True),
          ('reaver', 'weapon_properties', 0, ([], 'Null'), True),
          ('magic', 'weapon_properties', 0, ([], 'Null'), True),
          ('effective', 'weapon_properties', 0, ([], 'Null'), True),
          ('status_on_equip', 'weapon_properties', 0, ([], 'Null'), True),
          ('status_on_hold', 'weapon_properties', 0, ([], 'Null'), True),
          ('status_on_hit', 'weapon_properties', 0, ([], 'Null'), True),
          ]

effective = [('Horse', 'weapon_effective', 0, ([], 'Null'), True),
          ('Armor', 'weapon_effective', 0, ([], 'Null'), True),
          ('Flying', 'weapon_effective', 0, ([], 'Null'), True),
         ]

imbue = [('Strength +5', 'weapon_imbue', 0, ([], 'Null'), True),
          ('Speed +5', 'weapon_imbue', 0, ([], 'Null'), True),
          ('Skill +5', 'weapon_imbue', 0, ([], 'Null'), True),
          ('Luck +5', 'weapon_imbue', 0, ([], 'Null'), True),
          ('Defense +5', 'weapon_imbue', 0, ([], 'Null'), True),
          ('Resistance +5', 'weapon_imbue', 0, ([], 'Null'), True),
        ]

inflict = [('Poisoned', 'weapon_inflict', 0, ([], 'Null'), True),
          ('Silence', 'weapon_inflict', 0, ([], 'Null'), True),
          ('Dazzle', 'weapon_inflict', 0, ([], 'Null'), True),
          ('Chill', 'weapon_inflict', 0, ([], 'Null'), True),
          ('Frostbite', 'weapon_inflict', 0, ([], 'Null'), True),
           ]

config_icons = [engine.subsurface(SPRITES.get('settings_icons'), (0, c[2] * 16, 16, 16)) for c in properties]

class RandoStatusMenuState(State):
    name = 'randomizer_status_menu'
    in_level = False

    def start(self):

        self.bg = background.create_background('settings_background')
        # top_menu_left, top_menu_right, config, controls, get_input
        self.state = 'top_menu_left'

        property_options = [(c[0], c[1]) for c in properties]
        self.properties_menu = randomizer_menu_options.Config(None, property_options, 'menu_bg_base', config_icons)
        self.properties_menu.takes_input = False

        effective_options = [(c[0], c[1]) for c in effective]
        self.effective_menu = randomizer_menu_options.Config(None, effective_options, 'menu_bg_base', config_icons)
        self.effective_menu.takes_input = False

        imbue_options = [(c[0], c[1]) for c in imbue]
        self.imbue_menu = randomizer_menu_options.Config(None, imbue_options, 'menu_bg_base', config_icons)
        self.imbue_menu.takes_input = False

        inflict_options = [(c[0], c[1]) for c in inflict]
        self.inflict_menu = randomizer_menu_options.Config(None, inflict_options, 'menu_bg_base', config_icons)
        self.inflict_menu.takes_input = False

        self.top_cursor = menus.Cursor()
        self.defaultAllChildren()

        game.state.change('transition_in')
        return 'repeat'

    @property
    def current_menu(self):
        if self.state in ('top_menu_left', 'properties'):
            return self.properties_menu
        elif self.state in ('top_menu_midleft', 'effective'):
            return self.effective_menu
        elif self.state in ('top_menu_midright', 'imbue'):
            return self.imbue_menu
        else:
            return self.inflict_menu

    def current_menu_obj(self):
        if self.state in ('top_menu_left', 'properties'):
            return properties
        elif self.state in ('top_menu_midleft', 'effective'):
            return effective
        elif self.state in ('top_menu_midright', 'imbue'):
            return imbue
        else:
            return inflict

    def handle_mouse(self):
        mouse_position = INPUT.get_mouse_position()
        if mouse_position:
            mouse_x, mouse_y = mouse_position
            top_left_rect = (4, 4, 56, 24) #This makes the top categories, may need to adjust for more of them
            mid_left_rect = (64, 4, 56, 24)
            mid_right_rect = (124, 4, 56, 24)
            top_right_rect = (184, 4, 56, 24)
            # Test left rect
            x, y, width, height = top_left_rect
            if x <= mouse_x <= x + width and y <= mouse_y <= y + height:
                self.current_menu.takes_input = False
                self.state = 'top_menu_left'
                return
            # Test midleft rect
            x, y, width, height = mid_left_rect
            if x <= mouse_x <= x + width and y <= mouse_y <= y + height:
                self.current_menu.takes_input = False
                self.state = 'top_menu_midleft'
                return
            # Test midright rect
            x, y, width, height = mid_right_rect
            if x <= mouse_x <= x + width and y <= mouse_y <= y + height:
                self.current_menu.takes_input = False
                self.state = 'top_menu_midright'
                return
            # Test right rect
            x, y, width, height = top_right_rect
            if x <= mouse_x <= x + width and y <= mouse_y <= y + height:
                self.current_menu.takes_input = False
                self.state = 'top_menu_right'
                return
            current_idxs, current_option_rects = self.current_menu.get_rects()
            for idx, option_rect in zip(current_idxs, current_option_rects):
                x, y, width, height = option_rect
                if x <= mouse_x <= x + width and y <= mouse_y <= y + height:
                    if self.state in ('top_menu_left', 'properties'):
                        self.state = 'properties'
                    elif self.state in ('top_menu_midleft', 'effective'):
                        self.state = 'effective'
                    elif self.state in ('top_menu_midright', 'imbue'):
                        self.state = 'imbue'
                    else:
                        self.state = 'inflict'
                    self.current_menu.takes_input = True
                    self.current_menu.move_to(idx)
                    return

    def take_input(self, event):
        if self.state in ('top_menu_left','top_menu_midleft','top_menu_midright','top_menu_right'):
            self.handle_mouse()
            if event == 'DOWN' or event == 'SELECT':
                SOUNDTHREAD.play_sfx('Select 6')
                if self.state == 'top_menu_left':
                    self.state = 'properties'
                elif self.state == 'top_menu_midleft':
                    self.state = 'effective'
                elif self.state == 'top_menu_midright':
                    self.state = 'imbue'
                else:
                    self.state = 'inflict'
                self.current_menu.takes_input = True
            elif event == 'LEFT':
                if self.state == 'top_menu_right':
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.state = 'top_menu_midright'
                elif self.state == 'top_menu_midright':
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.state = 'top_menu_midleft'
                elif self.state == 'top_menu_midleft':
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.state = 'top_menu_left'
            elif event == 'RIGHT':
                if self.state == 'top_menu_left':
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.state = 'top_menu_midleft'
                elif self.state == 'top_menu_midleft':
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.state = 'top_menu_midright'
                elif self.state == 'top_menu_midright':
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.state = 'top_menu_right'
            elif event == 'BACK':
                self.back()

        else:
            self.handle_mouse()
            if event == 'DOWN':
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_down()
            elif event == 'UP':
                SOUNDTHREAD.play_sfx('Select 6')
                if self.current_menu.get_current_index() <= 0:
                    self.current_menu.takes_input = False
                    if self.state == 'properties':
                        self.state = 'top_menu_left'
                    elif self.state == 'effective':
                        self.state = 'top_menu_midleft'
                    elif self.state == 'imbue':
                        self.state = 'top_menu_midright'
                    else:
                        self.state = 'top_menu_right'
                else:
                    self.current_menu.move_up()
            elif event == 'LEFT':
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_left()
            elif event == 'RIGHT':
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_right()

            elif event == 'BACK':
                self.back()

            elif event == 'SELECT':
                if self.state in ['properties','effective','imbue','inflict']:
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.current_menu.move_next()

    def back(self):
        SOUNDTHREAD.play_sfx('Select 4')
        game.state.change('transition_pop')

    def update(self):
        self.current_menu.update()
        self.top_cursor.update()

    def draw_top_menu(self, surf):  #Also this for top menus
        bg = base_surf.create_base_surf(56, 24, 'menu_bg_clear')
        surf.blit(bg, (2, 4))
        surf.blit(bg, (62, 4))
        surf.blit(bg, (122, 4))
        surf.blit(bg, (182, 4))
        if self.current_menu is self.properties_menu:
            FONT['text-yellow'].blit_center('Properties', surf, (2 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Effective', surf, (62 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Hold/Equip', surf, (122 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Inflict', surf, (182 + 56 // 2, 8))
            if self.state in ('top_menu_left','top_menu_midleft','top_menu_midright','top_menu_right'):
                self.top_cursor.draw(surf, 2 + 56 // 2 - 16, 8)
        elif self.current_menu is self.effective_menu:
            FONT['text-grey'].blit_center('Properties', surf, (2 + 56 // 2, 8))
            FONT['text-yellow'].blit_center('Effective', surf, (62 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Hold/Equip', surf, (122 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Inflict', surf, (182 + 56 // 2, 8))
            if self.state in ('top_menu_left','top_menu_midleft','top_menu_midright','top_menu_right'):
                self.top_cursor.draw(surf, 62 + 56 // 2 - 16, 8)
        elif self.current_menu is self.imbue_menu:
            FONT['text-grey'].blit_center('Properties', surf, (2 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Effective', surf, (62 + 56 // 2, 8))
            FONT['text-yellow'].blit_center('Hold/Equip', surf, (122 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Inflict', surf, (182 + 56 // 2, 8))
            if self.state in ('top_menu_left','top_menu_midleft','top_menu_midright','top_menu_right'):
                self.top_cursor.draw(surf, 122 + 56 // 2 - 16, 8)
        else:
            FONT['text-grey'].blit_center('Properties', surf, (2 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Effective', surf, (62 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Hold/Equip', surf, (122 + 56 // 2, 8))
            FONT['text-yellow'].blit_center('Inflict', surf, (182 + 56 // 2, 8))
            if self.state in ('top_menu_left', 'top_menu_midleft', 'top_menu_midright', 'top_menu_right'):
                self.top_cursor.draw(surf, 182 + 56 // 2 - 16, 8)

    def draw_info_banner(self, surf):
        height = 16
        bg = base_surf.create_base_surf(WINWIDTH + 16, height, 'menu_bg_clear')
        surf.blit(bg, (-8, WINHEIGHT - height))
        if self.state == 'top_menu_left':
            text = 'config_desc'
        elif self.state == 'top_menu_midleft':
            text = 'config_desc'
        elif self.state == 'top_menu_midright':
            text = 'config_desc'
        elif self.state == 'top_menu_right':
            text = 'config_desc'
        elif self.state == 'properties':
            idx = self.properties_menu.get_current_index()
            text = properties[idx][0] + '_desc'
        elif self.state == 'effective':
            idx = self.effective_menu.get_current_index()
            text = effective[idx][0] + '_desc'
        elif self.state == 'imbue':
            idx = self.imbue_menu.get_current_index()
            text = imbue[idx][0] + '_desc'
        elif self.state == 'inflict':
            idx = self.inflict_menu.get_current_index()
            text = inflict[idx][0] + '_desc'
        else:
            text = 'keymap_desc'
        text = text_funcs.translate(text)
        FONT['text-white'].blit_center(text, surf, (WINWIDTH // 2, WINHEIGHT - height))

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)

        self.draw_top_menu(surf)
        if self.state == 'get_input':
            self.current_menu.draw(surf, True)
        else:
            self.current_menu.draw(surf)
        self.draw_info_banner(surf)

        return surf

    def defaultAllChildren(self):
        menus = [self.properties_menu, self.effective_menu, self.imbue_menu, self.inflict_menu]
        menuObjs = [properties, effective, imbue, inflict]
        for index, menu in enumerate(menus):
            menuObj = menuObjs[index]
            for option in menu.options:
                if menuObj[option.idx][4]:
                    option.available = True
                else:
                    option.available = False

    def finish(self):
        # Just to make sure!
        #INPUT.set_change_keymap(False)
        pass
