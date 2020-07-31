from app.engine import targets, status_system, action
from app.engine.game_state import game

class Ability():
    def targets(self, unit) -> set:
        return set()

    def highlights(self, unit):
        pass

    def do(self, unit):
        pass

class AttackAbility(Ability):
    name = 'Attack'

    def targets(self, unit) -> set:
        if self.cur_unit.has_attacked:
            return set()
        return targets.get_all_weapon_targets(unit)

    def highlights(self, unit):
        valid_attacks = targets.get_possible_attacks(unit, {unit.position})
        game.highlight.display_possible_attacks(valid_attacks)

class SpellAbility(Ability):
    name = 'Spell'

    def targets(self, unit) -> set:
        if self.cur_unit.has_attacked:
            return set()
        return targets.get_all_spell_targets(unit)

    def highlights(self, unit):
        valid_attacks = targets.get_possible_spell_attacks(unit, {unit.position})
        game.highlight.display_possible_spell_attacks(valid_attacks)

def get_adj_allies(unit) -> list:
    adj_positions = targets.get_adjacent_positions(unit)
    adj_units = [game.grid.get_unit(pos) for pos in adj_positions]
    adj_units = [_ for _ in adj_units if _]
    adj_allies = [u for u in adj_units if status_system.check_ally(unit, u)]
    return adj_allies

class DropAbility(Ability):
    name = "Drop"

    def targets(self, unit) -> set:
        if unit.traveler and not unit.has_attacked:
            good_pos = set()
            adj_positions = targets.get_adjacent_positions(unit)
            traveler = unit.traveler
            for adj_pos in adj_positions:
                if not game.grid.get_unit(adj_pos) and game.moving_units.get_mcost(unit, adj_pos) <= game.equations.movement(traveler):
                    good_pos.add(adj_pos)
            return good_pos
        return set()

    def do(self, unit):
        game.state.change('menu')
        u = game.level.units.get(unit.traveler)
        action.do(action.Drop(unit, u, game.cursor.position))

class RescueAbility(Ability):
    name = "Rescue"

    def targets(self, unit) -> set:
        if not unit.traveler and not unit.has_attacked:
            adj_allies = get_adj_allies(unit)
            return set([u.position for u in adj_allies if not u.traveler and
                        game.equations.rescue_aid(unit) > game.equations.rescue_weight(u)])

    def do(self, unit):
        u = game.grid.get_unit(game.cursor.position)
        action.do(action.Rescue(unit, u))
        if status_system.has_canto(unit):
            game.state.change('menu')
        else:
            game.state.change('free')
            action.do(action.Wait(unit))
            game.cursor.set_pos(unit.position)

class TakeAbility(Ability):
    name = 'take'

    def targets(self, unit) -> set:
        if not unit.traveler and not unit.has_attacked:
            adj_allies = get_adj_allies(unit)
            return set([u.position for u in adj_allies if u.traveler and
                        game.equations.rescue_aid(unit) > game.equations.rescue_weight(game.level.units.get(u.traveler))])

    def do(self, unit):
        u = game.grid.get_unit(game.cursor.position)
        action.do(action.Take(unit, u))
        # Taking does not count as major action
        game.state.change('menu')

class GiveAbility(Ability):
    name = 'give'

    def targets(self, unit) -> set:
        if unit.traveler and not unit.has_attacked:
            adj_allies = get_adj_allies(unit)
            return set([u.position for u in adj_allies if not u.traveler and
                        game.equations.rescue_aid(u) > game.equations.rescue_weight(game.level.units.get(unit.traveler))])

    def do(self, unit):
        u = game.grid.get_unit(game.cursor.position)
        action.do(action.Give(unit, u))
        # Giving does not count as a major action
        game.state.change('menu')

class ItemAbility(Ability):
    name = 'Item'

    def targets(self, unit) -> set:
        if unit.items:
            return {unit.position}
        return set()

class TradeAbility(Ability):
    name = 'Trade'

    def targets(self, unit) -> set:
        adj_allies = get_adj_allies(unit)
        return set([u.position for u in adj_allies if unit.team == u.team])

    def do(self, unit):
        game.state.change('trade')

ABILITIES = Ability.__sub_classes__()
