from app.utilities import utils
from app.data.database import DB

from app.engine.combat.solver import CombatPhaseSolver

from app.engine import action, skill_system, banner, item_system
from app.engine.game_state import game

from app.engine.objects.unit import UnitObject
from app.engine.objects.item import ItemObject

class SimpleCombat():
    ai_combat: bool = False
    event_combat: bool = False
    alerts: bool = False  # Whether to show end of combat alerts
    """
    Does the simple mechanical effects of combat without any effects
    """

    def _full_setup(self, attacker: UnitObject, main_item: ItemObject, items: list, 
                    positions: list, main_target_positions: list, splash_positions: list):
        self.attacker: UnitObject = attacker
        self.main_item: ItemObject = main_item
        self.target_positions: list = positions

        # Load in the defenders
        # List of UnitObject or None
        self.defenders = [game.board.get_unit(main_target_pos) if main_target_pos else None for main_target_pos in main_target_positions]
        # List of UnitObject
        self.all_defenders = list(set([_ for _ in self.defenders if _]))
        self.defender: UnitObject = None
        if len(self.all_defenders) == 1:
            self.defender = self.all_defenders[0]

        # Load in the splash units (list of list of UnitObjects)
        self.splashes = []
        for splash in splash_positions:
            s = []
            for splash_pos in splash:
                unit = game.board.get_unit(splash_pos)
                if unit:
                    s.append(unit)
            self.splashes.append(s)

        # All splash is the flattened version of self.splashes
        all_splash = [a for sublist in self.splashes for a in sublist]  # Flatten list
        self.all_splash = list(set([s for s in all_splash if s]))

        self.items = items
        self.def_items = [defender.get_weapon() if defender else None for defender in self.defenders]
        self.def_item = None
        if self.defender:
            self.def_item = self.defender.get_weapon()

    def __init__(self, attacker, main_item, items, positions, main_target_positions, splash_positions, script):
        self._full_setup(attacker, main_item, items, positions, main_target_positions, splash_positions)
        self.state_machine = CombatPhaseSolver(
            attacker, self.main_item, self.items,
            self.defenders, self.splashes, self.target_positions,
            self.defender, self.def_item, script)

        self.full_playback = []
        self.playback = []
        self.actions = []

        self.start_combat()
        while self.state_machine.get_state():
            self.actions, self.playback = self.state_machine.do()
            self.full_playback += self.playback
            self._apply_actions()
            self.state_machine.setup_next_state()

    def get_from_playback(self, s):
        return [brush for brush in self.playback if brush[0] == s]

    def get_from_full_playback(self, s):
        return [brush for brush in self.full_playback if brush[0] == s]

    def update(self) -> bool:
        self.clean_up()
        return True

    def _apply_actions(self):
        """
        Actually commit the actions that we had stored!
        """
        for act in self.actions:
            action.execute(act)

    def draw(self, surf):
        return surf

    def clean_up(self):
        game.state.back()

        # attacker has attacked
        action.do(action.HasAttacked(self.attacker))

        # Messages
        if self.defender:
            if skill_system.check_enemy(self.attacker, self.defender):
                action.do(action.Message("%s attacked %s" % (self.attacker.name, self.defender.name)))
            elif self.attacker is not self.defender:
                action.do(action.Message("%s helped %s" % (self.attacker.name, self.defender.name)))
            else:
                action.do(action.Message("%s used %s" % (self.attacker.name, self.main_item.name)))
        else:
            action.do(action.Message("%s attacked" % self.attacker.name))

        all_units = self._all_units()

        # Handle death
        for unit in all_units:
            if unit.get_hp() <= 0:
                game.death.should_die(unit)
            else:
                unit.sprite.change_state('normal')

        self.turnwheel_death_messages(all_units)

        self.handle_state_stack()
        game.events.trigger('combat_end', self.attacker, self.defender, self.main_item, self.attacker.position)
        self.handle_item_gain(all_units)

        # handle wexp & skills
        if not self.attacker.is_dying:
            self.handle_wexp(self.attacker, self.main_item, self.defender)
        if self.defender and self.def_item and not self.defender.is_dying:
            self.handle_wexp(self.defender, self.def_item, self.attacker)

        self.handle_exp()

        self.handle_records(self.full_playback, all_units)

        self.end_combat()

        self.handle_death(all_units)

        a_broke, d_broke = self.find_broken_items()
        self.handle_broken_items(a_broke, d_broke)

    def start_combat(self):
        game.events.trigger('combat_start', self.attacker, self.defender, self.main_item, self.attacker.position)
        skill_system.pre_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')

        already_pre = [self.attacker]
        for idx, defender in enumerate(self.defenders):
            # Make sure we only do this once
            if defender and defender not in already_pre:
                already_pre.append(defender)
                def_item = self.def_items[idx]
                skill_system.pre_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
        for unit in self.all_splash:
            skill_system.pre_combat(self.full_playback, unit, None, None, 'defense')

        skill_system.start_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        item_system.start_combat(self.full_playback, self.attacker, self.main_item, self.defender)

        already_pre = [self.attacker]
        for idx, defender in enumerate(self.defenders):
            if defender and defender not in already_pre:
                already_pre.append(defender)
                def_item = self.def_items[idx]
                skill_system.start_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
                if def_item:
                    item_system.start_combat(self.full_playback, defender, def_item, self.attacker)
        for unit in self.all_splash:
            skill_system.start_combat(self.full_playback, unit, None, None, 'defense')

    def end_combat(self):
        skill_system.end_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        item_system.end_combat(self.full_playback, self.attacker, self.main_item, self.defender)
        already_pre = [self.attacker]
        for idx, defender in enumerate(self.defenders):
            if defender and defender not in already_pre:
                already_pre.append(defender)
                def_item = self.def_items[idx]
                skill_system.end_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
                if def_item:
                    item_system.end_combat(self.full_playback, defender, def_item, self.attacker)
        for unit in self.all_splash:
            skill_system.end_combat(self.full_playback, unit, None, None, 'defense')

        skill_system.post_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        already_pre = [self.attacker]
        for idx, defender in enumerate(self.defenders):
            if defender and defender not in already_pre:
                already_pre.append(defender)
                def_item = self.def_items[idx]
                skill_system.post_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
        for unit in self.all_splash:
            skill_system.post_combat(self.full_playback, unit, None, None, 'defense')

    def _all_units(self) -> list:
        """
        Returns list of all units taking in this combat
        """
        all_units = [self.attacker]
        for unit in self.all_splash:
            if unit is not self.attacker:
                all_units.append(unit)
        for unit in self.all_defenders:
            if unit is not self.attacker:
                all_units.append(unit)
        return all_units

    def turnwheel_death_messages(self, units):
        messages = []
        dying_units = [u for u in units if u.is_dying]
        any_player_dead = any(not u.team.startswith('enemy') for u in dying_units)
        for unit in dying_units:
            if unit.team.startswith('enemy'):
                if any_player_dead:
                    messages.append("%s was defeated" % unit.name)
                else:
                    messages.append("Prevailed over %s" % unit.name)
            else:
                messages.append("%s was defeated" % unit.name)

        for message in messages:
            action.do(action.Message(message))

    def handle_state_stack(self):
        if self.event_combat:
            pass
        elif self.ai_combat:
            if skill_system.has_canto(self.attacker, self.defender):
                pass
            else:
                game.state.change('wait')
        elif self.attacker.is_dying:
            game.state.clear()
            game.state.change('free')
            game.state.change('wait')
        else:
            if not self.attacker.has_attacked or \
                    (self.attacker.team == 'player' and item_system.menu_after_combat(self.attacker, self.main_item)):
                game.state.change('menu')
            elif skill_system.has_canto(self.attacker, self.defender):
                game.state.change('move')
            else:
                game.state.clear()
                game.state.change('free')
                game.state.change('wait')

    def handle_item_gain(self, all_units):
        enemies = all_units.copy()
        enemies.remove(self.attacker)
        for unit in enemies:
            if unit.is_dying:
                for item in unit.items[:]:
                    if item.droppable:
                        action.do(action.RemoveItem(unit, item))
                        action.do(action.DropItem(self.attacker, item))
                        if self.alerts:
                            game.alerts.append(banner.AcquiredItem(self.attacker, item))
                            game.state.change('alert')
        if self.attacker.is_dying and self.defender:
            for item in self.attacker.items[:]:
                if item.droppable:
                    action.do(action.RemoveItem(self.attacker, item))
                    action.do(action.DropItem(self.defender, item))
                    if self.alerts:
                        game.alerts.append(banner.AcquiredItem(self.defender, item))
                        game.state.change('alert')

    def find_broken_items(self):
        a_broke, d_broke = False, False
        if item_system.is_broken(self.attacker, self.main_item):
            a_broke = True
        if self.def_item and item_system.is_broken(self.defender, self.def_item):
            d_broke = True
        return a_broke, d_broke

    def handle_broken_items(self, a_broke, d_broke):
        if a_broke:
            alert = item_system.on_broken(self.attacker, self.main_item)
            if self.alerts and self.attacker is not self.defender and alert and \
                    self.attacker.team == 'player' and not self.attacker.is_dying:
                game.alerts.append(banner.BrokenItem(self.attacker, self.main_item))
                game.state.change('alert')
        if d_broke:
            alert = item_system.on_broken(self.defender, self.def_item)
            if self.alerts and self.attacker is not self.defender and alert and \
                    self.defender.team == 'player' and not self.defender.is_dying:
                game.alerts.append(banner.BrokenItem(self.defender, self.def_item))
                game.state.change('alert')

    def handle_wexp(self, unit, item, target):
        marks = self.get_from_full_playback('mark_hit')
        marks += self.get_from_full_playback('mark_crit')
        if DB.constants.value('miss_wexp'):
            marks += self.get_from_full_playback('mark_miss')
        marks = [mark for mark in marks if mark[1] == unit and mark[4] == item]
        wexp = item_system.wexp(self.full_playback, unit, item, target)

        if self.alerts:
            func = action.do
        else:
            func = action.execute

        if DB.constants.value('double_wexp'):
            for mark in marks:
                if mark[2] and mark[2].is_dying and DB.constants.value('kill_wexp'):
                    func(action.GainWexp(unit, item, wexp*2))
                else:
                    func(action.GainWexp(unit, item, wexp))
        elif marks:
            if DB.constants.value('kill_wexp') and any(mark[2] and mark[2].is_dying for mark in marks):
                func(action.GainWexp(unit, item, wexp*2))
            else:
                func(action.GainWexp(unit, item, wexp))

    def handle_exp(self):
        # handle exp
        if self.attacker.team == 'player' and not self.attacker.is_dying:
            exp = self.calculate_exp(self.attacker, self.main_item)
            if self.defender and (skill_system.check_ally(self.attacker, self.defender) or 'Tile' in self.defender.tags):
                exp = int(utils.clamp(exp, 0, 100))
            else:
                exp = int(utils.clamp(exp, DB.constants.value('min_exp'), 100))

            if (self.alerts and exp > 0) or exp + self.attacker.exp >= 100:
                game.exp_instance.append((self.attacker, exp, None, 'init'))
                game.state.change('exp')

        elif self.defender and self.defender.team == 'player' and not self.defender.is_dying:
            exp = self.calculate_exp(self.defender, self.def_item)
            exp = int(utils.clamp(exp, DB.constants.value('min_exp'), 100))

            if (self.alerts and exp > 0) or exp + self.defender.exp >= 100:
                game.exp_instance.append((self.defender, exp, None, 'init'))
                game.state.change('exp')

    def calculate_exp(self, unit, item):
        marks = self.get_from_full_playback('mark_hit')
        marks += self.get_from_full_playback('mark_crit')
        marks = [mark for mark in marks if mark[1] == unit]
        total_exp = 0
        all_defenders = set()
        for mark in marks:
            attacker = mark[1]
            defender = mark[2]
            if defender in all_defenders:
                continue  # Don't double count defenders
            all_defenders.add(defender)

            exp = item_system.exp(self.full_playback, attacker, item, defender)
            exp *= skill_system.exp_multiplier(attacker, defender)
            if defender:
                exp *= skill_system.enemy_exp_multiplier(defender, attacker)
                if defender.is_dying:
                    exp *= float(DB.constants.value('kill_multiplier'))
                    if 'Boss' in defender.tags:
                        exp += int(DB.constants.value('boss_bonus'))
            total_exp += exp

        return total_exp

    def handle_records(self, full_playback, all_units):
        miss_marks = self.get_from_full_playback('mark_miss')
        hit_marks = self.get_from_full_playback('mark_hit')
        crit_marks = self.get_from_full_playback('mark_crit')

        for mark in miss_marks:
            attacker = mark[1]
            defender = mark[2]
            action.do(action.UpdateRecords('miss', (attacker.nid, defender.nid)))

        for mark in hit_marks:
            attacker = mark[1]
            defender = mark[2]
            action.do(action.UpdateRecords('hit', (attacker.nid, defender.nid)))

        for mark in crit_marks:
            attacker = mark[1]
            defender = mark[2]
            action.do(action.UpdateRecords('crit', (attacker.nid, defender.nid)))

        damage_marks = self.get_from_full_playback('damage_hit')
        damage_marks += self.get_from_full_playback('damage_crit')
        for mark in damage_marks:
            kind, dealer, item, receiver, damage, true_damage = mark
            action.do(action.UpdateRecords('damage', (dealer.nid, receiver.nid, item.nid, damage, true_damage, 'crit' if kind == 'damage_crit' else 'hit')))

        heal_marks = self.get_from_full_playback('heal_hit')
        for mark in heal_marks:
            kind, dealer, item, receiver, heal, true_heal = mark
            action.do(action.UpdateRecords('heal', (dealer.nid, receiver.nid, item.nid, heal, true_heal, 'hit')))

        for mark in self.full_playback:
            if mark[0] in ('mark_miss', 'mark_hit', 'mark_crit'):
                attacker = mark[1]
                defender = mark[2]
                if defender.is_dying:
                    act = action.UpdateRecords('kill', (attacker.nid, defender.nid))
                    action.do(act)
                    if defender.team == 'player':  # If player is dying, save this result even if we turnwheel back
                        act = action.UpdateRecords('death', (attacker.nid, defender.nid))
                        act.do()
                if attacker.is_dying:
                    act = action.UpdateRecords('kill', (defender.nid, attacker.nid))
                    action.do(act)
                    if defender.team == 'player':  # If player is dying, save this result even if we turnwheel back
                        act = action.UpdateRecords('death', (defender.nid, attacker.nid))
                        act.do()

    def handle_death(self, units):
        for unit in units:
            if unit.is_dying:
                game.state.change('dying')
                break
        for unit in units:
            if unit.is_dying:
                game.events.trigger('unit_death', unit, position=unit.position)
                skill_system.on_death(unit)
