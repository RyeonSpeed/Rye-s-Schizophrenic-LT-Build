from app.utilities import utils

from app.engine.sound import get_sound_thread
from app.engine.state import MapState
from app.engine.game_state import game
from app.engine import engine, info_menu, evaluate, target_system, action
from app.engine.input_manager import get_input_manager

import logging

class FreeRoamState(MapState):
    name = 'free_roam'

    def start(self):
        self.roam_unit = None
        self.last_move = 0

        # speed and direction variables
        self.speed = 0.00
        self.vspeed = 0.0
        self.hspeed = 0.0
        self.direction = [0, 0]

    def begin(self):
        game.cursor.hide()

        if game.level.roam and game.level.roam_unit:
            roam_unit_nid = game.level.roam_unit
            if self.roam_unit and self.roam_unit.nid != roam_unit_nid:
                self.rationalize()  # Rationalize original unit
                # Now get the new one
                self.roam_unit = game.get_unit(roam_unit_nid)
                game.cursor.cur_unit = self.roam_unit
                # Roam unit is no longer consider to be on the board
                game.leave(self.roam_unit)
            elif self.roam_unit:
                # Don't need to do anything --  just reusing the same unit
                pass
            elif game.get_unit(roam_unit_nid):
                self.roam_unit = game.get_unit(roam_unit_nid)
                game.cursor.cur_unit = self.roam_unit
                # Roam unit is no longer consider to be on the board
                game.leave(self.roam_unit)
            else:
                logging.error("Roam State unable to find roaming unit %s", roam_unit_nid)

        elif self.roam_unit:  # Have a roam unit and we shouldn't...
            # No roam unit assigned, time to go
            self.rationalize()

        if not self.roam_unit or not self.roam_unit.position:
            game.level.roam = False
            # Leave this state
            game.state.back()
            return 'repeat'

        rounded_pos = int(self.roam_unit.position[0]), int(self.roam_unit.position[1])
        game.cursor.set_pos(rounded_pos)

    def take_input(self, event):
        base_speed = 0.008
        base_accel = 0.008
        running_accel = 0.01

        if get_input_manager().is_pressed('BACK'):
            max_speed = 0.15
        else:
            max_speed = 0.1

        # Horizontal direction
        if (get_input_manager().is_pressed('LEFT') or get_input_manager().just_pressed('LEFT')) and self.roam_unit.position[0] > game.board.bounds[0]:
            self.last_move = engine.get_time()
            self.direction[0] = -5
        elif (get_input_manager().is_pressed('RIGHT') or get_input_manager().just_pressed('RIGHT')) and self.roam_unit.position[0] < game.board.bounds[2]:
            self.last_move = engine.get_time()
            self.direction[0] = 5

        if not get_input_manager().is_pressed('RIGHT') and self.direction[0] > 0:
            self.direction[0] -= 1

        if not get_input_manager().is_pressed('LEFT') and self.direction[0] < 0:
            self.direction[0] += 1

        # Vertical direction
        if (get_input_manager().is_pressed('UP') or get_input_manager().just_pressed('UP')) and self.roam_unit.position[1] > game.board.bounds[1]:
            self.last_move = engine.get_time()
            self.direction[1] = -5
        elif (get_input_manager().is_pressed('DOWN') or get_input_manager().just_pressed('DOWN')) and self.roam_unit.position[1] < game.board.bounds[3]:
            self.last_move = engine.get_time()
            self.direction[1] = 5

        if not get_input_manager().is_pressed('DOWN') and self.direction[1] > 0:
            self.direction[1] -= 1

        if not get_input_manager().is_pressed('UP') and self.direction[1] < 0:
            self.direction[1] += 1

        # Horizontal speed
        if self.direction[0] > 0 and self.can_move('RIGHT'):
            self.hspeed = self.speed
        elif self.direction[0] < 0 and self.can_move('LEFT'):
            self.hspeed = -self.speed
        else:
            self.hspeed = 0.0

        # Vertcal speed
        if self.direction[1] > 0 and self.can_move('DOWN'):
            self.vspeed = self.speed
        elif self.direction[1] < 0 and self.can_move('UP'):
            self.vspeed = -self.speed
        else:
            self.vspeed = 0.0

        # Actually move the unit
        if abs(self.hspeed) > base_speed or abs(self.vspeed) > base_speed:
            self.move(self.hspeed, self.vspeed)
            self.roam_unit.sprite.change_state('moving')
            self.roam_unit.sprite.handle_net_position((self.hspeed, self.vspeed))

        game.camera.force_center(*self.roam_unit.position)

        if any((get_input_manager().just_pressed(direction) for direction in ('LEFT', 'RIGHT', 'UP', 'DOWN'))) \
                or any((get_input_manager().is_pressed(direction) for direction in ('LEFT', 'RIGHT', 'UP', 'DOWN'))):
            for region in game.level.regions:
                if region.fuzzy_contains(self.roam_unit.position) and region.interrupt_move:
                    new_pos = (int(round(self.roam_unit.position[0])), int(round(self.roam_unit.position[1])))
                    current_occupant = game.board.get_unit(new_pos)
                    if current_occupant:
                        new_pos = target_system.get_nearest_open_tile(current_occupant, new_pos)
                    self.roam_unit.position = new_pos
            if self.speed < max_speed and get_input_manager().is_pressed('BACK'):
                self.speed += running_accel
            elif self.speed < max_speed:
                self.speed += base_accel
            elif self.speed > max_speed:
                self.speed -= running_accel
        elif self.speed >= base_speed or self.speed > max_speed:
            self.speed -= running_accel

        if event == 'SELECT':
            other_unit = self.can_talk()
            region = self.can_visit()
            if other_unit:
                get_sound_thread().play_sfx('Select 2')
                did_trigger = game.events.trigger('on_talk', self.roam_unit, other_unit)
                if did_trigger:
                    action.do(action.RemoveTalk(self.roam_unit.nid, other_unit.nid))
                    self.rationalize()
            elif region:
                get_sound_thread().play_sfx('Select 2')
                did_trigger = game.events.trigger(region.sub_nid, self.roam_unit, position=self.roam_unit.position, local_args={'region': region})
                if did_trigger:
                    self.rationalize()
                if did_trigger and region.only_once:
                    action.do(action.RemoveRegion(region))
            else:
                get_sound_thread().play_sfx('Error')

        elif event == 'AUX':
            game.state.change('option_menu')

        elif event == 'INFO':
            info_menu.handle_info()

    def update(self):
        super().update()
        if self.last_move and engine.get_time() - self.last_move > 166:
            self.last_move = 0
            self.roam_unit.sprite.change_state('normal')
            self.roam_unit.sound.stop()
            self.direction = [0, 0]

    def move(self, dx, dy):
        x, y = self.roam_unit.position
        self.roam_unit.position = x + dx, y + dy
        self.roam_unit.sound.play()
        rounded_pos = int(self.roam_unit.position[0]), int(self.roam_unit.position[1])
        game.cursor.set_pos(rounded_pos)

    def can_move(self, direc: str) -> bool:
        if direc == 'LEFT':
            check_x = int(round(self.roam_unit.position[0] - 0.4))
            check_y = int(round(self.roam_unit.position[1]))
            mcost = game.movement.get_mcost(self.roam_unit, (check_x, check_y))
            return mcost < 99 and self.no_bumps(check_x, check_y)
        elif direc == 'RIGHT':
            check_x = int(round(self.roam_unit.position[0] + 0.4))
            check_y = int(round(self.roam_unit.position[1]))
            mcost = game.movement.get_mcost(self.roam_unit, (check_x, check_y))
            return mcost < 99 and self.no_bumps(check_x, check_y)
        elif direc == 'UP':
            check_x = int(round(self.roam_unit.position[0]))
            check_y = int(round(self.roam_unit.position[1] - 0.4))
            mcost = game.movement.get_mcost(self.roam_unit, (check_x, check_y))
            return mcost < 99 and self.no_bumps(check_x, check_y)
        elif direc == 'DOWN':
            check_x = int(round(self.roam_unit.position[0]))
            check_y = int(round(self.roam_unit.position[1] + 0.4))
            mcost = game.movement.get_mcost(self.roam_unit, (check_x, check_y))
            return mcost < 99 and self.no_bumps(check_x, check_y)
        return True

    def no_bumps(self, x: int, y: int) -> bool:
        '''Used to detect if the space is occupied by an impassable unit'''
        new_pos = (x, y)
        if game.board.get_unit(new_pos):
            other_team = game.board.get_team(new_pos)
            if not other_team or utils.compare_teams(self.roam_unit.team, other_team):
                return True # Allies, this is fine
            else:  # Enemies
                return False
        return True

    def rationalize(self):
        """
        Done whenever the roam unit should be returned to a regular unit
        """
        new_pos = (int(round(self.roam_unit.position[0])), int(round(self.roam_unit.position[1])))
        current_occupant = game.board.get_unit(new_pos)
        if current_occupant:
            new_pos = target_system.get_nearest_open_tile(self.roam_unit, new_pos)
        self.roam_unit.position = new_pos
        game.arrive(self.roam_unit)
        self.roam_unit.sprite.change_state('normal')
        self.roam_unit.sound.stop()
        self.roam_unit = None
        self.last_move = 0

    def can_talk(self):
        """
        Returns a unit if that unit is close enough to talk. Returns the closest unit if more than one is
        available, or None if not good targets
        """
        units = []
        for unit in game.units:
            if unit.position and unit is not self.roam_unit and self.roam_unit and \
                    utils.calculate_distance(self.roam_unit.position, unit.position) < 1:
                units.append(unit)
        units = list(sorted(units, key=lambda unit: utils.calculate_distance(self.roam_unit.position, unit.position)))
        if units:
            return units[0]
        return None

    def can_visit(self):
        """
        Returns first region that is close enough to visit
        """
        for region in game.level.regions:
            if region.region_type == 'event' and region.fuzzy_contains(self.roam_unit.position):
                try:
                    truth = evaluate.evaluate(region.condition, self.roam_unit, position=self.roam_unit.position, local_args={'region': region})
                    if truth:
                        return region
                except Exception as e:
                    logging.error("%s: Could not evaluate {%s}" % (e, region.condition))
        return None
