from app.data.database import DB
from app.engine import (action, banner, item_funcs, item_system, skill_system,
                        static_random, supports)
from app.engine.combat.solver import CombatPhaseSolver
from app.engine.game_state import game
from app.engine.objects.item import ItemObject
from app.engine.objects.unit import UnitObject
from app.events import triggers, event_commands
from app.utilities import utils


class SimpleCombat():
    ai_combat: bool = False
    event_combat: bool = False
    arena_combat: bool = False
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

    def __init__(self, attacker, main_item, items, positions, main_target_positions, splash_positions, script, total_rounds=1):
        self._full_setup(attacker, main_item, items, positions, main_target_positions, splash_positions)
        self.state_machine = CombatPhaseSolver(
            attacker, self.main_item, self.items,
            self.defenders, self.splashes, self.target_positions,
            self.defender, self.def_item, script, total_rounds)

        self.full_playback = []
        self.playback = []
        self.actions = []

        self.start_combat()
        self.start_event()
        while self.state_machine.get_state():
            self.actions, self.playback = self.state_machine.do()
            self.full_playback += self.playback
            self._apply_actions()
            self.state_machine.setup_next_state()

    def get_from_playback(self, s):
        return [brush for brush in self.playback if brush.nid == s]

    def get_from_full_playback(self, s):
        return [brush for brush in self.full_playback if brush.nid == s]

    def skip(self):
        pass

    def end_skip(self):
        pass

    def stop_arena(self):
        self.state_machine.total_rounds = 0  # So that we are forced out next time

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

        self.handle_messages()

        all_units = self._all_units()

        for unit in all_units:
            if unit.get_hp() > 0:
                unit.sprite.change_state('normal')
                unit.sprite.reset()

        self.cleanup_combat()

        # Handle death
        for unit in all_units:
            if unit.get_hp() <= 0:
                game.death.should_die(unit)

        self.turnwheel_death_messages(all_units)

        self.handle_state_stack()
        game.events.trigger(triggers.CombatEnd(self.attacker, self.defender, self.attacker.position, self.main_item))
        self.handle_item_gain(all_units)

        pairs = self.handle_supports(all_units)
        self.handle_support_pairs(pairs)

        # handle wexp & skills
        if not self.attacker.is_dying:
            self.handle_wexp(self.attacker, self.main_item, self.defender)

        if DB.constants.value('pairup') and self.main_item:
            if self.attacker.strike_partner:
                self.handle_wexp(self.attacker.strike_partner, self.main_item, self.defender)
            if self.attacker.traveler:
                self.handle_wexp(game.get_unit(self.attacker.traveler), self.main_item, self.defender)

        if self.defender and self.def_item and not self.defender.is_dying:
            self.handle_wexp(self.defender, self.def_item, self.attacker)

        if DB.constants.value('pairup') and self.def_item:
            if self.defender and self.defender.strike_partner:
                self.handle_wexp(self.defender.strike_partner, self.def_item, self.attacker)
            if self.defender and self.defender.traveler:
                self.handle_wexp(game.get_unit(self.defender.traveler), self.def_item, self.attacker)

        self.handle_mana(all_units)
        self.handle_exp()

        self.handle_records(self.full_playback, all_units)

        self.end_combat()

        self.attacker.built_guard = True
        if self.defender:
            self.defender.strike_partner = None
            self.defender.built_guard = True

        self.handle_death(all_units)

        a_broke, d_broke = self.find_broken_items()
        self.handle_broken_items(a_broke, d_broke)

    def start_event(self, full_animation=False):
        # region is set to True or False depending on whether we are in a battle anim
        game.events.trigger(triggers.CombatStart(self.attacker, self.defender, self.attacker.position, self.main_item, full_animation))

    def start_combat(self):
        self.initial_random_state = static_random.get_combat_random_state()

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
        item_system.start_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')

        already_pre = [self.attacker]
        for idx, defender in enumerate(self.defenders):
            if defender and defender not in already_pre:
                already_pre.append(defender)
                def_item = self.def_items[idx]
                skill_system.start_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
                if def_item:
                    item_system.start_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
        for unit in self.all_splash:
            skill_system.start_combat(self.full_playback, unit, None, None, 'defense')

    def cleanup_combat(self):
        skill_system.cleanup_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        already_pre = [self.attacker]
        for idx, defender in enumerate(self.defenders):
            if defender and defender not in already_pre:
                already_pre.append(defender)
                def_item = self.def_items[idx]
                skill_system.cleanup_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
        for unit in self.all_splash:
            skill_system.cleanup_combat(self.full_playback, unit, None, self.attacker, 'defense')

    def end_combat(self):
        skill_system.end_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        item_system.end_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        if self.attacker.strike_partner:
            skill_system.end_combat(self.full_playback, self.attacker.strike_partner, self.attacker.strike_partner.get_weapon(), self.defender, 'attack')
            item_system.end_combat(self.full_playback, self.attacker.strike_partner, self.attacker.strike_partner.get_weapon(), self.defender, 'attack')
            self.attacker.strike_partner = None
        if self.defender:
            if self.defender.strike_partner:
                skill_system.end_combat(self.full_playback, self.defender.strike_partner, self.defender.strike_partner.get_weapon(), self.attacker, 'defense')
                item_system.end_combat(self.full_playback, self.defender.strike_partner, self.defender.strike_partner.get_weapon(), self.attacker, 'defense')
                self.defender.strike_partner = None
        already_pre = [self.attacker]
        for idx, defender in enumerate(self.defenders):
            if defender and defender not in already_pre:
                already_pre.append(defender)
                def_item = self.def_items[idx]
                skill_system.end_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
                if def_item:
                    item_system.end_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
        for unit in self.all_splash:
            skill_system.end_combat(self.full_playback, unit, None, self.attacker, 'defense')

        skill_system.deactivate_all_combat_arts(self.attacker)

        skill_system.post_combat(self.full_playback, self.attacker, self.main_item, self.defender, 'attack')
        already_pre = [self.attacker]
        for idx, defender in enumerate(self.defenders):
            if defender and defender not in already_pre:
                already_pre.append(defender)
                def_item = self.def_items[idx]
                skill_system.post_combat(self.full_playback, defender, def_item, self.attacker, 'defense')
        for unit in self.all_splash:
            skill_system.post_combat(self.full_playback, unit, None, self.attacker, 'defense')

        self.final_random_state = static_random.get_combat_random_state()
        action.do(action.RecordRandomState(self.initial_random_state, self.final_random_state))

    def _all_units(self) -> list:
        """
        Returns list of all units taking part in this combat
        """
        all_units = {self.attacker}
        if DB.constants.value('pairup'):
            if self.attacker.strike_partner:
                all_units.add(self.attacker.strike_partner)
            elif self.attacker.traveler:
                all_units.add(game.get_unit(self.attacker.traveler))
        for unit in self.all_splash:
            all_units.add(unit)
        for unit in self.all_defenders:
            if DB.constants.value('pairup'):
                if len(self.all_defenders) == 1 and unit.strike_partner:
                    all_units.add(unit.strike_partner)
                if unit.traveler:
                    all_units.add(game.get_unit(unit.traveler))
            all_units.add(unit)
        return all_units

    def handle_messages(self):
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
                if item_system.can_attack_after_combat(self.attacker, self.main_item):
                    action.do(action.HasNotAttacked(self.attacker))
                    action.do(action.HasTraded(self.attacker))
                game.state.change('menu')
            elif skill_system.has_canto(self.attacker, self.defender):
                game.cursor.set_pos(self.attacker.position)
                game.state.change('move')
                game.cursor.place_arrows()

            else:
                game.state.clear()
                game.state.change('free')
                game.state.change('wait')

    def handle_item_gain(self, all_units):
        # What we are doing is basically mocking a drop item event so it will happen in the correct order with other
        # events that we are adding to the event trigger stack
        enemies = all_units.copy()
        enemies.remove(self.attacker)
        counter = 0
        for unit in enemies:
            if unit.is_dying:
                for item in unit.items[:]:
                    if item.droppable:
                        action.do(action.RemoveItem(unit, item))
                        event_nid = 'DropItem%d' % counter
                        if self.alerts:
                            flags = None
                        else:
                            flags = {'no_banner'}
                        command = event_commands.GiveItem({'GlobalUnitOrConvoy': '{unit}', 'Item': str(item.uid)}, flags)
                        trigger = triggers.GenericTrigger(self.attacker, unit, self.attacker.position, {'item_uid': item.uid})
                        game.events._add_event(event_nid, [command], trigger)
                        counter += 1
                        
        if self.attacker.is_dying and self.defender:
            for item in self.attacker.items[:]:
                if item.droppable:
                    action.do(action.RemoveItem(self.attacker, item))
                    event_nid = 'DropItem%d' % counter
                    if self.alerts:
                        flags = None
                    else:
                        flags = {'no_banner'}
                    command = event_commands.GiveItem({'GlobalUnitOrConvoy': '{unit}', 'Item': str(item.uid)}, flags)
                    trigger = triggers.GenericTrigger(self.defender, self.attacker, self.defender.position, {'item_uid': item.uid})
                    game.events._add_event(event_nid, [command], trigger)
                    counter += 1

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
        marks = [mark for mark in marks if mark.attacker == unit and mark.item == item]
        wexp = item_system.wexp(self.full_playback, unit, item, target)

        if self.alerts:
            func = action.do
        else:
            func = action.execute

        if DB.constants.value('double_wexp'):
            for mark in marks:
                if mark.defender:
                    multiplier = skill_system.wexp_multiplier(unit, mark.defender) * skill_system.enemy_wexp_multiplier(mark.defender, unit)
                else:
                    multiplier = skill_system.wexp_multiplier(unit, mark.defender)
                if mark.defender and mark.defender.is_dying and DB.constants.value('kill_wexp'):
                    func(action.GainWexp(unit, item, (wexp * 2) * multiplier))
                else:
                    func(action.GainWexp(unit, item, wexp * multiplier))
        elif marks:
            if target:
                multiplier = skill_system.wexp_multiplier(unit, target) * skill_system.enemy_wexp_multiplier(target, unit)
            else:
                multiplier = skill_system.wexp_multiplier(unit, target)
            if DB.constants.value('kill_wexp') and any(mark.defender and mark.defender.is_dying for mark in marks):
                func(action.GainWexp(unit, item, (wexp * 2) * multiplier))
            else:
                func(action.GainWexp(unit, item, wexp * multiplier))

    def handle_mana(self, all_units):
        # Attacker mana
        total_mana = 0
        for unit in all_units:
            if unit is not self.attacker:
                total_mana += skill_system.mana(self.full_playback, self.attacker, self.main_item, unit)
        # This is being left open - if something effects mana gain it will be done here
        if self.attacker.team == 'player':
            game.mana_instance.append((self.attacker, total_mana))
        else:
            action.do(action.ChangeMana(self.attacker, total_mana))

        # Defender mana
        if self.defender:
            # This is being left open - if something effects mana gain it will be done here
            mana_gain = skill_system.mana(self.full_playback, self.defender, self.def_item, self.attacker)
            if self.defender.team == 'player':
                game.mana_instance.append((self.defender, mana_gain))
            else:
                action.do(action.ChangeMana(self.defender, mana_gain))

    def handle_exp(self, combat_object=None):
        # handle exp
        if self.attacker.team == 'player' and not self.attacker.is_dying:
            exp = self.calculate_exp(self.attacker, self.main_item)

            if self.defender and (skill_system.check_ally(self.attacker, self.defender) or 'Tile' in self.defender.tags):
                exp = int(utils.clamp(exp, 0, 100))
            else:
                exp = int(utils.clamp(exp, DB.constants.value('min_exp'), 100))

            if DB.constants.value('pairup') and self.main_item:
                self.handle_paired_exp(self.attacker, combat_object)

            if (self.alerts and exp > 0) or exp + self.attacker.exp >= 100:
                game.exp_instance.append((self.attacker, exp, combat_object, 'init'))
                game.state.change('exp')
                game.ai.end_skip()
            elif not self.alerts and exp > 0:
                action.do(action.GainExp(self.attacker, exp))

        elif self.defender and self.defender.team == 'player' and not self.defender.is_dying:
            exp = self.calculate_exp(self.defender, self.def_item)
            exp = int(utils.clamp(exp, DB.constants.value('min_exp'), 100))

            if DB.constants.value('pairup') and self.def_item:
                self.handle_paired_exp(self.defender, combat_object)

            if (self.alerts and exp > 0) or exp + self.defender.exp >= 100:
                game.exp_instance.append((self.defender, exp, combat_object, 'init'))
                game.state.change('exp')
                game.ai.end_skip()
            elif not self.alerts and exp > 0:
                action.do(action.GainExp(self.defender, exp))

    def handle_paired_exp(self, leader_unit, combat_object=None):
        partner = None
        if leader_unit.strike_partner:
            # Get half the exp you would normally get
            partner = leader_unit.strike_partner
            exp = self.calculate_exp(partner, partner.get_weapon())
            exp = int(utils.clamp(exp, 0, 100))
            exp //= 2
        elif leader_unit.traveler:
            # Just get a base amount of exp
            partner = game.get_unit(leader_unit.traveler)
            exp = self.calculate_guard_stance_exp(partner, partner.get_weapon())
            exp = int(utils.clamp(exp, 0, 100))
        if partner:
            if (self.alerts and exp > 0) or exp + partner.exp >= 100:
                game.exp_instance.append((partner, exp, combat_object, 'init'))
                game.state.change('exp')
                game.ai.end_skip()
            elif not self.alerts and exp > 0:
                action.do(action.GainExp(partner, exp))

    def get_exp(self, attacker, item, defender) -> int:
        exp = item_system.exp(self.full_playback, attacker, item, defender)
        exp *= skill_system.exp_multiplier(attacker, defender)
        if defender:
            exp *= skill_system.enemy_exp_multiplier(defender, attacker)
            if defender.is_dying:
                exp *= float(DB.constants.value('kill_multiplier'))
                if 'Boss' in defender.tags:
                    exp += int(DB.constants.value('boss_bonus'))
        return exp

    def calculate_exp(self, unit, item):
        """
        If you score a hit or a crit,
        or deal damage to an enemy
        get exp
        """
        marks = self.get_from_full_playback('mark_hit')
        marks += self.get_from_full_playback('mark_crit')
        marks = [mark for mark in marks if mark.attacker == unit]
        damage_marks = self.get_from_full_playback('damage_hit')
        damage_marks = [mark for mark in damage_marks if mark.attacker == unit and skill_system.check_enemy(unit, mark.defender)]
        total_exp = 0
        all_defenders = set()
        for mark in marks:
            if mark.defender in all_defenders:
                continue  # Don't double count defenders
            all_defenders.add(mark.defender)
            exp = self.get_exp(mark.attacker, item, mark.defender)
            total_exp += exp
        for mark in damage_marks:
            if mark.defender in all_defenders:
                continue  # Don't double count defenders
            all_defenders.add(mark.defender)
            exp = self.get_exp(mark.attacker, item, mark.defender)
            total_exp += exp

        return total_exp

    def calculate_guard_stance_exp(self, unit, item):
        """
        If you blocked an attacker get exp
        """
        # if not item:  #
            # return 0
        marks = self.get_from_full_playback('mark_hit')
        marks = [mark for mark in marks if mark.guard_hit]
        total_exp = 0
        for mark in marks:
            exp = 10
            # exp = self.get_exp(game.get_unit(defender.traveler), item, attacker)
            total_exp += exp

        return total_exp

    def handle_supports(self, all_units) -> list:
        """
        Returns a list of pairs of units that gained support together
        """
        pairs = []
        if game.game_vars.get('_supports'):
            # End combat supports
            for unit in all_units:
                if unit is self.attacker and self.defender and self.defender is not self.attacker:
                    pairs += supports.increment_end_combat_supports(self.attacker, self.defender)
                else:
                    pairs += supports.increment_end_combat_supports(unit)
            enemies = all_units.copy()
            enemies.remove(self.attacker)
            for unit in enemies:
                if supports.increment_interact_supports(self.attacker, unit):
                    pairs.append((self.attacker, unit))

            if DB.constants.value('pairup'):
                for unit in all_units:
                    if unit.traveler:
                        if supports.increment_pairup_supports(unit, unit.traveler):
                            pairs.append((unit, unit.traveler))
                    if unit.strike_partner:
                        if supports.increment_pairup_supports(unit, unit.strike_partner):
                            pairs.append((unit, unit.strike_partner))
        return pairs

    def handle_support_pairs(self, pairs):
        pass

    def handle_records(self, full_playback, all_units):
        miss_marks = self.get_from_full_playback('mark_miss')
        hit_marks = self.get_from_full_playback('mark_hit')
        crit_marks = self.get_from_full_playback('mark_crit')

        for mark in miss_marks:
            action.do(action.UpdateRecords('miss', (mark.attacker.nid, mark.defender.nid)))

        for mark in hit_marks:
            action.do(action.UpdateRecords('hit', (mark.attacker.nid, mark.defender.nid)))

        for mark in crit_marks:
            action.do(action.UpdateRecords('crit', (mark.attacker.nid, mark.defender.nid)))

        damage_marks = self.get_from_full_playback('damage_hit')
        damage_marks += self.get_from_full_playback('damage_crit')
        for mark in damage_marks:
            action.do(action.UpdateRecords('damage', (mark.attacker.nid, mark.defender.nid, mark.item.nid, mark.damage, mark.true_damage, 'crit' if mark.nid == 'damage_crit' else 'hit')))

        heal_marks = self.get_from_full_playback('heal_hit')
        for mark in heal_marks:
            action.do(action.UpdateRecords('heal', (mark.attacker.nid, mark.defender.nid, mark.item.nid, mark.damage, mark.true_damage, 'hit')))

        for mark in self.full_playback:
            if mark.nid in ('mark_miss', 'mark_hit', 'mark_crit'):
                if mark.defender.is_dying:
                    act = action.UpdateRecords('kill', (mark.attacker.nid, mark.defender.nid))
                    action.do(act)
                    if mark.defender.team == 'player':  # If player is dying, save this result even if we turnwheel back
                        act = action.UpdateRecords('death', (mark.attacker.nid, mark.defender.nid))
                        act.do()
                if mark.attacker.is_dying:
                    act = action.UpdateRecords('kill', (mark.defender.nid, mark.attacker.nid))
                    action.do(act)
                    if mark.defender.team == 'player':  # If player is dying, save this result even if we turnwheel back
                        act = action.UpdateRecords('death', (mark.defender.nid, mark.attacker.nid))
                        act.do()

    def handle_death(self, units):
        if not self.arena_combat:
            for unit in units:
                if unit.is_dying:
                    game.state.change('dying')
                    break

        for unit in units:
            if unit.is_dying:
                killer = game.records.get_killer(unit.nid, game.level.nid if game.level else None)
                if killer:
                    killer = game.get_unit(killer)
                game.events.trigger(triggers.UnitDeath(unit, killer, unit.position))
                skill_system.on_death(unit)

        if self.arena_combat:
            for unit in units:
                if unit.is_dying:
                    game.death.force_death(unit)
