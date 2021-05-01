from app.counters import generic3counter
from app.utilities import utils
from app.constants import TILEWIDTH, TILEHEIGHT, FRAMERATE

from app.engine.sprites import SPRITES
from app.engine.sound import SOUNDTHREAD
from app.engine import engine, target_system, skill_system
from app.engine import config as cf
from app.engine.game_state import game
from app.engine.input_manager import INPUT
from app.engine.fluid_scroll import FluidScroll

import logging

class Cursor():
    def __init__(self):
        self.cursor_counter = generic3counter(20*FRAMERATE, 2*FRAMERATE, 8*FRAMERATE)
        self.position = (0, 0)
        self.cur_unit = None
        self.path = []
        self.draw_state = 0
        self.speed_state = False

        self.sprite = SPRITES.get('cursor')
        self.format_sprite(self.sprite)
        self.offset_x, self.offset_y = 0, 0

        self.fluid = FluidScroll(cf.SETTINGS['cursor_speed'])

        self._display_arrows: bool = False
        self.arrows = []
        self._last_valid_position = None  # Last position within movement borders
        self.stopped_at_move_border = False

        self.mouse_mode: bool = False

    def get_hover(self):
        unit = game.board.get_unit(self.position)
        if unit and 'Tile' not in unit.tags and game.board.in_vision(unit.position):
            return unit
        return None

    def hide(self):
        self.draw_state = 0

    def show(self):
        self.draw_state = 1

    def combat_show(self):
        self.draw_state = 2

    def set_turnwheel_sprite(self):
        self.draw_state = 3

    def formation_show(self):
        self.draw_state = 4

    def set_speed_state(self, val: bool):
        self.speed_state = val

    def set_pos(self, pos):
        logging.debug("New position %s", pos)
        self.position = pos
        self.offset_x, self.offset_y = 0, 0
        game.camera.set_xy(*self.position)
        game.ui_view.remove_unit_display()

    def _get_path(self) -> list:
        if not self._last_valid_position:
            self.path.clear()
            return self.path

        if self.path:
            if self._last_valid_position in self.path:
                idx = self.path.index(self._last_valid_position)
                self.path = self.path[idx:]
                return self.path
            elif self._last_valid_position in target_system.get_adjacent_positions(self.path[0]):
                self.path.insert(0, self._last_valid_position)
                if target_system.check_path(self.cur_unit, self.path):
                    return self.path
        
        self.path = target_system.get_path(self.cur_unit, self._last_valid_position)
        return self.path

    def move(self, dx, dy, mouse=False, sound=True):
        x, y = self.position
        self.position = x + dx, y + dy

        # Cursor Sound
        if mouse:
            if dx == 0 and dy == 0:
                pass
            else:
                SOUNDTHREAD.stop_sfx('Select 5')
                SOUNDTHREAD.play_sfx('Select 5')
        else:
            SOUNDTHREAD.stop_sfx('Select 5')
            if sound:
                SOUNDTHREAD.play_sfx('Select 5')

        if game.highlight.check_in_move(self.position):
            self._last_valid_position = self.position

        if self._display_arrows:
            self.path = self._get_path()
            self.construct_arrows(self.path[::-1])

        # Remove unit info display
        if dx != 0 or dy != 0:
            game.ui_view.remove_unit_display()

        if mouse:
            self.offset_x += utils.clamp(8*dx, -8, 8)
            self.offset_y += utils.clamp(8*dy, -8, 8)
            self.offset_x = min(self.offset_x, 8)
            self.offset_y = min(self.offset_y, 8)
        # If we are slow
        elif cf.SETTINGS['cursor_speed'] >= 40:
            if self.speed_state:
                self.offset_x += 8*dx
                self.offset_y += 8*dy
            else:
                self.offset_x += 12*dx
                self.offset_y += 12*dy

        self.offset_x = min(self.offset_x, 12)
        self.offset_y = min(self.offset_y, 12)

    def autocursor(self, immediate=False):
        player_units = [unit for unit in game.units if unit.team == 'player' and unit.position]
        lord_units = [unit for unit in player_units if 'Lord' in unit.tags]
        if lord_units:
            self.set_pos(lord_units[0].position)
            if immediate:
                game.camera.force_center(*self.position)
            else:
                game.camera.set_center(*self.position)
        elif player_units:
            self.set_pos(player_units[0].position)
            if immediate:
                game.camera.force_center(*self.position)
            else:
                game.camera.set_center(*self.position)

    def place_arrows(self):
        self.path.clear()
        self._display_arrows = True

    def construct_arrows(self, path):
        self.arrows.clear()
        if len(path) <= 1:
            return
        for idx in range(len(path)):
            if idx == 0:  # Start of path
                direction = (path[idx + 1][0] - path[idx][0], path[idx + 1][1] - path[idx][1])
                if direction == (1, 0):  # Right
                    self.arrows.append(Arrow(0, 0, path[idx]))
                elif direction == (-1, 0):  # Left
                    self.arrows.append(Arrow(1, 1, path[idx]))
                elif direction == (0, -1):  # Up
                    self.arrows.append(Arrow(0, 1, path[idx]))
                elif direction == (0, 1):  # Down
                    self.arrows.append(Arrow(1, 0, path[idx]))
            elif idx == len(path) - 1:  # End of path
                direction = (path[idx][0] - path[idx - 1][0], path[idx][1] - path[idx - 1][1])
                if direction == (1, 0):  # Right
                    self.arrows.append(Arrow(6, 0, path[idx]))
                elif direction == (-1, 0):  # Left
                    self.arrows.append(Arrow(7, 1, path[idx]))
                elif direction == (0, -1):  # Up
                    self.arrows.append(Arrow(6, 1, path[idx]))
                elif direction == (0, 1):  # Down
                    self.arrows.append(Arrow(7, 0, path[idx]))
            else:  # Neither beginning nor end of path
                next_p = path[idx + 1]
                current_p = path[idx]
                prev_p = path[idx - 1]
                direction = (next_p[0] - prev_p[0], next_p[1] - prev_p[1])
                modifier = (current_p[0] - prev_p[0], current_p[1] - prev_p[1])
                if direction == (2, 0) or direction == (-2, 0):  # Right or Left
                    self.arrows.append(Arrow(3, 0, path[idx]))
                elif direction == (0, 2) or direction == (0, -2):  # Up or Down
                    self.arrows.append(Arrow(2, 0, path[idx]))
                elif direction == (1, -1) or direction == (-1, 1):  # Topleft or Bottomright
                    if modifier == (0, -1) or modifier == (-1, 0):
                        self.arrows.append(Arrow(4, 0, path[idx]))
                    elif modifier == (1, 0) or modifier == (0, 1):
                        self.arrows.append(Arrow(5, 1, path[idx]))
                elif direction == (1, 1) or direction == (-1, -1):  # Topright or Bottomleft
                    if modifier == (0, -1) or modifier == (1, 0):
                        self.arrows.append(Arrow(5, 0, path[idx]))
                    else:
                        self.arrows.append(Arrow(4, 1, path[idx]))

    def remove_arrows(self):
        self._last_valid_position = None
        self._display_arrows = False
        self.arrows.clear()

    def take_input(self):
        self.fluid.update()
        if self.stopped_at_move_border:
            directions = self.fluid.get_directions(double_speed=self.speed_state, slow_speed=True)
        else:
            directions = self.fluid.get_directions(double_speed=self.speed_state)

        if game.highlight.check_in_move(self.position):
            if directions:
                # If we would move off the current move
                if ('LEFT' in directions and not INPUT.just_pressed('LEFT') and
                        not game.highlight.check_in_move((self.position[0] - 1, self.position[1]))) or \
                        ('RIGHT' in directions and not INPUT.just_pressed('RIGHT') and
                         not game.highlight.check_in_move((self.position[0] + 1, self.position[1]))) or \
                        ('UP' in directions and not INPUT.just_pressed('UP') and
                         not game.highlight.check_in_move((self.position[0], self.position[1] - 1))) or \
                        ('DOWN' in directions and not INPUT.just_pressed('DOWN') and
                         not game.highlight.check_in_move((self.position[0], self.position[1] + 1))):
                    # Then we can just keep going
                    if self.stopped_at_move_border:
                        self.stopped_at_move_border = False
                    else:  # Ooh, we gotta stop the cursor movement
                        directions.clear()
                        self.fluid.reset()
                        self.stopped_at_move_border = True
                else:
                    self.stopped_at_move_border = False
        else:
            self.stopped_at_move_border = False

        # Handle keyboard first
        if 'LEFT' in directions and self.position[0] > 0:
            self.move(-1, 0)
            game.camera.cursor_x(self.position[0])
            self.mouse_mode = False
        elif 'RIGHT' in directions and self.position[0] < game.tilemap.width - 1:
            self.move(1, 0)
            game.camera.cursor_x(self.position[0])
            self.mouse_mode = False

        if 'UP' in directions and self.position[1] > 0:
            self.move(0, -1)
            game.camera.cursor_y(self.position[1])
            self.mouse_mode = False
        elif 'DOWN' in directions and self.position[1] < game.tilemap.height - 1:
            self.move(0, 1)
            game.camera.cursor_y(self.position[1])
            self.mouse_mode = False

        # Handle mouse
        mouse_position = INPUT.get_mouse_position()
        if mouse_position:
            self.mouse_mode = True
        if self.mouse_mode:
            # Get the actual mouse position, irrespective if actually used recently
            mouse_pos = INPUT.get_real_mouse_position()
            if mouse_pos:
                new_pos = mouse_pos[0] // TILEWIDTH, mouse_pos[1] // TILEHEIGHT
                new_pos = int(new_pos[0] + game.camera.get_x()), int(new_pos[1] + game.camera.get_y())
                dpos = new_pos[0] - self.position[0], new_pos[1] - self.position[1]
                self.move(dpos[0], dpos[1], mouse=True, sound=bool(mouse_position))
                game.camera.cursor_x(self.position[0])
                game.camera.cursor_y(self.position[1])

    def update(self):
        self.cursor_counter.update(engine.get_time())
        left = self.cursor_counter.count * TILEWIDTH * 2
        hovered_unit = self.get_hover()
        if self.draw_state == 4:
            if game.check_for_region(self.position, 'formation'):
                self.image = engine.subsurface(self.formation_sprite, (0, 0, 32, 32))
            else:
                self.image = engine.subsurface(self.formation_sprite, (32, 0, 32, 32))
        elif self.draw_state == 2:
            self.image = engine.subsurface(self.red_sprite, (left, 0, 32, 32))
        elif self.draw_state == 3:  # Green for turnwheel
            self.image = engine.subsurface(self.green_sprite, (left, 0, 32, 32))
        elif hovered_unit and hovered_unit.team == 'player' and not hovered_unit.finished:
            self.image = self.active_sprite
        else:
            self.image = engine.subsurface(self.passive_sprite, (left, 0, 32, 32))

    def format_sprite(self, sprite):
        self.passive_sprite = engine.subsurface(sprite, (0, 0, 128, 32))
        self.red_sprite = engine.subsurface(sprite, (0, 32, 128, 32))
        self.active_sprite = engine.subsurface(sprite, (0, 64, 32, 32))
        self.formation_sprite = engine.subsurface(sprite, (64, 64, 64, 32))
        self.green_sprite = engine.subsurface(sprite, (0, 96, 128, 32))

    def draw(self, surf, cull_rect):
        if self.draw_state:
            x, y = self.position
            left = x * TILEWIDTH - max(0, (self.image.get_width() - 16)//2) - self.offset_x
            top = y * TILEHEIGHT - max(0, (self.image.get_height() - 16)//2) - self.offset_y
            surf.blit(self.image, (left - cull_rect[0], top - cull_rect[1]))

            # Now reset offset
            num = 8 if self.speed_state else 4
            if self.offset_x > 0:
                self.offset_x = max(0, self.offset_x - num)
            elif self.offset_x < 0:
                self.offset_x = min(0, self.offset_x + num)
            if self.offset_y > 0:
                self.offset_y = max(0, self.offset_y - num)
            elif self.offset_y < 0:
                self.offset_y = min(0, self.offset_y + num)

        return surf

    def draw_arrows(self, surf, cull_rect):
        if self._display_arrows:
            for arrow in self.arrows:
                surf = arrow.draw(surf, cull_rect)
        return surf

class Arrow(object):
    sprite = SPRITES.get('movement_arrows')

    def __init__(self, x, y, position):
        self.image = engine.subsurface(self.sprite, (x * TILEWIDTH, y * TILEHEIGHT, TILEWIDTH, TILEHEIGHT))
        self.position = position

    def draw(self, surf, cull_rect):
        x, y = self.position
        topleft = x * TILEWIDTH - cull_rect[0], y * TILEHEIGHT - cull_rect[1]
        surf.blit(self.image, topleft)
        return surf
