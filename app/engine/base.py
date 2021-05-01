from app.constants import WINWIDTH, WINHEIGHT

from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.sound import SOUNDTHREAD
from app.engine.fonts import FONT
from app.engine.input_manager import INPUT
from app.engine.state import State

from app.engine.game_state import game
from app.engine import menus, base_surf, background, text_funcs, \
    image_mods, gui, icons, prep, record_book
from app.engine.fluid_scroll import FluidScroll
import app.engine.config as cf

class BaseMainState(State):
    name = 'base_main'

    def __init__(self, name=None):
        super().__init__(name)
        self.fluid = FluidScroll()

    def start(self):
        base_music = game.game_vars.get('_base_music')
        if base_music:
            SOUNDTHREAD.fade_in(base_music)
        game.cursor.hide()
        game.cursor.autocursor()
        game.boundary.hide()
        # build background
        bg_name = game.game_vars.get('_base_bg_name')
        panorama = None
        if bg_name:
            panorama = RESOURCES.panoramas.get(bg_name)
        if panorama:
            panorama = RESOURCES.panoramas.get(bg_name)
            self.bg = background.PanoramaBackground(panorama)
        else:
            panorama = RESOURCES.panoramas.get('default_background')
            self.bg = background.ScrollingBackground(panorama)
            self.bg.scroll_speed = 50
        game.memory['base_bg'] = self.bg

        options = ['Manage', 'Convos', 'Codex', 'Options', 'Save', 'Continue']
        ignore = [False, True, False, False, False, False]
        if game.base_convos:
            ignore[1] = False
        # TODO: Supports
        if game.game_vars.get('_base_market'):
            options.insert(1, 'Market')
            if game.market_items:
                ignore.insert(1, False)
            else:
                ignore.insert(1, True)
        if cf.SETTINGS['debug']:
            options.insert(0, 'Debug')
            ignore.insert(0, False)
        
        topleft = 4, WINHEIGHT//2 - (len(options) * 16 + 8)//2
        self.menu = menus.Choice(None, options, topleft=topleft)
        self.menu.set_ignore(ignore)

        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        elif event == 'SELECT':
            SOUNDTHREAD.play_sfx('Select 1')
            selection = self.menu.get_current()
            if selection == 'Debug':
                game.state.change('debug')
            elif selection == 'Manage':
                game.memory['next_state'] = 'base_manage'
                game.state.change('transition_to')
            elif selection == 'Market':
                game.memory['next_state'] = 'base_market_select'
                game.state.change('transition_to')
            elif selection == 'Convos':
                game.memory['option_owner'] = selection
                game.memory['option_menu'] = self.menu
                game.state.change('base_convos_child')
            elif selection == 'Codex':
                game.memory['option_owner'] = selection
                game.memory['option_menu'] = self.menu
                game.state.change('base_codex_child')
            elif selection == 'Options':
                game.memory['next_state'] = 'settings_menu'
                game.state.change('transition_to')
            elif selection == 'Save':
                game.memory['save_kind'] = 'base'
                game.memory['next_state'] = 'in_chapter_save'
                game.state.change('transition_to')
            elif selection == 'Continue':
                game.state.change('transition_pop')

    def update(self):
        super().update()
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        surf = super().draw(surf)
        if self.bg:
            self.bg.draw(surf)
        if self.menu:
            self.menu.draw(surf)
        return surf

class BaseMarketSelectState(prep.PrepManageState):
    name = 'base_market_select'

    def create_quick_disp(self):
        sprite = SPRITES.get('buttons')
        buttons = [sprite.subsurface(0, 66, 14, 13)]
        font = FONT['text-white']
        commands = ['Market']
        commands = [text_funcs.translate(c) for c in commands]
        size = (49 + max(font.width(c) for c in commands), 24)
        bg_surf = base_surf.create_base_surf(size[0], size[1], 'menu_bg_brown')
        bg_surf = image_mods.make_translucent(bg_surf, 0.1)
        bg_surf.blit(buttons[0], (12 - buttons[0].get_width()//2, 18 - buttons[0].get_height()))
        for idx, command in enumerate(commands):
            font.blit(command, bg_surf, (30, idx * 16 + 3))
        return bg_surf

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'LEFT' in directions:
            if self.menu.move_left(first_push):
                SOUNDTHREAD.play_sfx('Select 5')
        elif 'RIGHT' in directions:
            if self.menu.move_right(first_push):
                SOUNDTHREAD.play_sfx('Select 5')

        if event == 'SELECT':
            unit = self.menu.get_current()
            game.memory['current_unit'] = unit
            game.memory['next_state'] = 'prep_market'
            game.state.change('transition_to')
            SOUNDTHREAD.play_sfx('Select 1')
        elif event == 'BACK':
            game.state.change('transition_pop')
            SOUNDTHREAD.play_sfx('Select 4')
        elif event == 'INFO':
            SOUNDTHREAD.play_sfx('Select 1')
            game.memory['scroll_units'] = game.get_units_in_party()
            game.memory['next_state'] = 'info_menu'
            game.memory['current_unit'] = self.menu.get_current()
            game.state.change('transition_to')

class BaseConvosChildState(State):
    name = 'base_convos_child'
    transparent = True

    def start(self):
        self.fluid = FluidScroll()
        self.options = [event_nid for event_nid in game.base_convos.keys()]
        ignore = [game.base_convos[event_nid] for event_nid in self.options]

        selection = game.memory['option_owner']
        topleft = game.memory['option_menu']

        self.menu = menus.Choice(selection, self.options, topleft)
        # color = ['text-grey' if i else 'text-white' for i in ignore]
        # self.menu.set_color(color)
        self.menu.set_ignore(ignore)

    def begin(self):
        ignore = [game.base_convos[event_nid] for event_nid in self.options]
        # color = ['text-grey' if i else 'text-white' for i in ignore]
        # self.menu.set_color(color)
        self.menu.set_ignore(ignore)
        base_music = game.game_vars.get('_base_music')
        if base_music:
            SOUNDTHREAD.fade_in(base_music)

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.back()

        elif event == 'SELECT':
            selection = self.menu.get_current()
            if not game.base_convos[selection]:
                SOUNDTHREAD.play_sfx('Select 1')
                # Auto-ignore
                game.base_convos[selection] = True
                game.events.trigger('on_base_convo', selection)

    def update(self):
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        if self.menu:
            self.menu.draw(surf)
        return surf

class BaseCodexChildState(State):
    name = 'base_codex_child'
    transparent = True
    
    def start(self):
        self.fluid = FluidScroll()

        options = []
        unlocked_lore = [lore for lore in DB.lore if lore.nid in game.unlocked_lore]
        if unlocked_lore:
            options.append('Library')
        if game.game_vars['_world_map_in_base']:
            options.append('Map')
        options.append('Records')
        # TODO Achievements?
        # TODO Tactics?
        unlocked_guide = [lore for lore in unlocked_lore if lore.category == 'Guide']
        if unlocked_guide:
            options.append('Guide')

        selection = game.memory['option_owner']
        topleft = game.memory['option_menu']

        self.menu = menus.Choice(selection, options, topleft)

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.back()

        elif event == 'SELECT':
            selection = self.menu.get_current()
            SOUNDTHREAD.play_sfx('Select 1')

            if selection == 'Library':
                game.memory['next_state'] = 'base_library'
                game.state.change('transition_to')
            elif selection == 'Map':
                game.memory['next_state'] = 'base_world_map'
                game.state.change('transition_to')
            elif selection == 'Records':
                game.memory['next_state'] = 'base_records'
                game.state.change('transition_to')
            elif selection == 'Guide':
                game.memory['next_state'] = 'base_guide'
                game.state.change('transition_to')

    def update(self):
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        if self.menu:
            self.menu.draw(surf)
        return surf

class LoreDisplay():
    def __init__(self):
        self.lore = None
        self.topleft = (84, 4)
        self.width = WINWIDTH - 84
        self.bg_surf = base_surf.create_base_surf(self.width, WINHEIGHT - 8, 'menu_bg_brown')
        shimmer = SPRITES.get('menu_shimmer3')
        self.bg_surf.blit(shimmer, (self.bg_surf.get_width() - shimmer.get_width() - 1, self.bg_surf.get_height() - shimmer.get_height() - 5))
        self.bg_surf = image_mods.make_translucent(self.bg_surf, .1)

        self.left_arrow = gui.ScrollArrow('left', (self.topleft[0] + 4, 8))
        self.right_arrow = gui.ScrollArrow('right', (self.topleft[0] + self.width - 11, 8), 0.5)

        self.dialogs = []

    def update_entry(self, lore_nid):
        from app.engine import dialog

        if self.lore and lore_nid == self.lore.nid:
            return  # No need to update

        class LoreDialog(dialog.Dialog):
            num_lines = 8
            draw_cursor_flag = False

        self.lore = DB.lore.get(lore_nid)
        text = self.lore.text.split('\n')
        self.page_num = 0
        self.dialogs.clear()
        for idx, line in enumerate(text):
            dialog = LoreDialog(text[idx])
            dialog.position = self.topleft[0], self.topleft[1] + 12
            dialog.text_width = WINWIDTH - 100
            dialog.font = FONT['text-white']
            dialog.font_type = 'text'
            dialog.font_color = 'white'
            self.dialogs.append(dialog)
        self.num_pages = len(text)

    def page_right(self, first_push=False) -> bool:
        if self.page_num < self.num_pages - 1:
            self.page_num += 1
            self.right_arrow.pulse()
            return True
        elif first_push:
            self.page_num = (self.page_num + 1) % self.num_pages
            self.right_arrow.pulse()
            return True
        return False

    def page_left(self, first_push=False) -> bool:
        if self.page_num > 0:
            self.page_num -= 1
            self.left_arrow.pulse()
            return True
        elif first_push:
            self.page_num = (self.page_num - 1) % self.num_pages
            self.left_arrow.pulse()
            return True
        return False

    def draw(self, surf):
        if self.lore:
            image = self.bg_surf.copy()
            if game.get_unit(self.lore.nid):
                unit = game.get_unit(self.lore.nid)
                icons.draw_portrait(image, unit, (self.width - 96, WINHEIGHT - 12 - 80))
            elif self.lore.nid in DB.units.keys():
                portrait = icons.get_portrait_from_nid(DB.units.get(self.lore.nid).portrait_nid)
                image.blit(portrait, (self.width - 96, WINHEIGHT - 12 - 80))

            FONT['text-blue'].blit_center(self.lore.title, image, (self.width//2, 4))

            if self.num_pages > 1:
                text = '%d / %d' % (self.page_num + 1, self.num_pages)
                FONT['text-yellow'].blit_right(text, image, (self.width - 8, WINHEIGHT - 12 - 16))

            surf.blit(image, self.topleft)

            if self.dialogs and self.page_num < len(self.dialogs):
                self.dialogs[self.page_num].update()
                self.dialogs[self.page_num].draw(surf)

            if self.num_pages > 1:
                self.left_arrow.draw(surf)
                self.right_arrow.draw(surf)

        return surf

class BaseLibraryState(State):
    name = 'base_library'

    def __init__(self, name=None):
        super().__init__(name)
        self.fluid = FluidScroll()

    def _build_menu(self, unlocked_lore, ignore=None):
        topleft = 4, 4
        self.options = unlocked_lore
        self.menu = menus.Choice(None, self.options, topleft=topleft, background='menu_bg_brown')
        self.menu.shimmer = 3
        self.menu.gem = 'brown'
        self.menu.set_limit(9)
        self.menu.set_hard_limit(True)
        if ignore:
            self.menu.set_ignore(ignore)

    def start(self):
        self.bg = game.memory['base_bg']

        unlocked_lore = [lore for lore in DB.lore if lore.nid in game.unlocked_lore and lore.category != 'Guide']
        sorted_lore = sorted(unlocked_lore, key=lambda x: x.category)
        self.categories = []
        options = []
        ignore = []
        for lore in sorted_lore:
            if lore.category not in self.categories:
                self.categories.append(lore.category)
                options.append(lore)
                ignore.append(True)
            options.append(lore)
            ignore.append(False)

        self._build_menu(options, ignore)

        self.display = LoreDisplay()
        self.display.update_entry(self.menu.get_current().nid)

        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if not self.display.lore or self.display.lore.nid != self.menu.get_current().nid:
            self.display.update_entry(self.menu.get_current().nid)

        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
            self.display.update_entry(self.menu.get_current().nid)
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
            self.display.update_entry(self.menu.get_current().nid)
        elif 'RIGHT' in directions:
            if self.display.page_right():
                SOUNDTHREAD.play_sfx('Status_Page_Change')
        elif 'LEFT' in directions:
            if self.display.page_left():
                SOUNDTHREAD.play_sfx('Status_Page_Change')

        if event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.change('transition_pop')

        elif event == 'SELECT':
            if self.display.page_right(True):
                SOUNDTHREAD.play_sfx('Status_Page_Change')

        elif event == 'AUX':
            SOUNDTHREAD.play_sfx('Info')
            lore = self.menu.get_current()
            # Go to previous category
            cidx = self.categories.index(lore.category)
            new_category = self.categories[(cidx + 1) % len(self.categories)]
            idx = self.options.index(new_category)
            option = self.options[idx + 1]
            
            self.display.update_entry(option.nid)

        elif event == 'INFO':
            SOUNDTHREAD.play_sfx('Info')
            lore = self.menu.get_current()
            # Go to next category
            cidx = self.categories.index(lore.category)
            new_category = self.categories[(cidx - 1) % len(self.categories)]
            idx = self.options.index(new_category)
            option = self.options[idx + 1]

            self.display.update_entry(option.nid)

    def update(self):
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.menu:
            self.menu.draw(surf)
        if self.display:
            self.display.draw(surf)
        return surf

class BaseGuideState(BaseLibraryState):
    name = 'base_guide'

    def start(self):
        self.bg = game.memory.get('base_bg', None)
        if not self.bg:
            panorama = RESOURCES.panoramas.get('default_background')
            self.bg = background.ScrollingBackground(panorama)
            self.bg.scroll_speed = 50

        unlocked_lore = [lore for lore in DB.lore if lore.nid in game.unlocked_lore and lore.category == 'Guide']
        self.categories = ["Guide"]

        self._build_menu(unlocked_lore)

        self.display = LoreDisplay()
        self.display.update_entry(self.menu.get_current().nid)

        game.state.change('transition_in')
        return 'repeat'

class BaseRecordsState(State):
    name = 'base_records'

    def __init__(self, name=None):
        super().__init__(name)
        self.fluid = FluidScroll()

    def start(self):
        self.mouse_indicator = gui.MouseIndicator()
        self.bg = game.memory['base_bg']

        self.record_menu = record_book.RecordsDisplay()
        self.chapter_menus = [record_book.ChapterStats(option.get()[0]) for option in self.record_menu.options if not option.ignore]
        self.mvp = record_book.MVPDisplay()
        self.unit_menus = [record_book.UnitStats(option.get()[0]) for option in self.mvp.options if not option.ignore]

        self.state = 'records'
        self.current_menu = self.record_menu
        self.prev_menu = None

        self.current_offset_x = 0
        self.current_offset_y = 0
        self.prev_offset_x = 0
        self.prev_offset_y = 0

        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.current_menu.handle_mouse()

        if 'DOWN' in directions:
            if self.current_menu.move_down(first_push):
                SOUNDTHREAD.play_sfx('Select 6')
        elif 'UP' in directions:
            if self.current_menu.move_up(first_push):
                SOUNDTHREAD.play_sfx('Select 6')

        if event == 'LEFT':
            self.move_left()
                
        elif event == 'RIGHT':
            self.move_right()

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            if self.state in ('records', 'mvp'):
                game.state.change('transition_pop')
            else:
                self.prev_menu = self.current_menu
                self.current_offset_y = -WINHEIGHT
                self.prev_offset_y = 1

            if self.state == 'unit':
                self.state = 'mvp'
                self.current_menu = self.mvp
            elif self.state == 'chapter':
                self.state = 'records'
                self.current_menu = self.record_menu

        elif event == 'SELECT':
            if self.check_mouse_position():
                pass
            else:
                SOUNDTHREAD.play_sfx('Select 1')
                if self.state in ('records', 'mvp'):
                    self.prev_menu = self.current_menu
                    self.current_offset_y = WINHEIGHT
                    self.prev_offset_y = -1

                if self.state == 'records':
                    self.state = 'chapter'
                    self.current_menu = self.chapter_menus[self.current_menu.get_current_index()]
                elif self.state == 'mvp':
                    self.state = 'unit'
                    self.current_menu = self.unit_menus[self.current_menu.get_current_index()]

    def check_mouse_position(self):
        mouse_position = INPUT.get_mouse_position()
        if mouse_position:
            mouse_x, mouse_y = mouse_position
            if mouse_x <= 16:
                self.move_left()
                return True
            elif mouse_x >= WINWIDTH - 16:
                self.move_right()
                return True
            elif mouse_y <= 16:
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_up()
                return True
            elif mouse_y >= WINHEIGHT - 16:
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_down()
                return True
        return False

    def move_left(self):
        SOUNDTHREAD.play_sfx('Status_Page_Change')
        self.prev_menu = self.current_menu
        self.current_offset_x = -WINWIDTH
        self.prev_offset_x = 1
        if self.state == 'records':
            self.state = 'mvp'
            self.current_menu = self.mvp
        elif self.state == 'mvp':
            self.state = 'records'
            self.current_menu = self.record_menu
        elif self.state == 'chapter':
            self.record_menu.move_up(True)
            self.current_menu = self.chapter_menus[self.record_menu.get_current_index()]
        elif self.state == 'unit':
            self.mvp.move_up(True)
            self.current_menu = self.unit_menus[self.mvp.get_current_index()]

    def move_right(self):
        SOUNDTHREAD.play_sfx('Status_Page_Change')
        self.prev_menu = self.current_menu
        self.current_offset_x = WINWIDTH
        self.prev_offset_x = -1
        if self.state == 'records':
            self.state = 'mvp'
            self.current_menu = self.mvp
        elif self.state == 'mvp':
            self.state = 'records'
            self.current_menu = self.record_menu
        elif self.state == 'chapter':
            self.record_menu.move_down(True)
            self.current_menu = self.chapter_menus[self.record_menu.get_current_index()]
        elif self.state == 'unit':
            self.mvp.move_down(True)
            self.current_menu = self.unit_menus[self.mvp.get_current_index()]

    def update(self):
        if self.current_menu:
            self.current_menu.update()

        # X axis
        if self.current_offset_x > 0:
            self.current_offset_x -= 16
        elif self.current_offset_x < 0:
            self.current_offset_x += 16
        if self.prev_menu:
            if self.prev_offset_x > 0:
                self.prev_offset_x += 16
            elif self.prev_offset_x < 0:
                self.prev_offset_x -= 16
            if self.prev_offset_x > WINWIDTH or self.prev_offset_x < -WINWIDTH:
                self.prev_offset_x = 0
                self.prev_menu = None

        # Y axis
        if self.current_offset_y > 0:
            self.current_offset_y -= 16
        elif self.current_offset_y < 0:
            self.current_offset_y += 16
        if self.prev_menu:
            if self.prev_offset_y > 0:
                self.prev_offset_y += 16
            elif self.prev_offset_y < 0:
                self.prev_offset_y -= 16
            if self.prev_offset_y > WINHEIGHT or self.prev_offset_y < -WINHEIGHT:
                self.prev_offset_y = 0
                self.prev_menu = None

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.current_menu:
            self.current_menu.draw(surf, offset=(self.current_offset_x, self.current_offset_y))
        if self.prev_menu:
            self.prev_menu.draw(surf, offset=(self.prev_offset_x, self.prev_offset_y))
        if self.mouse_indicator:
            self.mouse_indicator.draw(surf)
        return surf
