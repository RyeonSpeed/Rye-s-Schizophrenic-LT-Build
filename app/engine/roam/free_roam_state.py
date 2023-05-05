import logging

from app.engine import action, evaluate
from app.engine.game_state import game
from app.engine.input_manager import get_input_manager
from app.engine.roam import free_roam_ai
from app.engine.movement.roam_player_movement_component import RoamPlayerMovementComponent
from app.engine.movement import movement_funcs
from app.engine.sound import get_sound_thread
from app.engine.state import MapState
from app.events import triggers
from app.events.regions import RegionType
from app.utilities import utils

class FreeRoamState(MapState):
    name = 'free_roam'

    TALK_RANGE = 1.0

    def start(self):
        self.roam_unit = None
        self.movement_component = None

        self.ai_handler = free_roam_ai.FreeRoamAIHandler()

    def begin(self):
        game.cursor.hide()

        if game.level.roam and game.level.roam_unit:
            roam_unit_nid = game.level.roam_unit

            if self.roam_unit and self.roam_unit.nid != roam_unit_nid:
                # Now get the new unit
                unit = game.get_unit(roam_unit_nid)
                self._assign_unit(unit)
            elif self.roam_unit:
                # Don't need to do anything -- just reusing the same unit
                pass
            elif game.get_unit(roam_unit_nid):
                unit = game.get_unit(roam_unit_nid)
                self._assign_unit(roam_unit_nid)
            else:
                logging.error("Unable to find roaming unit %s", roam_unit_nid)

        elif self.roam_unit:  # Have a roam unit and we shouldn't...
            self.roam_unit = None

        if not self.roam_unit or not self.roam_unit.position:
            self.rationalize_all_units()
            self.leave()

    def leave(self):
        if self.movement_component:
            self.movement_component.finish()
        game.level.roam = False
        # Leave this state
        game.state.back()
        return 'repeat'

    def _assign_unit(self, unit):
        self.roam_unit = unit
        self.movement_component = RoamPlayerMovementComponent(unit)
        game.movement.add(self.movement_component)
        game.cursor.cur_unit = self.roam_unit

    def rationalize_all_units(self):
        """
        # Done whenever we would leave the roam state and we need the units to go to normal positions
        """
        self.ai_handler.stop_all_units()
        self.roam_unit = None
        if self.movement_component:
            self.movement_component.finish()
        game.state.change('free_roam_rationalize')

    def get_talk_partner(self):
        """
        # Returns a unit that roam unit can talk to.
        # Returns the closest unit if more than one is available.
        # Returns None if no good targets.
        """
        if not self.roam_unit:
            return None
        units = []
        for unit in game.get_all_units():
            if unit is not self.roam_unit and \
                    utils.calculate_distance(self.roam_unit.sprite.fake_position, unit.position) < self.TALK_RANGE and \
                    (self.roam_unit.nid, unit.nid) in game.talk_options:
                units.append(unit)
        units = list(sorted(units, key=lambda unit: utils.calculate_distance(self.roam_unit.position, unit.position)))
        if units:
            return units[0]
        return None

    def get_visit_region(self):
        """
        # Returns the first region that is close enough to visit
        """
        if not self.roam_unit:
            return None
        region = game.get_region_under_pos(self.roam_unit.position)
        if region and region.region_type == RegionType.EVENT:
            try:
                truth = evaluate.evaluate(region.condition, self.roam_unit, 
                                          position=self.roam_unit.position, 
                                          local_args={'region': region})
                if truth:
                    return region
            except Exception as e:
                logging.error("%s: Could not evaluate {%s}" % (e, region.condition))
        return None

    def check_region_interrupt(self):
        region = movement_funcs.check_region_interrupt(self.roam_unit.position)
        if region:
            did_trigger = game.events.trigger(triggers.RoamingInterrupt(self.roam_unit, self.roam_unit.position, region))
            if did_trigger and region.only_once:
                action.do(action.RemoveRegion())

    def check_select(self):
        """
        # Called whenever the player presses SELECT
        """
        other_unit = self.get_talk_partner()
        region = self.get_visit_region()

        if other_unit:
            get_sound_thread().play_sfx('Select 2')
            did_trigger = game.events.trigger(triggers.OnTalk(self.roam_unit, other_unit, None))
            if did_trigger:
                action.do(action.RemoveTalk(self.roam_unit.nid, other_unit.nid))
        elif region:
            get_sound_thread().play_sfx('Select 2')
            did_trigger = game.events.trigger(triggers.RegionTrigger(region.sub_nid, self.roam_unit, self.roam_unit.position, region))
            if did_trigger and region.only_once:
                action.do(action.RemoveRegion(region))
        else:
            get_sound_thread().play_sfx('Error')

    def check_info(self):
        """
        # Called whenever the player presses INFO
        """
        other_unit = self.get_talk_partner()
        did_trigger = game.events.trigger(triggers.RoamPressInfo(self.roam_unit, other_unit))
        if did_trigger:
            pass
        else:
            get_sound_thread().play_sfx('Select 1')
            game.memory['next_state'] = 'info_menu'
            game.memory['current_unit'] = self.roam_unit
            game.state.change('transition_to')

    def take_input(self, event):
        if not self.roam_unit:
            return

        # Handle movement controls
        # SPRINT
        if get_input_manager().is_pressed('BACK'):
            self.movement_component.set_sprint(True)
        else:
            self.movement_component.set_sprint(False)

        inputs = []
        for button in ['LEFT', 'RIGHT', 'UP', 'DOWN']:
            if get_input_manager().is_pressed(button) or get_input_manager().just_pressed(button):
                inputs.append(button)

        self.movement_component.set_inputs(inputs)

        # Now check regular events
        if event == 'SELECT':
            self.check_select()

        elif event == 'AUX':
            game.state.change('option_menu')

        elif event == 'INFO':
            self.check_info()

        elif event == 'START':
            did_trigger = game.events.trigger(triggers.RoamPressStart(self.roam_unit))
            if did_trigger:
                get_sound_thread().play_sfx('Select 2')
            else:
                get_sound_thread().play_sfx('Error')

    def update(self):
        super().update()
        game.movement.update()
        self.ai_handler.update()
        self.check_region_interrupt()
