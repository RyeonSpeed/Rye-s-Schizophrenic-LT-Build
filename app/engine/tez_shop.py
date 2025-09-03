from __future__ import annotations

from typing import Callable, List, Literal, Optional, Tuple
from collections import OrderedDict, defaultdict
from enum import Enum

from app.constants import TILEWIDTH, TILEHEIGHT, WINWIDTH, WINHEIGHT, TILEX
from app.data.database.database import DB
from app.data.resources.resources import RESOURCES
from app.engine.objects.unit import UnitObject
from app.events.regions import RegionType
from app.events import triggers, event_commands
from app.engine.objects.item import ItemObject

from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine.sound import get_sound_thread
from app.engine.state import State, MapState
import app.engine.config as cf
from app.engine.game_state import game
from app.engine import engine, action, menus, image_mods, \
    banner, save, phase, skill_system, item_system, \
    item_funcs, ui_view, base_surf, gui, background, dialog, \
    text_funcs, equations, evaluate, supports
from app.engine.combat import base_combat, interaction
from app.engine.selection_helper import SelectionHelper
from app.engine.abilities import ABILITIES, PRIMARY_ABILITIES, OTHER_ABILITIES, TradeAbility, SupplyAbility
from app.engine.input_manager import get_input_manager
from app.engine.fluid_scroll import FluidScroll
from app.engine.info_menu.info_menu_portrait import InfoMenuPortrait
from app.engine.graphics.text.text_renderer import fix_tags, render_text, text_width

import threading

import logging

class TezukaShopState(State):
    name = 'tez_shop'

    def start(self):
        self.fluid = FluidScroll()
        self.tstate = 'start'
        self.tframe = 60
        self.aframe = 0
        self.unit = game.memory['current_unit']
        self.shopkeeper = game.memory['shopkeeper']
        self.desc_idx = 0
        self.desc_array = []
        self.display_name = game.get_unit(self.shopkeeper).name if game.get_unit(self.shopkeeper) else 'Rinnosuke'
        self.opening_message = 'shop_opener'
        self.buy_message = 'shop_buy'
        self.back_message = 'shop_back'
        self.leave_message = 'shop_leave'
        self.buy_again_message = 'shop_buy_again'
        self.convoy_message = 'shop_convoy'
        self.no_stock_message = 'shop_no_stock'
        self.no_money_message = 'shop_no_money'
        self.max_inventory_message = 'shop_max_inventory'
        self.sell_again_message = 'shop_sell_again'
        self.again_message = 'shop_again'
        self.no_value_message = 'shop_no_value'

        self.current_portrait = None
        
        self.choice_menu = menus.TezukaChoice(self.unit, ["Buy", "Sell"], (165, 135), background=None)
        self.choice_menu.set_horizontal(True)
        self.choice_menu.set_color(['text-white', 'text-white'])
        self.choice_menu.set_highlight(False)
        self.choice_menu.set_width(30)

        items = game.memory['shop_items']
        self.stock = game.memory.get('shop_stock', None)
        my_items = item_funcs.get_all_tradeable_items(self.unit)
        self.sell_menu = menus.TezukaShop(self.unit, my_items, topleft=(98, 4), disp_value='sell')
        self.buy_menu = menus.TezukaShop(self.unit, items, topleft=(98, 4), disp_value='buy', stock=self.stock)
        self.sell_menu_2 = menus.Shop(self.unit, my_items, topleft=(95, 4), disp_value='sell')
        self.buy_menu_2 = menus.Shop(self.unit, items, topleft=(95, 4), disp_value='buy', stock=self.stock)
        self.sell_menu.set_limit(6)
        self.sell_menu.set_hard_limit(True)
        self.sell_menu_2.set_limit(6)
        self.sell_menu_2.set_hard_limit(True)
        self.buy_menu.set_limit(6)
        self.buy_menu.set_hard_limit(True)
        self.buy_menu_2.set_limit(6)
        self.buy_menu_2.set_hard_limit(True)
        self.menu = None  # For input

        self.state = 'open'
        self.current_msg = self.get_dialog(self.opening_message)
        
        # TODO
        self.money_counter_disp = gui.PopUpDisplay((223, 32))

        panorama = RESOURCES.panoramas.get('shop_menu_background')
        if not panorama:
            panorama = RESOURCES.panoramas.get('default_background')
        if panorama:
            self.bg = background.PanoramaBackground(panorama)
        else:
            self.bg = None

        game.state.change('transition_in')
        return 'repeat'

    def begin(self):
        self.fluid.reset_on_change_state()

    def get_dialog(self, text):
        text = text_funcs.translate_and_text_evaluate(text, self=self)
        d = dialog.Dialog(text, num_lines=3)
        d.position = (90, 100)
        d.text_width = 132
        d.width = d.text_width + 16
        d.font = FONT['text']
        d.font_type = 'text'
        d.font_color = 'white'
        d.reformat()
        return d

    def update_options(self):
        self.sell_menu.update_options(item_funcs.get_all_tradeable_items(self.unit))

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()
        
        if self.tstate:
            return

        if self.menu:
            self.menu.handle_mouse()
            if 'DOWN' in directions:
                if self.menu.move_down(first_push):
                    self.update_desc()
                    get_sound_thread().play_sfx('Select 6')
            elif 'RIGHT' in directions:
                if hasattr(self.menu, 'move_right'):
                    if self.menu.move_right(first_push):
                        self.update_desc()
                        get_sound_thread().play_sfx('Select 6')
                else:
                    if self.menu.move_down(first_push):
                        self.update_desc()
                        get_sound_thread().play_sfx('Select 6')
            elif 'UP' in directions:
                if self.menu.move_up(first_push):
                    self.update_desc()
                    get_sound_thread().play_sfx('Select 6')
            elif 'LEFT' in directions:
                if hasattr(self.menu, 'move_left'):
                    if self.menu.move_left(first_push):
                        self.update_desc()
                        get_sound_thread().play_sfx('Select 6')
                else:
                    if self.menu.move_up(first_push):
                        self.update_desc()
                        get_sound_thread().play_sfx('Select 6')

        if event == 'SELECT':
            if self.state == 'open':
                get_sound_thread().play_sfx('Select 1')
                self.current_msg.hurry_up()
                if self.current_msg.is_done_or_wait():
                    self.state = 'choice'
                    self.update_desc()
                    self.menu = self.choice_menu

            elif self.state == 'choice':
                get_sound_thread().play_sfx('Select 1')
                current = self.choice_menu.get_current()
                if current == 'Buy':
                    self.menu = self.buy_menu
                    self.state = 'buy'
                    self.current_msg = None
                    self.buy_menu.set_takes_input(True)
                    self.update_desc()
                elif current == 'Sell' and item_funcs.get_all_tradeable_items(self.unit):
                    self.menu = self.sell_menu
                    self.state = 'sell'
                    self.sell_menu.set_takes_input(True)
                    self.current_msg = None
                    self.update_desc()

            elif self.state == 'buy':
                item = self.buy_menu.get_current()
                if item:
                    value = item_funcs.buy_price(self.unit, item)
                    new_item = item_funcs.create_item(self.unit, item.nid)
                    if game.get_money() - value >= 0 and \
                            self.buy_menu.get_stock() != 0 and \
                            (not item_funcs.inventory_full(self.unit, new_item) or
                             game.game_vars.get('_convoy')):
                        action.do(action.HasTraded(self.unit))
                        get_sound_thread().play_sfx('GoldExchange')
                        action.do(action.GainMoney(game.current_party, -value))
                        action.do(action.UpdateRecords('money', (game.current_party, -value)))
                        stock_marker = '__shop_%s_%s' % (self.shop_id, item.nid)
                        action.do(action.SetGameVar(stock_marker, game.level_vars.get(stock_marker, 0) + 1))  # Remember that we bought one of this
                        self.buy_menu.decrement_stock()
                        self.money_counter_disp.start(-value)
                        game.register_item(new_item)
                        if not item_funcs.inventory_full(self.unit, new_item):
                            action.do(action.GiveItem(self.unit, new_item))
                            self.current_msg = self.get_dialog(self.buy_again_message)
                        elif game.game_vars.get('_convoy'):
                            action.do(action.PutItemInConvoy(new_item))
                            self.current_msg = self.get_dialog(self.convoy_message)
                        self.update_options()

                    # How it could fail
                    elif self.buy_menu.get_stock() == 0:
                        # We don't have any more of this in stock
                        get_sound_thread().play_sfx('Select 4')
                        self.current_msg = self.get_dialog(self.no_stock_message)
                    elif game.get_money() - value < 0:
                        # You don't have enough money
                        get_sound_thread().play_sfx('Select 4')
                        self.current_msg = self.get_dialog(self.no_money_message)
                    else:
                        # No inventory space
                        get_sound_thread().play_sfx('Select 4')
                        self.current_msg = self.get_dialog(self.max_inventory_message)

            elif self.state == 'sell':
                item = self.sell_menu.get_current()
                if item:
                    value = item_funcs.sell_price(self.unit, item)
                    if value:
                        action.do(action.HasTraded(self.unit))
                        get_sound_thread().play_sfx('GoldExchange')
                        action.do(action.GainMoney(game.current_party, value))
                        action.do(action.UpdateRecords('money', (game.current_party, value)))
                        self.money_counter_disp.start(value)
                        action.do(action.RemoveItem(self.unit, item))
                        self.current_msg = self.get_dialog(self.sell_again_message)
                        self.update_options()
                    else:
                        # No value, can't be sold
                        get_sound_thread().play_sfx('Select 4')
                        self.current_msg = self.get_dialog(self.no_value_message)
                else:
                    # You didn't choose anything to sell
                    get_sound_thread().play_sfx('Select 4')

            elif self.state == 'close':
                get_sound_thread().play_sfx('Select 1')
                if self.current_msg.is_done_or_wait():
                    if self.unit.has_traded:
                        action.do(action.HasAttacked(self.unit))
                    game.state.change('transition_pop')
                else:
                    self.current_msg.hurry_up()

        elif event == 'BACK':
            if self.state == 'open' or self.state == 'close':
                get_sound_thread().play_sfx('Select 4')
                if self.unit.has_traded:
                    action.do(action.HasAttacked(self.unit))
                game.state.change('transition_pop')
            elif self.state == 'choice':
                get_sound_thread().play_sfx('Select 4')
                self.state = 'close'
                self.current_msg = self.get_dialog(self.leave_message)
            elif self.state == 'buy' or self.state == 'sell':
                if self.menu.info_flag:
                    self.menu.toggle_info()
                    get_sound_thread().play_sfx('Info Out')
                else:
                    get_sound_thread().play_sfx('Select 4')
                    self.state = 'choice'
                    self.menu.set_takes_input(False)
                    self.menu = self.choice_menu
                    self.current_msg = self.get_dialog(self.again_message)

        elif event == 'INFO':
            if self.state == 'buy' or self.state == 'sell':
                if self.current_msg:
                    self.current_msg = None
                    self.desc_idx = -1
                self.desc_idx += 1
                if self.desc_idx > len(self.desc_array) - 1:
                    self.desc_idx = 0
                self.update_desc()
                get_sound_thread().play_sfx('Select 4')
                
        elif event == 'AUX':
            if self.state == 'buy' or self.state == 'sell':
                self.sell_menu, self.sell_menu_2, self.buy_menu, self.buy_menu_2 = self.sell_menu_2, self.sell_menu, self.buy_menu_2, self.buy_menu
                if self.state == 'buy':
                    self.menu = self.buy_menu
                elif self.state == 'sell':
                    self.menu = self.sell_menu
                self.menu.move_to(0)
                get_sound_thread().play_sfx('Select 4')

    def update(self):
        if self.current_msg:
            self.current_msg.update()
        if self.menu:
            self.menu.update()
        if self.tframe:
            self.tframe = self.tframe - 1
        if not self.tframe:
            self.tstate = None
        self.aframe += 1
        if self.aframe >= 6000:
            self.aframe = 0

    def _draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
            
        if not self.current_portrait:
            portrait = RESOURCES.portraits.get('Rinnosuke')
            self.current_portrait = InfoMenuPortrait(portrait, DB.constants.value('info_menu_blink'), True)
            if self.shopkeeper:
                portrait = RESOURCES.portraits.get(self.shopkeeper)

        # We do have a portrait, so update...
        if self.current_portrait:
            self.current_portrait.update()
            im = self.current_portrait.create_image()
            offset = self.current_portrait.portrait.info_offset
        # Draw portrait onto the surf
        if im:
            toffset = 0
            if self.tstate == 'start':
                toffset = max(0, int(self.tframe * 1.5) - 30)
            x_pos = (im.get_width() - 96)//2
            im_surf = engine.subsurface(im, (x_pos, 0, 96, 136))
            surf.blit(im_surf, (0, 32 + toffset))
            
        # Draw static elements
        bottom_bg = SPRITES.get('tez_shop_text')
        surf.blit(bottom_bg, (0, 0))

        return surf
        
    def update_desc(self):
        item = None
        if self.state == 'buy':
            item = self.buy_menu.get_current()
        elif self.state == 'sell':
            item = self.sell_menu.get_current()
            
        if item:
            self.current_msg = None
            if item_system.hover_description(self.unit, item):
                desc = item_system.hover_description(self.unit, item)
            elif item.desc:
                desc = item.desc
            elif not available:
                desc = "Cannot wield."
            else:
                desc = ""

            desc = desc.replace('{br}', '\n')
            lines = self.build_lines(desc, 132)
            lines = fix_tags(lines)
            self.desc_array = []
            desc_temp = []
            for idx, line in enumerate(lines):
                desc_temp.append(line)
                if idx % 3 == 2:
                    self.desc_array.append(desc_temp)
                    desc_temp = []
            if desc_temp:
                self.desc_array.append(desc_temp)

        else:
            self.desc_array = []
        
    def build_lines(self, desc, width):
        if not desc:
            desc = ''
        desc = text_funcs.translate(desc)
        # Hard set num lines if desc is very short
        if '\n' in desc:
            lines_pre = desc.splitlines()
            lines = []
            for line in lines_pre:
                line = text_funcs.line_wrap('text', line, width)
                lines.extend(line)
        else:
            lines = text_funcs.line_wrap('text', desc, width)
        
        return lines

    def draw(self, surf):
        surf = self._draw(surf)
        if self.tstate == 'start':
            special_surf = engine.copy_surface(surf)
            stock_bg = SPRITES.get('tez_scroll_bg')
            special_surf.blit(stock_bg, (90, 0))
            self.buy_menu.draw(special_surf)
            progress = 15 - self.tframe * 0.25 if self.tframe >= 32 else 55 - self.tframe * 1.5
            if self.tframe == 32:
                get_sound_thread().play_sfx('Shop Scroll')
            special_surf = engine.subsurface(special_surf, (0, max(0, 48 - progress), 240, 10 + progress * 2))
            surf.blit(special_surf, (0, max(0, 48 - progress)))
            scroll_top = SPRITES.get('tez_scroll_top')
            scroll_bottom = SPRITES.get('tez_scroll_bottom')
            surf.blit(scroll_top, (86, 44 - progress))
            surf.blit(scroll_bottom, (86, 54 + progress))
            bottom_bg = SPRITES.get('tez_shop_text')
            surf.blit(bottom_bg, (0, 0))
            return surf
            
        stock_bg = SPRITES.get('tez_scroll_bg')
        surf.blit(stock_bg, (90, 0))

        money_bg = SPRITES.get('tez_gold')
        money_bg = image_mods.make_translucent(money_bg, .1)
        surf.blit(money_bg, (0, 0))

        FONT['text-white'].blit_right(str(game.get_money()) + ' G', surf, (58, -3))
        self.money_counter_disp.draw(surf)
        FONT['text-white'].blit(str(self.display_name), surf, (2, 90))

        # Draw bottom text
        item = None
        if self.state == 'buy':
            item = self.buy_menu.get_current()
        elif self.state == 'sell':
            item = self.sell_menu.get_current()
            
        if item and item.weapon:
            rng = item_funcs.get_range_string(self.unit, item)
            dam = str(item.damage.value) if item.damage else '--'
            acc = str(item.hit.value) if item.hit else '--'
            crt = str(item.crit.value) if item.crit else '--'
            wt = str(item.weight.value) if item.weight else '--'
            typ = item_system.weapon_type(self.unit, item)
            rnk = ''
            if typ:
                rnk = item_system.weapon_rank(self.unit, item)
            
            weapon_bg = SPRITES.get('tez_bottom_left')
            surf.blit(weapon_bg, (0, 107))
            FONT['narrow-white'].blit('Mt', surf, (6, 125))
            FONT['narrow-white'].blit_right(dam, surf, (38, 125))
            FONT['narrow-white'].blit('Crit', surf, (6, 140))
            FONT['narrow-white'].blit_right(crt, surf, (38, 140))
            FONT['narrow-white'].blit('Rng', surf, (52, 110))
            FONT['narrow-white'].blit_right(rng, surf, (84, 110))
            FONT['narrow-white'].blit('Hit', surf, (52, 125))
            FONT['narrow-white'].blit_right(acc, surf, (84, 125))
            FONT['narrow-white'].blit('Wt', surf, (52, 140))
            FONT['narrow-white'].blit_right(wt, surf, (84, 140))
        
        if self.current_msg:
            self.current_msg.draw(surf)
        elif self.desc_array:    
            if item:
                name_bg = SPRITES.get('tez_nameplate')
                surf.blit(name_bg, (124, 104))
                FONT['text-white'].blit_center(item.name, surf, (167, 100))
            for idx, line in enumerate(self.desc_array[self.desc_idx]):
                FONT['text-white'].blit(line, surf, (96, 116 + idx * 12))

        if self.state == 'sell':
            self.sell_menu.draw(surf)
        else:
            self.buy_menu.draw(surf)
            if self.buy_menu.info_flag:
                surf = self.buy_menu.vert_draw_info(surf)
        if self.state == 'choice':
            self.choice_menu.draw(surf)

        return surf
