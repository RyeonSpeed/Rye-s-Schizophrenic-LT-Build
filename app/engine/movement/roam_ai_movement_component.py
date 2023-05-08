from __future__ import annotations

from typing import List, Tuple

from app.engine import action
from app.engine.game_state import game
from app.engine.movement.roam_player_movement_component import RoamPlayerMovementComponent
from app.utilities import utils

import logging

class RoamAIMovementComponent(RoamPlayerMovementComponent):
    """
    # Used for moving the ai roaming unit according to a path given to it
    """
    def __init__(self, unit, follow=False, muted=False):
        super().__init__(unit, follow=follow, muted=muted)
        self.unit = unit
        # This is the copy we will work with
        self.position = self.unit.position
        self.speed_modifier: float = 1.0
        self.path = []
        self.start()

    def set_speed(self, mult: float = 1):
        self.speed_modifier = mult

    def set_path(self, path: List[Tuple[float, float]]):
        """
        # How I should get to my goal
        """
        # Get rid of my current position
        if path and path[-1] == self.unit.position:
            path.pop()
        self.path = path

    def get_end_goal(self) -> Tuple[int, int]:
        """
        # Returns what the final goal of this
        # movement is as a position
        """
        return utils.round_pos(self.path[0]) if self.path else self.unit.position

    def get_accel(self):
        return self.base_accel

    def get_desired_vector(self) -> Tuple[float, float]:
        desired_vector = (
            self.path[-1][0] - self.position[0],
            self.path[-1][1] - self.position[1],
        )
        desired_vector = utils.normalize(desired_vector)
        return desired_vector

    def _kinematics(self, delta_time):
        """
        # Updates the velocity of the current unit
        """
        print("_kinematics", self.path)
        if self.path:
            desired_vector = self.get_desired_vector()
            self.x_mag, self.y_mag = desired_vector
        else:
            self.x_mag, self.y_mag = (0, 0)
        print(self.x_mag, self.y_mag)
        # Modify velocity
        self._accelerate(delta_time, self.x_mag, self.y_mag)

    def move(self, delta_time):
        print("actually move")
        x, y = self.position
        dx = self.x_vel * delta_time * self.speed_modifier
        dy = self.y_vel * delta_time * self.speed_modifier
        next_position = (x + dx, y + dy)

        rounded_pos = utils.round_pos(next_position)
        if self._can_move(rounded_pos):
            self.position = next_position
        else:
            self.path.clear()
            return

        # Assign the position to the image
        self.unit.sprite.set_roam_position(self.position)

        # Move the unit's true position if necessary
        if rounded_pos != self.unit.position:
            game.leave(self.unit)
            self.unit.position = rounded_pos
            game.arrive(self.unit)
            action.UpdateFogOfWar(self.unit).do()

        if self.path and self.unit.position == self.path[-1]:
            self.path.pop()
