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

unit = [  ('player_bases', bool, 0, ([], 'Null'), True),
          ('boss_bases', bool, 0, ([], 'Null'), True),
          ('bases_mode', ['Redistribute','Delta'], 0, (['player_bases', 'boss_bases'], 'Any'), False),
          ('bases_variance', list(range(0,16)), 0, (['player_bases', 'boss_bases'], 'Any'), False),
          ('use_klass_move', bool, 0, (['player_bases', 'boss_bases'], 'Any'), False),
          ('named_growths', bool, 0, ([], 'Null'), True),
          ('growths_mode', ['Redistribute','Delta','Absolute'], 0, (['named_growths'], 'All'), False),
          ('growths_variance', list(range(0,201,5)), 0, (['named_growths'], 'All'), False),
          ('growths_min', list(range(0,101,5)), 0, (['named_growths'], 'All'), False),
          ('growths_max', list(range(5,201,5)), 0, (['named_growths'], 'All'), False),
          ('name_rando', bool, 0, ([], 'Null'), True),
          ('portrait_rando', bool, 0, ([], 'Null'), True),
          ('desc_rando', bool, 0, ([], 'Null'), True),
          ('personal_skill_rando', bool, 0, ([], 'Null'), True),
          ('personal_skill_mode', ['Match','Random','Static'], 0, (['personal_skill_rando'], 'All'), False),
          ('personal_skill_limit', list(range(0,3)), 0, (['personal_skill_rando'], 'All'), False),
          ('personal_skill_stop_redundancy', bool, 0, (['personal_skill_rando'], 'All'), False),
          ]

klass = [('player_class_rando', bool, 0, ([], 'Null'), True),
          ('player_class_stop_redundancy', bool, 0, ([], 'Null'), True),
          ('boss_rando', bool, 0, ([], 'Null'), True),
          ('generic_rando', bool, 0, ([], 'Null'), True),
          ('wexp_mode', ['Similar','Redistribute','Absolute'], 0, (['player_class_rando', 'boss_rando'], 'Any'), False),
          ('keepWeps', bool, 0, (['player_class_rando', 'boss_rando', 'generic_rando'], 'Any'), False),
          ('weps_mode', ['Match', 'Random'], 0, (['player_class_rando', 'boss_rando', 'generic_rando'], 'Any'), False),
          ('promo_rando', bool, 0, ([], 'Null'), True),
          ('promo_rando_stop_redundancy', bool, 0, ([], 'Null'), True),
          ('promotion_mode',['Match','Random'], 0, (['promo_rando'], 'All'), False),
          ('promotion_amount',list(range(1,4)), 0, (['promo_rando'], 'All'), False),
          ('class_skill_rando', bool, 0, ([], 'Null'), True),
          ('class_skill_mode', ['Match','Random','Static'], 0, (['class_skill_rando'], 'All'), False),
          ('class_skill_limit', list(range(0,4)), 0, (['class_skill_rando'], 'All'), False),
          ('class_skill_stop_redundancy', bool, 0, (['class_skill_rando'], 'All'), False),
          ('class_skill_match_levels', bool, 0, (['class_skill_rando'], 'All'), False),
         ]

item = [['item_stats', bool, 0, ([], 'Null'), True],
          ('wepMt', bool, 0, (['item_rando'], 'All'), False),
          ('wepMtVar', list(range(0,21)), 0, (['item_stats', 'wepMt'], 'All'), False),
          ('wepMtMin', list(range(1,21)), 0, (['item_stats', 'wepMt'], 'All'), False),
          ('wepMtMax', list(range(2,41)), 0, (['item_stats', 'wepMt'], 'All'), False),
          ('wepHit', bool, 0, (['item_rando'], 'All'), False),
          ('wepHitVar', list(range(0,101,5)), 0, (['item_stats', 'wepHit'], 'All'), False),
          ('wepHitMin', list(range(5,101,5)), 0, (['item_stats', 'wepHit'], 'All'), False),
          ('wepHitMax', list(range(10,201,5)), 0, (['item_stats', 'wepHit'], 'All'), False),
          ('wepCrit', bool, 0, (['item_rando'], 'All'), False),
          ('wepCritVar', list(range(0,51)), 0, (['item_stats', 'wepCrit'], 'All'), False),
          ('wepCritMin', list(range(0,21)), 0, (['item_stats', 'wepCrit'], 'All'), False),
          ('wepCritMax', list(range(20,101)), 0, (['item_stats', 'wepCrit'], 'All'), False),
          ('wepWeight', bool, 0, (['item_rando'], 'All'), False),
          ('wepWeightVar', list(range(0,21)), 0, (['item_stats', 'wepWeight'], 'All'), False),
          ('wepWeightMin', list(range(1,11)), 0, (['item_stats', 'wepWeight'], 'All'), False),
          ('wepWeightMax', list(range(10,21)), 0, (['item_stats', 'wepWeight'], 'All'), False),
          ('wepUses', bool, 0, (['item_rando'], 'All'), False),
          ('wepUsesVar', list(range(0,61)), 0, (['item_stats', 'wepUses'], 'All'), False),
          ('wepUsesMin', list(range(1,11)), 0, (['item_stats', 'wepUses'], 'All'), False),
          ('wepUsesMax', list(range(10,61)), 0, (['item_stats', 'wepUses'], 'All'), False),
          ('wepCUses', bool, 0, (['item_rando'], 'All'), False),
          ('wepCUsesVar', list(range(0,11)), 0, (['item_stats', 'wepCUses'], 'All'), False),
          ('wepCUsesMin', list(range(1,6)), 0, (['item_stats', 'wepCUses'], 'All'), False),
          ('wepCUsesMax', list(range(5,11)), 0, (['item_stats', 'wepCUses'], 'All'), False),
          ('random_effects', bool, 0, ([], 'Null'), True),
          ('safe_basic_weapons', bool, 0, (['random_effects'], 'All'), False),
          ('random_effects_mode', ['Add','Replace'], 0, (['random_effects'], 'All'), False),
          ('random_effects_limit', list(range(0,3)), 0, (['random_effects'], 'All'), False),
          ('random_effects_settings', 'weapon_settings', 0, (['random_effects'], 'All'), False),
        ]

other = [('swap_offense', bool, 0, ([], 'Null'), True),
         ('lord_rando', bool, 0, ([], 'Null'), True),
         ('thief_rando', bool, 0, ([], 'Null'), True),
         ('special_rando', bool, 0, ([], 'Null'), True),
         ('finished', 'finish', 0, ([], 'Null'), True)
         ]

config_icons = [engine.subsurface(SPRITES.get('settings_icons'), (0, c[2] * 16, 16, 16)) for c in item]

class RandoMenuState(State):
    name = 'randomizer_menu'
    in_level = False

    def start(self):

        self.bg = background.create_background('settings_background')
        # top_menu_left, top_menu_right, config, controls, get_input
        self.state = 'top_menu_left'

        unit_options = [(c[0], c[1]) for c in unit]
        unit_parents = [(c[0], c[3]) for c in unit]
        self.unit_menu = randomizer_menu_options.Config(None, unit_options, 'menu_bg_base', config_icons)
        self.unit_menu.takes_input = False

        class_options = [(c[0], c[1]) for c in klass]
        self.class_menu = randomizer_menu_options.Config(None, class_options, 'menu_bg_base', config_icons)
        self.class_menu.takes_input = False

        item_options = [(c[0], c[1]) for c in item]
        self.item_menu = randomizer_menu_options.Config(None, item_options, 'menu_bg_base', config_icons)
        self.item_menu.takes_input = False

        other_options = [(c[0], c[1]) for c in other]
        self.other_menu = randomizer_menu_options.Config(None, other_options, 'menu_bg_base', config_icons)
        self.other_menu.takes_input = False

        self.top_cursor = menus.Cursor()
        self.defaultAllChildren()

        game.state.change('transition_in')
        return 'repeat'

    @property
    def current_menu(self):
        if self.state in ('top_menu_left', 'unit'):
            return self.unit_menu
        elif self.state in ('top_menu_midleft', 'class'):
            return self.class_menu
        elif self.state in ('top_menu_midright', 'item'):
            return self.item_menu
        else:
            return self.other_menu

    def current_menu_obj(self):
        if self.state in ('top_menu_left', 'unit'):
            return unit
        elif self.state in ('top_menu_midleft', 'class'):
            return klass
        elif self.state in ('top_menu_midright', 'item'):
            return item
        else:
            return other

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
                    if self.state in ('top_menu_left', 'unit'):
                        self.state = 'unit'
                    elif self.state in ('top_menu_midleft', 'class'):
                        self.state = 'class'
                    elif self.state in ('top_menu_midright', 'item'):
                        self.state = 'item'
                    else:
                        self.state = 'other'
                    self.current_menu.takes_input = True
                    self.current_menu.move_to(idx)
                    return

    def take_input(self, event):
        if self.state in ('top_menu_left','top_menu_midleft','top_menu_midright','top_menu_right'):
            self.handle_mouse()
            if event == 'DOWN' or event == 'SELECT':
                SOUNDTHREAD.play_sfx('Select 6')
                if self.state == 'top_menu_left':
                    self.state = 'unit'
                elif self.state == 'top_menu_midleft':
                    self.state = 'class'
                elif self.state == 'top_menu_midright':
                    self.state = 'item'
                else:
                    self.state = 'other'
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
                    if self.state == 'unit':
                        self.state = 'top_menu_left'
                    elif self.state == 'class':
                        self.state = 'top_menu_midleft'
                    elif self.state == 'item':
                        self.state = 'top_menu_midright'
                    else:
                        self.state = 'top_menu_right'
                else:
                    self.current_menu.move_up()
            elif event == 'LEFT':
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_left()
                menuObj = self.current_menu_obj()
                idx = self.current_menu.get_current_index()
                updates = (menuObj[idx][4], menuObj[idx][3])
                self.updateChildren()
            elif event == 'RIGHT':
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_right()
                menuObj = self.current_menu_obj()
                idx = self.current_menu.get_current_index()
                updates = (menuObj[idx][4], menuObj[idx][3])
                self.updateChildren()

            elif event == 'BACK':
                self.back()

            elif event == 'SELECT':
                if self.state in ['unit','other','class','item']:
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.current_menu.move_next()
                    menuObj = self.current_menu_obj()
                    idx = self.current_menu.get_current_index()
                    updates = (menuObj[idx][4], menuObj[idx][3])
                    self.updateChildren()

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
        if self.current_menu is self.unit_menu:
            FONT['text-yellow'].blit_center('Unit', surf, (2 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Class', surf, (62 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Item', surf, (122 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Other', surf, (182 + 56 // 2, 8))
            if self.state in ('top_menu_left','top_menu_midleft','top_menu_midright','top_menu_right'):
                self.top_cursor.draw(surf, 2 + 56 // 2 - 16, 8)
        elif self.current_menu is self.class_menu:
            FONT['text-grey'].blit_center('Unit', surf, (2 + 56 // 2, 8))
            FONT['text-yellow'].blit_center('Class', surf, (62 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Item', surf, (122 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Other', surf, (182 + 56 // 2, 8))
            if self.state in ('top_menu_left','top_menu_midleft','top_menu_midright','top_menu_right'):
                self.top_cursor.draw(surf, 62 + 56 // 2 - 16, 8)
        elif self.current_menu is self.item_menu:
            FONT['text-grey'].blit_center('Unit', surf, (2 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Class', surf, (62 + 56 // 2, 8))
            FONT['text-yellow'].blit_center('Item', surf, (122 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Other', surf, (182 + 56 // 2, 8))
            if self.state in ('top_menu_left','top_menu_midleft','top_menu_midright','top_menu_right'):
                self.top_cursor.draw(surf, 122 + 56 // 2 - 16, 8)
        else:
            FONT['text-grey'].blit_center('Unit', surf, (2 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Class', surf, (62 + 56 // 2, 8))
            FONT['text-grey'].blit_center('Item', surf, (122 + 56 // 2, 8))
            FONT['text-yellow'].blit_center('Other', surf, (182 + 56 // 2, 8))
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
        elif self.state == 'unit':
            idx = self.unit_menu.get_current_index()
            text = unit[idx][0] + '_desc'
        elif self.state == 'class':
            idx = self.class_menu.get_current_index()
            text = klass[idx][0] + '_desc'
        elif self.state == 'item':
            idx = self.item_menu.get_current_index()
            text = item[idx][0] + '_desc'
        elif self.state == 'other':
            idx = self.other_menu.get_current_index()
            text = other[idx][0] + '_desc'
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

    def updateChildrenOld(self, parents):
        #Parents is a tuple of the child name, list of parents
        menu = self.current_menu
        children_on = 0
        childList, parentList = parents[0], parents[1]
        for option in menu.options:
            if option.name in parentList and Rando.rando_settings[option.name]:
                children_on += 1
        if children_on > 0:
            for option in menu.options:
                if option.name in childList:
                    option.available = True
        else:
            for option in menu.options:
                if option.name in childList:
                    option.available = False

    def updateChildren(self):
        menu = self.current_menu
        menuObj = self.current_menu_obj()
        for idx, option in enumerate(menu.options):
            parents, mode = menuObj[idx][3]
            self_on = True
            if mode == 'All':
                if not all(Rando.rando_settings[choice] for choice in parents):
                    self_on = False
            elif mode == 'Any':
                if not any(Rando.rando_settings[choice] for choice in parents):
                    self_on = False

            if self_on:
                option.available = True
            else:
                option.available = False

    def defaultAllChildren(self):
        menus = [self.unit_menu, self.class_menu, self.item_menu, self.other_menu]
        menuObjs = [unit, klass, item, other]
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
