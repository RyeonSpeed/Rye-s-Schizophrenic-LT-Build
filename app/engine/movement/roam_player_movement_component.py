from __future__ import annotations

from typing import List, Tuple

from app.game_state import game
from app.engine import action
from app.engine.movement.movement_component import MovementComponent
from app.utilities import utils

import logging

class RoamPlayerMovementComponent(MovementComponent):
    """
    # Used for moving the player's roaming unit according to the player's inputs
    """
    min_speed = 0.48  # Unit must have a velocity above this to actually move (tiles per second)
    base_max_speed = 6.0  # maximum speed allowed (tiles per second)
    base_accel = 30.0  # normal acceleration to maximum speed (tiles per second^2)
    running_accel = 36.0  # acceleration to maximum speed while sprinting (tiles per second^2)
    deceleration = 72.0  # deceleration to 0 (tiles per second^2)

    def __init__(self, unit):
        super().__init__(follow=True, muted=False)
        self.unit = unit
        self.max_speed: float = game.game_vars.get("_roam_speed", 1) * self.base_max_speed
        self.sprint = False

        self.inputs = []
        self.start()

        self._last_update = 0

    def set_sprint(self, b: bool):
        self.sprint = b
        if b:
            self.max_speed = 1.5 * game.game_vars.get("_roam_speed", 1) * self.base_max_speed
        else:
            self.max_speed = 1.0 * game.game_vars.get("_roam_speed", 1) * self.base_max_speed

    def set_inputs(self, inputs: List[str]):
        self.inputs = inputs

    def get_position(self) -> Tuple[int, int]:
        return utils.round_pos(self.unit.position)

    def get_accel(self):
        if self.sprint:
            return self.running_accel
        else:
            return self.base_accel

    def start(self):
        # The unit's position is self.unit.position
        # What the unit's velocity is
        self.x_vel, self.y_vel = 0.0, 0.0
        # What the player is inputting
        self.x, self.y = 0.0, 0.0

    def finish(self, surprise=False):
        self.active = False

    def update(self, current_time: int):
        delta_time_ms = (current_time - self._last_update)
        # Never make delta time too large
        delta_time_ms = min(delta_time_ms, utils.frames2ms(4))
        delta_time = delta_time_ms / 1000  # Get delta time in seconds
        self._last_update = current_time

        if not self.active:
            return

        if not self.unit.position:
            logging.error("Unit %s is no longer on the map", self.unit)
            self.active = False
            return

        # === Process inputs ===
        self._kinematics(delta_time)

        # Actually move the unit if it's to move fast enough
        if utils.magnitude((self.x_vel, self.y_vel)) > self.min_speed:
            self.move(delta_time)
            self.unit.sprite.change_state('moving')
            self.unit.sprite.handle_net_position((self.x_vel, self.y_vel))
            self.unit.sprite.sound.play()
        else:
            self.unit.sprite.change_state('normal')
            self.unit.sprite.sound.stop()

        game.camera.force_center(*self.unit.position)

    def _kinematics(self, delta_time):
        """
        # Updates the velocity of the current unit
        """
        if 'LEFT' in self.inputs:
            self.x_mag = -1
        elif 'RIGHT' in self.inputs:
            self.x_mag = 1
        if 'UP' in self.inputs:
            self.y_mag = -1
        elif 'DOWN' in self.inputs:
            self.y_mag = 1

        # Modify velocity
        if self.x_mag > 0:
            self.x_vel += (self.get_accel() * delta_time)
        elif self.x_mag < 0:
            self.x_vel -= (self.get_accel() * delta_time)
        else:
            if self.x_vel > 0:
                self.x_vel -= (self.deceleration * delta_time)
                self.x_vel = max(0, self.x_vel)
            elif self.x_vel < 0:
                self.x_vel += (self.deceleration * delta_time)
                self.x_vel = min(0, self.x_vel)
        self.x_vel = utils.clamp(self.x_vel, -self.max_speed, self.max_speed)

        if self.y_mag > 0:
            self.y_vel += (self.get_accel() * delta_time)
        elif self.y_mag < 0:
            self.y_vel -= (self.get_accel() * delta_time)
        else:
            if self.y_vel > 0:
                self.y_vel -= (self.deceleration * delta_time)
                self.y_vel = max(0, self.y_vel)
            elif self.y_vel < 0:
                self.y_vel += (self.deceleration * delta_time)
                self.y_vel = min(0, self.y_vel)
        self.y_vel = utils.clamp(self.x_vel, -self.max_speed, self.max_speed)

    def move(self, delta_time):
        x, y = self.unit.position
        dx = self.x_vel * delta_time
        dy = self.y_vel * delta_time
        self.unit.position = x + dx, y + dy

        # Update fog of war!
        # This is necessary because the roaming unit has been
        # game.leave() off the map
        rounded_pos = utils.round_pos(self.unit.position)
        if game.board.fow_vantage_point.get(self.unit.nid) != rounded_pos:
            true_pos = self.unit.position
            # Inject the rounded position into UpdateFogOfWar
            self.unit.position = rounded_pos
            action.UpdateFogOfWar(self.unit).do()
            self.unit.position = true_pos  # Reset the position to its unrounded self
