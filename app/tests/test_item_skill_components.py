import unittest
from typing import Any, Callable, List
from unittest.mock import MagicMock, patch

from app.data.database.item_components import ItemComponent
from app.data.database.skill_components import SkillComponent
from app.engine.component_system import source_generator
from app.engine.item_components.base_components import Spell, Weapon
from app.engine.item_components.advanced_components import MultiTarget
from app.engine.item_components.exp_components import Wexp
from app.engine.skill_components.base_components import CanUseWeaponType, CannotUseWeaponType, ChangeAI, ChangeBuyPrice, IgnoreAlliances, Locktouch
from app.engine.skill_components.combat_components import DamageMultiplier
from app.engine.skill_components.combat2_components import Vantage
from app.engine.skill_components.dynamic_components import DynamicDamage
from app.engine.skill_components.aesthetic_components import BattleAnimMusic, UnitFlickeringTint


class ItemSkillComponentTests(unittest.TestCase):
    def setUp(self):
        source_generator.generate_component_system_source()

    def tearDown(self):
        pass

    def test_item_components(self):
        # Test that all item components have
        # unique nids
        item_components = ItemComponent.__subclasses__()
        nids = {component.nid for component in item_components}
        for component in item_components:
            nid = component.nid
            self.assertIn(nid, nids)
            nids.remove(nid)

    def test_skill_components(self):
        # Test that all skill components have
        # unique nids
        skill_components = SkillComponent.__subclasses__()
        nids = {component.nid for component in skill_components}
        for component in skill_components:
            nid = component.nid
            self.assertIn(nid, nids)
            nids.remove(nid)

    def _test_skill_hook_with_components(self, components: List[SkillComponent], call_hook: Callable[[], Any], expected_result: Any):
        mock_skill = MagicMock()
        mock_skill.components = components
        mock_unit = MagicMock()
        mock_unit.skills = [mock_skill]
        mock_unit.ai = 'Pursue'
        mock_unit.team = 'player'
        self.assertEqual(expected_result, call_hook(mock_unit))

    def test_skill_hooks_set_union_behavior(self):
        from app.engine import skill_system
        self._test_skill_hook_with_components([], lambda unit: skill_system.usable_wtypes(unit), set())
        self._test_skill_hook_with_components([CanUseWeaponType(None), CanUseWeaponType("Sword"), CanUseWeaponType("Lance")], lambda unit: skill_system.usable_wtypes(unit), set(["Sword", "Lance"]))
        self._test_skill_hook_with_components([CanUseWeaponType("Sword"), CanUseWeaponType("Lance"), CanUseWeaponType("Lance")], lambda unit: skill_system.usable_wtypes(unit), set(["Sword", "Lance"]))
        
    def test_skill_hooks_all_false_priority(self):
        from app.engine import skill_system
        self._test_skill_hook_with_components([], lambda unit: skill_system.vantage(unit), False)
        self._test_skill_hook_with_components([Vantage()], lambda unit: skill_system.vantage(unit), True)
        mock_component = MagicMock()
        mock_component.vantage = MagicMock(return_value=False)
        self._test_skill_hook_with_components([Vantage(), mock_component], lambda unit: skill_system.vantage(unit), False)
        
    def test_skill_hooks_all_true_priority(self):
        from app.engine import skill_system
        mock_component_1 = MagicMock()
        mock_component_1.available = MagicMock(return_value=False)
        mock_component_2 = MagicMock()
        mock_component_2.available = MagicMock(return_value=True)
        mock_arg = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.available(unit, mock_arg), True)
        self._test_skill_hook_with_components([mock_component_1], lambda unit: skill_system.available(unit, mock_arg), False)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.available(unit, mock_arg), False)
        
    def test_skill_hooks_any_false_priority(self):
        from app.engine import skill_system
        mock_arg = MagicMock()
        mock_component = MagicMock()
        mock_component.can_unlock = MagicMock(return_value=False)
        self._test_skill_hook_with_components([], lambda unit: skill_system.can_unlock(unit, mock_arg), False)
        self._test_skill_hook_with_components([Locktouch()], lambda unit: skill_system.can_unlock(unit, mock_arg), True)
        self._test_skill_hook_with_components([Locktouch(), mock_component], lambda unit: skill_system.can_unlock(unit, mock_arg), True)
        
    def test_skill_hooks_unique_default(self):
        from app.engine import skill_system
        self._test_skill_hook_with_components([], lambda unit: skill_system.change_ai(unit), 'Pursue')
        self._test_skill_hook_with_components([ChangeAI('Guard'), ChangeAI('Defend')], lambda unit: skill_system.change_ai(unit), 'Defend')
        self._test_skill_hook_with_components([ChangeAI('Defend'), ChangeAI('Guard')], lambda unit: skill_system.change_ai(unit), 'Guard')
        
    def test_skill_hooks_unique_default_item(self):
        from app.engine import skill_system
        mock_item = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.modify_buy_price(unit, mock_item), 1.0)
        self._test_skill_hook_with_components([ChangeBuyPrice(2.0), ChangeBuyPrice(0.5)], lambda unit: skill_system.modify_buy_price(unit, mock_item), 0.5)
        self._test_skill_hook_with_components([ChangeBuyPrice(0.5), ChangeBuyPrice(2.0)], lambda unit: skill_system.modify_buy_price(unit, mock_item), 2.0)
        
    def test_skill_hooks_accumulate_item(self):
        from app.engine import skill_system
        mock_item = MagicMock()
        mock_component_1 = MagicMock()
        mock_component_1.modify_damage = MagicMock(return_value=1)
        mock_component_2 = MagicMock()
        mock_component_2.modify_damage = MagicMock(return_value=2)
        self._test_skill_hook_with_components([], lambda unit: skill_system.modify_damage(unit, mock_item), 0)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.modify_damage(unit, mock_item), 3)
        self._test_skill_hook_with_components([mock_component_2, mock_component_1], lambda unit: skill_system.modify_damage(unit, mock_item), 3)
        
    def test_skill_hooks_accumulate(self):
        from app.engine import skill_system
        mock_item = MagicMock()
        mock_target = MagicMock()
        mock_info = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.dynamic_damage(unit, mock_item, mock_target, 'attack', mock_info, 1), 0)
        self._test_skill_hook_with_components([DynamicDamage("1"), DynamicDamage("2")], lambda unit: skill_system.dynamic_damage(unit, mock_item, mock_target, 'attack', mock_info, 1), 3)
        self._test_skill_hook_with_components([DynamicDamage("2"), DynamicDamage("1")], lambda unit: skill_system.dynamic_damage(unit, mock_item, mock_target, 'attack', mock_info, 1), 3)
        
    def test_skill_hooks_multiply(self):
        from app.engine import skill_system
        mock_item = MagicMock()
        mock_target = MagicMock()
        mock_info = MagicMock()
        mock_mode = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.damage_multiplier(unit, mock_item, mock_target, mock_mode, mock_info, 0), 1)
        self._test_skill_hook_with_components([DamageMultiplier(3.0), DamageMultiplier(1.5)], lambda unit: skill_system.damage_multiplier(unit, mock_item, mock_target, mock_mode, mock_info, 0), 4.5)
        self._test_skill_hook_with_components([DamageMultiplier(-2), DamageMultiplier(1.5)], lambda unit: skill_system.damage_multiplier(unit, mock_item, mock_target, mock_mode, mock_info, 0), -3)
        
    def test_skill_hooks_unique_default_target(self):
        from app.engine import skill_system
        mock_target = MagicMock()
        mock_target.team = 'other'
        self._test_skill_hook_with_components([], lambda unit: skill_system.check_ally(unit, mock_target), True)
        self._test_skill_hook_with_components([IgnoreAlliances()], lambda unit: skill_system.check_ally(unit, mock_target), False)
        
    def test_skill_hooks_unique_no_default(self):
        from app.engine import skill_system
        mock_playback = MagicMock()
        mock_item = MagicMock()
        mock_target = MagicMock()
        mock_mode = MagicMock()
        self._test_skill_hook_with_components([], lambda unit: skill_system.battle_music(mock_playback, unit, mock_item, mock_target, mock_mode), None)
        self._test_skill_hook_with_components([BattleAnimMusic('FillerBong'), BattleAnimMusic('FillerSong')], lambda unit: skill_system.battle_music(mock_playback, unit, mock_item, mock_target, mock_mode), 'FillerSong')
        
    def test_skill_hooks_unique_event(self):
        from app.engine import skill_system
        self._test_skill_hook_with_components([], lambda unit: skill_system.on_death(unit), None)
        mock_component_1 = MagicMock()
        mock_component_1.on_death = MagicMock()
        mock_component_1.on_add_item = MagicMock()
        mock_component_1.start_combat = MagicMock()
        mock_component_1.start_sub_combat = MagicMock()
        mock_component_1.after_strike = MagicMock()
        mock_component_1.on_upkeep = MagicMock(('Fail', 'Fail'))
        mock_component_1.on_add_item = MagicMock()
        mock_component_2 = MagicMock()
        mock_component_2.on_death = MagicMock()
        mock_component_2.on_add_item = MagicMock()
        mock_component_2.start_combat = MagicMock()
        mock_component_2.start_sub_combat = MagicMock()
        mock_component_2.after_strike = MagicMock()
        mock_component_2.on_upkeep = MagicMock(return_value=('Test', 'Test'))
        mock_component_2.on_add_item = MagicMock()
        mock_component_3 = MagicMock()
        mock_component_3.start_combat = MagicMock()
        mock_component_3.start_combat_unconditional = MagicMock()
        mock_component_3.condition = MagicMock(return_value=False)
        mock_component_3.ignore_conditional = None
        mock_arg = 'Test'
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.on_death(unit), None)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.on_add_item(unit, mock_arg), None)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.on_upkeep(mock_arg, mock_arg, unit), None)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.start_sub_combat(mock_arg, mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg), None)
        self._test_skill_hook_with_components([mock_component_1, mock_component_2], lambda unit: skill_system.after_strike(mock_arg, mock_arg, unit, mock_arg, mock_arg, mock_arg, mock_arg, mock_arg), None)
        # has unconditional
        self._test_skill_hook_with_components([mock_component_1, mock_component_2, mock_component_3], lambda unit: skill_system.start_combat(mock_arg, unit, mock_arg, mock_arg, mock_arg), None)
        self.assertTrue(mock_component_1.on_death.called)
        self.assertTrue(mock_component_2.on_death.called)
        self.assertTrue(mock_component_1.on_add_item.called)
        self.assertTrue(mock_component_2.on_add_item.called)
        self.assertTrue(mock_component_1.start_combat.called)
        self.assertTrue(mock_component_2.start_combat.called)
        self.assertTrue(mock_component_1.start_sub_combat.called)
        self.assertTrue(mock_component_2.start_sub_combat.called)
        self.assertTrue(mock_component_1.after_strike.called)
        self.assertTrue(mock_component_2.after_strike.called)
        # unconditional tests
        self.assertFalse(mock_component_3.start_combat.called)
        self.assertTrue(mock_component_3.start_combat_unconditional.called)
        
    def _test_item_hook_with_components(self, components: List[ItemComponent], call_hook: Callable[[], Any], expected_result: Any):
        mock_item = MagicMock()
        mock_item.components = components
        mock_unit = MagicMock()
        self.assertEqual(expected_result, call_hook(mock_unit, mock_item))
        
    def test_item_hooks_weapon_resolution_logic(self):
        from app.engine import item_system
        # is_weapon
        self._test_item_hook_with_components([Weapon()], lambda unit, item: item_system.is_weapon(unit, item), True)
        self._test_item_hook_with_components([Spell()], lambda unit, item: item_system.is_weapon(unit, item), False)
        self._test_item_hook_with_components([Spell(), Weapon()], lambda unit, item: item_system.is_weapon(unit, item), False)
        self._test_item_hook_with_components([], lambda unit, item: item_system.is_weapon(unit, item), False)

if __name__ == '__main__':
    unittest.main()
