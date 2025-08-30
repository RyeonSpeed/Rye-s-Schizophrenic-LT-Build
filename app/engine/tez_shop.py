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

import threading

import logging

class TezukaShopState(State):
    name = 'tez_shop'

    def start(self):
        self.fluid = FluidScroll()
        self.tstate = 'start'
        self.tframe = 40
        self.unit = game.memory['current_unit']
        self.shopkeeper = game.memory['shopkeeper']

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
        
        # TODO
        self.choice_menu = menus.Choice(self.unit, ["Buy", "Sell"], (120, 32), background=None)
        self.choice_menu.set_horizontal(True)
        self.choice_menu.set_color(['convo-white', 'convo-white'])
        self.choice_menu.set_highlight(False)                

        items = game.memory['shop_items']
        self.stock = game.memory.get('shop_stock', None)
        my_items = item_funcs.get_all_tradeable_items(self.unit)
        self.sell_menu = menus.TezukaShop(self.unit, my_items, disp_value='sell')
        self.buy_menu = menus.TezukaShop(self.unit, my_items, disp_value='buy', stock=self.stock)

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
        d.font = FONT['nconvo-white']
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
            if 'DOWN' in directions or 'RIGHT' in directions:
                if self.menu.move_down(first_push):
                    get_sound_thread().play_sfx('Select 6')
            elif 'UP' in directions or 'LEFT' in directions:
                if self.menu.move_up(first_push):
                    get_sound_thread().play_sfx('Select 6')

        if event == 'SELECT':
            if self.state == 'open':
                get_sound_thread().play_sfx('Select 1')
                self.current_msg.hurry_up()
                if self.current_msg.is_done_or_wait():
                    self.state = 'choice'
                    self.menu = self.choice_menu

            elif self.state == 'choice':
                get_sound_thread().play_sfx('Select 1')
                current = self.choice_menu.get_current()
                if current == 'Buy':
                    self.menu = self.buy_menu
                    self.state = 'buy'
                    self.current_msg = self.get_dialog(self.buy_message)
                    self.buy_menu.set_takes_input(True)
                elif current == 'Sell' and item_funcs.get_all_tradeable_items(self.unit):
                    self.menu = self.sell_menu
                    self.state = 'sell'
                    self.sell_menu.set_takes_input(True)

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
                self.menu.toggle_info()
                if self.menu.info_flag:
                    get_sound_thread().play_sfx('Info In')
                else:
                    get_sound_thread().play_sfx('Info Out')

    def update(self):
        if self.current_msg:
            self.current_msg.update()
        if self.menu:
            self.menu.update()
        if self.tframe:
            self.tframe = self.tframe - 1
        if not self.tframe:
            self.tstate = None

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
                toffset = int(self.tframe * 1.5)
            x_pos = (im.get_width() - 96)//2
            im_surf = engine.subsurface(im, (x_pos, 0, 96, 136))
            surf.blit(im_surf, (0, 32 + toffset))
            
        bottom_bg = SPRITES.get('tez_shop_text')
        surf.blit(bottom_bg, (0, 0))

        if self.tstate == 'start':
            return surf

        money_bg = SPRITES.get('tez_gold')
        money_bg = image_mods.make_translucent(money_bg, .1)
        surf.blit(money_bg, (0, 0))

        FONT['text-white'].blit_right(str(game.get_money()) + ' G', surf, (58, -3))
        self.money_counter_disp.draw(surf)
        FONT['text-white'].blit(str(self.display_name), surf, (2, 90))

        if self.current_msg:
            self.current_msg.draw(surf)

        return surf

    def draw(self, surf):
        surf = self._draw(surf)
        if self.tstate == 'start':
            return surf

        if self.state == 'sell':
            self.sell_menu.draw(surf)
        else:
            self.buy_menu.draw(surf)
            if self.stock:
                FONT['text'].blit_center(text_funcs.translate('Item'), surf, (80, 64), color='yellow')
                FONT['text'].blit_center(text_funcs.translate('Uses'), surf, (128, 64), color='yellow')
                FONT['text'].blit_center(text_funcs.translate('Stock'), surf, (156, 64), color='yellow')
                FONT['text'].blit_center(text_funcs.translate('Price'), surf, (186, 64), color='yellow')
            if self.buy_menu.info_flag:
                surf = self.buy_menu.vert_draw_info(surf)
        if self.state == 'choice' and self.current_msg.is_done_or_wait():
            self.choice_menu.draw(surf)

        return surf
