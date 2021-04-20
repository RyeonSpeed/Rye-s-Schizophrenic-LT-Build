from app.utilities import utils
from app.constants import WINWIDTH, WINHEIGHT

from app.engine import config as cf
from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine import text_funcs, menu_options, image_mods, \
    gui, base_surf, help_menu, engine, menus, randomizer
from app.engine.game_state import game
from app.engine.randomizer import Rando


class ControlOption(menu_options.BasicOption):
    def __init__(self, idx, name, icon):
        self.idx = idx
        self.name = name
        self.display_name = text_funcs.translate(name)
        self.icon = icon
        self.help_box = None
        self.ignore = False

    def get(self):
        return self.name

    def width(self):
        return 224

    def height(self):
        return 16

    def draw(self, surf, x, y, active=False, get_input=False):
        name_font = 'text-white'
        key_font = 'text-blue'
        if active and get_input:
            name_font = 'text-yellow'
            key_font = 'text-yellow'
        surf.blit(self.icon, (x + 32 - self.icon.get_width() // 2, y + 8 - self.icon.get_height() // 2))
        FONT[name_font].blit(self.display_name, surf, (x + 56, y))
        key_name = engine.get_key_name(cf.SETTINGS[self.name])
        FONT[key_font].blit(key_name, surf, (x + 128, y))


class ConfigOption(menu_options.BasicOption):
    def __init__(self, idx, name, values, icon):
        self.idx = idx
        self.name = name
        self.display_name = text_funcs.translate(name).replace('_', ' ').capitalize()
        self.icon = icon
        self.help_box = None
        self.values = values
        self.ignore = False
        self.available = True

    def get(self):
        return self.name

    def width(self):
        return 224

    def height(self):
        return 16

    def get_value(self):
        return Rando.rando_settings[self.name]

    def move_left(self):
        value = self.get_value()
        if value in self.values:
            idx = self.values.index(value)
            idx = utils.clamp(idx - 1, 0, len(self.values) - 1)
            Rando.rando_settings[self.name] = self.values[idx]
        else:
            Rando.rando_settings[self.name] = self.values[0]

    def move_right(self):
        value = self.get_value()
        if value in self.values:
            idx = self.values.index(value)
            idx = utils.clamp(idx + 1, 0, len(self.values) - 1)
            Rando.rando_settings[self.name] = self.values[idx]
        else:
            Rando.rando_settings[self.name] = self.values[-1]

    def move_next(self):
        """
        Always move to the next one, even if it has to backwards
        """
        value = self.get_value()
        if value in self.values:
            idx = self.values.index(value)
            idx = (idx + 1) % len(self.values)
            Rando.rando_settings[self.name] = self.values[idx]
        else:
            Rando.rando_settings[self.name] = self.values[-1]


class SliderOption(ConfigOption):
    def __init__(self, idx, name, values, icon):
        super().__init__(idx, name, values, icon)
        self.counter = 0
        self.anim = [0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1]

    def draw(self, surf, x, y, active=False):
        self.counter = (self.counter + 1) % len(self.anim)
        surf.blit(self.icon, (x + 16, y))
        if self.available:
            name_font = 'text-white'
        else:
            name_font = 'text-grey'
        FONT[name_font].blit(self.display_name, surf, (x + 32, y))
        slider_bar = SPRITES.get('health_bar_bg')
        if not slider_bar:
            return
        surf.blit(slider_bar, (x + 150, y + 4))
        slider_cursor = SPRITES.get('waiting_cursor')
        if not slider_cursor:
            return
        value = Rando.rando_settings[self.name]
        if value in self.values:
            slider_fraction = self.values.index(value) / float(len(self.values) - 1)
        else:
            slider_fraction = value - self.values[0] / float(self.values[-1] - self.values[0])
        offset = slider_fraction * (slider_bar.get_width() - 6)
        if active:
            slider_bop = self.anim[self.counter] // 2 - 1
        else:
            slider_bop = 0
        surf.blit(slider_cursor, (x + 150 + offset, y + 4 + slider_bop))
        FONT['text-blue'].blit(str(value), surf, (x + 120 ,y))


class ChoiceOption(ConfigOption):
    def __init__(self, idx, name, values, icon):
        super().__init__(idx, name, values, icon)
        self.left_arrow = gui.ScrollArrow('left', (0, 0), 0)
        self.right_arrow = gui.ScrollArrow('right', (0, 0), 0.5)

    def move_left(self):
        value = Rando.rando_settings[self.name]
        if value in self.values:
            idx = self.values.index(value)
            idx = (idx - 1) % len(self.values)
            Rando.rando_settings[self.name] = self.values[idx]
        else:
            Rando.rando_settings[self.name] = self.values[0]
        self.left_arrow.pulse()

    def move_right(self):
        value = Rando.rando_settings[self.name]
        if value in self.values:
            idx = self.values.index(value)
            idx = (idx + 1) % len(self.values)
            Rando.rando_settings[self.name] = self.values[idx]
        else:
            Rando.rando_settings[self.name] = self.values[-1]
        self.right_arrow.pulse()

    def draw(self, surf, x, y, active=False):
        surf.blit(self.icon, (x + 16, y))
        if self.available:
            name_font = FONT['text-white']
        else:
            name_font = FONT['text-grey']
        name_font.blit(self.display_name, surf, (x + 32, y))
        value_font = FONT['text-blue']
        value = Rando.rando_settings[self.name]
        display_value = text_funcs.translate(value)
        value_font.blit_center(display_value, surf, (x + 164, y))
        self.draw_side_arrows(surf, x, y, active)

    def draw_side_arrows(self, surf, x, y, active):
        self.left_arrow.x = x + 112
        self.right_arrow.x = x + 216 - 8  # To account for right
        self.left_arrow.y = self.right_arrow.y = y
        self.left_arrow.draw(surf)
        self.right_arrow.draw(surf)


class SimpleOption(ConfigOption):
    def get_value(self):
        return str(Rando.rando_settings[self.name])

    def draw(self, surf, x, y, active=False):
        surf.blit(self.icon, (x + 16, y))
        if self.available:
            name_font = FONT['text-white']
        else:
            name_font = FONT['text-grey']
        name_font.blit(self.display_name, surf, (x + 32, y))
        value = str(Rando.rando_settings[self.name])

        running_width = 0
        for choice in self.values:
            if choice == value:
                font = FONT['text-blue']
            else:
                font = FONT['text-grey']
            text = text_funcs.translate(choice) + '    '
            font.blit(text, surf, (x + 112 + running_width, y))
            width = font.width(text)
            running_width += width


class BoolOption(ConfigOption):
    def move_left(self):
        value = Rando.rando_settings[self.name]
        if not value:
            Rando.rando_settings[self.name] = 1

    def move_right(self):
        value = Rando.rando_settings[self.name]
        if value:
            Rando.rando_settings[self.name] = 0

    def move_next(self):
        value = Rando.rando_settings[self.name]
        if value:
            Rando.rando_settings[self.name] = 0
        else:
            Rando.rando_settings[self.name] = 1

    def draw(self, surf, x, y, active=False):
        surf.blit(self.icon, (x + 16, y))
        if self.available:
            name_font = FONT['text-white']
        else:
            name_font = FONT['text-grey']
        name_font.blit(self.display_name, surf, (x + 32, y))
        value = Rando.rando_settings[self.name]

        if value:
            on_font = FONT['text-blue']
            off_font = FONT['text-grey']
        else:
            on_font = FONT['text-grey']
            off_font = FONT['text-blue']
        on_str = text_funcs.translate('ON') + '    '
        on_font.blit(on_str, surf, (x + 150, y))
        off_font.blit(text_funcs.translate('OFF'), surf, (x + 150 + on_font.width(on_str), y))

class BoolSpecialOption(ConfigOption):
    def __init__(self, idx, name, values, icon):
        super().__init__(idx, name, values, icon)
        self.value = False

    def get_list(self):
        return Rando.rando_settings[self.values]

    def get_value(self):
        pass

    def move_left(self):
        list = self.get_list()
        if not self.value:
            list.append(self.name)
            self.value = True

    def move_right(self):
        list = self.get_list()
        if self.value:
            list.remove(self.name)
            self.value = False

    def move_next(self):
        list = self.get_list()
        if self.value:
            list.remove(self.name)
            self.value = False
        else:
            list.append(self.name)
            self.value = True

    def draw(self, surf, x, y, active=False):
        surf.blit(self.icon, (x + 16, y))
        if self.available:
            name_font = FONT['text-white']
        else:
            name_font = FONT['text-grey']
        name_font.blit(self.display_name, surf, (x + 32, y))

        if self.value:
            on_font = FONT['text-blue']
            off_font = FONT['text-grey']
        else:
            on_font = FONT['text-grey']
            off_font = FONT['text-blue']
        on_str = text_funcs.translate('ON') + '    '
        on_font.blit(on_str, surf, (x + 150, y))
        off_font.blit(text_funcs.translate('OFF'), surf, (x + 150 + on_font.width(on_str), y))

class FinishOption(ConfigOption):
    def move_left(self):
        pass

    def move_right(self):
        pass

    def move_next(self):
        Rando.rando_settings['class_pools'] = randomizer.createClassPools(Rando)
        randomizer.createUnitDatabase(Rando)
        randomizer.createClassDatabase(Rando)

        if Rando.rando_settings['player_class_rando'] or Rando.rando_settings['boss_rando'] or Rando.rando_settings['generic_rando']:
            randomizer.randomizeClassStatic(Rando)
            randomizer.randomizeWexpStatic(Rando)
            randomizer.randomizeWeaponsStatic(Rando)
            if Rando.rando_settings['generic_rando']:
                randomizer.randomizeGenericWeaponsStatic(Rando)
        if Rando.rando_settings['item_rando']:
            Rando.rando_settings['itemDictionary'] = randomizer.createRandomItemDictionary(Rando)
        if Rando.rando_settings['promo_rando']:
            randomizer.randomizePromotions(Rando)
        if Rando.rando_settings['player_bases'] or Rando.rando_settings['boss_bases']:
            randomizer.randomizeBasesStatic(Rando)
        if Rando.rando_settings['named_growths']:
            randomizer.randomizeGrowthsStatic(Rando)
        if Rando.rando_settings['name_rando']:
            randomizer.randomizeNames(Rando)
        if Rando.rando_settings['portrait_rando']:
            randomizer.randomizePortraits(Rando)
        if Rando.rando_settings['desc_rando']:
            randomizer.randomizeDescriptions(Rando)
        #if Rando.rando_settings['personal_skill_rando']:
            #randomizer.randomizePersonalSkills(Rando)
        if Rando.rando_settings['class_skill_rando']:
            randomizer.randomizeClassSkills(Rando)

        Rando.rando_settings['Randomized'] = True
        game.state.change('title_new')
        #value = game.rando_settings[self.name]
        #if value:
            #game.rando_settings[self.name] = 0
        #else:
            #game.rando_settings[self.name] = 1

    def draw(self, surf, x, y, active=False):
        surf.blit(self.icon, (x + 16, y))
        name_font = FONT['text-white']
        name_font.blit(self.display_name, surf, (x + 32, y))
        #value = game.rando_settings[self.name]

        #if value:
            #on_font = FONT['text-blue']
            #off_font = FONT['text-grey']
        #else:
            #on_font = FONT['text-grey']
            #off_font = FONT['text-blue']
        #on_str = text_funcs.translate('ON') + '    '
        #on_font.blit(on_str, surf, (x + 112, y))
        #off_font.blit(text_funcs.translate('OFF'), surf, (x + 112 + on_font.width(on_str), y))

class WepSettingsOption(ConfigOption):
    def move_left(self):
        pass

    def move_right(self):
        pass

    def move_next(self):
        game.state.change('randomizer_status_menu')

    def draw(self, surf, x, y, active=False):
        surf.blit(self.icon, (x + 16, y))
        name_font = FONT['text-white']
        name_font.blit(self.display_name, surf, (x + 32, y))

class Controls(menus.Simple):
    def __init__(self, owner, options, background, icons, info=None):
        self.icons = icons
        super().__init__(owner, options, None, background, info)
        self.set_limit(6)

    def create_options(self, options, info_descs=None):
        self.options.clear()
        for idx, option in enumerate(options):
            option = ControlOption(idx, option, self.icons[idx])
            if info_descs:
                option.help_box = help_menu.HelpDialog(info_descs[idx])
            self.options.append(option)

    def move_left(self):
        pass

    def move_right(self):
        pass

    def move_next(self):
        pass

    def draw(self, surf, get_input=False):
        topleft = (8, 34)
        bg_surf = base_surf.create_base_surf(self.get_menu_width(), self.get_menu_height(), self.background)
        bg_surf = image_mods.make_translucent(bg_surf, .1)
        surf.blit(bg_surf, topleft)

        if len(self.options) > self.limit:
            self.draw_scroll_bar(surf, topleft)

        end_index = self.scroll + self.limit
        choices = self.options[self.scroll:end_index]
        running_height = 0

        for idx, choice in enumerate(choices):
            top = topleft[1] + 4 + running_height
            left = topleft[0] - 4

            active = (idx + self.scroll == self.current_index and self.takes_input)
            if get_input:
                choice.draw(surf, left, top, active, True)
            else:
                choice.draw(surf, left, top, active)
            if active:
                self.cursor.draw(surf, left + 8, top)

            running_height += choice.height()

        return surf

    def get_rects(self):
        topleft = (8, 34)
        end_index = self.scroll + self.limit
        choices = self.options[self.scroll:end_index]
        running_height = 0
        idxs, rects = [], []
        for idx, choice in enumerate(choices):
            top = topleft[1] + 4 + running_height
            left = topleft[0] - 4
            rect = (left, top, choice.width(), choice.height())
            rects.append(rect)
            idxs.append(self.scroll + idx)

            running_height += choice.height()
        return idxs, rects


class Config(Controls):
    def __init__(self, owner, options, background, icons, info=None):
        super().__init__(owner, options, background, icons, info)

    def create_options(self, options, info_descs=None):
        self.options.clear()
        for idx, option in enumerate(options):
            if option[1] is bool:
                option = BoolOption(idx, option[0], option[1], self.icons[idx])
            elif option[1] in ['weapon_properties','weapon_effective','weapon_imbue','weapon_inflict']:
                option = BoolSpecialOption(idx, option[0], option[1], self.icons[idx])
            elif option[1] is 'finish':
                option = FinishOption(idx, option[0], option[1], self.icons[idx])
            elif option[1] is 'weapon_settings':
                option = WepSettingsOption(idx, option[0], option[1], self.icons[idx])
            elif isinstance(option[1][0], int) or isinstance(option[1][0], float):
                option = SliderOption(idx, option[0], option[1], self.icons[idx])
            else:  # Is a list of text options or bool
                if len(' '.join([text_funcs.translate(o) for o in option[1]])) > 16:  # Long list
                    option = ChoiceOption(idx, option[0], option[1], self.icons[idx])
                else:  # Short list
                    option = SimpleOption(idx, option[0], option[1], self.icons[idx])
            if info_descs:
                option.help_box = help_menu.HelpDialog(info_descs[idx])
            self.options.append(option)

    def move_left(self):
        option = self.get_current_option()
        option.move_left()

    def move_right(self):
        option = self.get_current_option()
        option.move_right()

    def move_next(self):
        option = self.get_current_option()
        option.move_next()
