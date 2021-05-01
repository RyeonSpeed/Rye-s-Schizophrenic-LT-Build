from app.data.skill_components import SkillComponent
from app.data.components import Type

from app.utilities import utils
from app.engine import action
from app.engine.game_state import game

class StatChange(SkillComponent):
    nid = 'stat_change'
    desc = "Gives stat bonuses"
    tag = 'combat'

    expose = (Type.Dict, Type.Stat)
    value = []

    def stat_change(self, unit):
        return {stat[0]: stat[1] for stat in self.value}

    def tile_def(self):
        total_value = 0
        for stat_nid, stat_value in self.value:
            if stat_nid == 'DEF':
                total_value += stat_value
        return total_value

class StatMultiplier(SkillComponent):
    nid = 'stat_multiplier'
    desc = "Gives stat bonuses"
    tag = 'combat'

    expose = (Type.FloatDict, Type.Stat)
    value = []

    def stat_change(self, unit):
        return {stat[0]: int((stat[1]-1)*unit.stats[stat[0]]) for stat in self.value}

class GrowthChange(SkillComponent):
    nid = 'growth_change'
    desc = "Gives growth rate % bonuses"
    tag = 'advanced'

    expose = (Type.Dict, Type.Stat)
    value = []

    def growth_change(self, unit):
        return {stat[0]: stat[1] for stat in self.value}

class Damage(SkillComponent):
    nid = 'damage'
    desc = "Gives +X damage"
    tag = 'combat'

    expose = Type.Int
    value = 3

    def modify_damage(self, unit, item):
        return self.value

class EvalDamage(SkillComponent):
    nid = 'eval_damage'
    desc = "Gives +X damage solved using evaluate"
    tag = 'combat'

    expose = Type.String

    def modify_damage(self, unit, item):
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, item=item))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
        return 0 

class Resist(SkillComponent):
    nid = 'resist'
    desc = "Gives +X damage resist"
    tag = 'combat'

    expose = Type.Int
    value = 2

    def modify_resist(self, unit, item_to_avoid):
        return self.value

class Hit(SkillComponent):
    nid = 'hit'
    desc = "Gives +X accuracy"
    tag = 'combat'

    expose = Type.Int
    value = 15

    def modify_accuracy(self, unit, item):
        return self.value

class Avoid(SkillComponent):
    nid = 'avoid'
    desc = "Gives +X avoid"
    tag = 'combat'

    expose = Type.Int
    value = 20

    def modify_avoid(self, unit, item_to_avoid):
        return self.value

    def tile_avoid(self):
        return self.value

class Crit(SkillComponent):
    nid = 'crit'
    desc = "Gives +X crit"
    tag = 'combat'

    expose = Type.Int
    value = 30

    def modify_crit_accuracy(self, unit, item):
        return self.value

class CritAvoid(SkillComponent):
    nid = 'crit_avoid'
    desc = "Gives +X crit avoid"
    tag = 'combat'

    expose = Type.Int
    value = 10

    def modify_crit_avoid(self, unit, item_to_avoid):
        return self.value

class AttackSpeed(SkillComponent):
    nid = 'attack_speed'
    desc = "Gives +X attack speed"
    tag = 'combat'

    expose = Type.Int
    value = 4

    def modify_attack_speed(self, unit, item):
        return self.value

class DefenseSpeed(SkillComponent):
    nid = 'defense_speed'
    desc = "Gives +X defense speed"
    tag = 'combat'

    expose = Type.Int
    value = 4

    def modify_defense_speed(self, unit, item_to_avoid):
        return self.value

class DynamicDamage(SkillComponent):
    nid = 'dynamic_damage'
    desc = "Gives +X damage solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_damage(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DynamicResist(SkillComponent):
    nid = 'dynamic_resist'
    desc = "Gives +X resist solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_resist(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DynamicAccuracy(SkillComponent):
    nid = 'dynamic_accuracy'
    desc = "Gives +X hit solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_accuracy(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DynamicAvoid(SkillComponent):
    nid = 'dynamic_avoid'
    desc = "Gives +X avoid solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_avoid(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DynamicCritAccuracy(SkillComponent):
    nid = 'dynamic_crit_accuracy'
    desc = "Gives +X crit solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_crit_accuracy(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DynamicCritAvoid(SkillComponent):
    nid = 'dynamic_crit_avoid'
    desc = "Gives +X crit avoid solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_crit_avoid(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DynamicAttackSpeed(SkillComponent):
    nid = 'dynamic_attack_speed'
    desc = "Gives +X attack speed solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_attack_speed(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DynamicDefenseSpeed(SkillComponent):
    nid = 'dynamic_defense_speed'
    desc = "Gives +X defense speed solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_defense_speed(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DynamicMultiattacks(SkillComponent):
    nid = 'dynamic_multiattacks'
    desc = "Gives +X extra attacks per phase solved dynamically"
    tag = 'combat'

    expose = Type.String

    def dynamic_multiattacks(self, unit, item, target, mode) -> int:
        from app.engine import evaluate
        try:
            return int(evaluate.evaluate(self.value, unit, target, item, mode=mode, skill=self.skill))
        except:
            print("Couldn't evaluate %s conditional" % self.value)
            return 0

class DamageMultiplier(SkillComponent):
    nid = 'damage_multiplier'
    desc = "Multiplies damage given by a fraction"
    tag = 'combat'

    expose = Type.Float
    value = 0.5

    def damage_multiplier(self, unit, item, target, mode):
        return self.value

class ResistMultiplier(SkillComponent):
    nid = 'resist_multiplier'
    desc = "Multiplies damage taken by a fraction"
    tag = 'combat'

    expose = Type.Float
    value = 0.5

    def resist_multiplier(self, unit, item, target, mode):
        return self.value

class GiveStatusAfterCombat(SkillComponent):
    nid = 'give_status_after_combat'
    desc = "Gives a status to target after combat"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        from app.engine import skill_system
        if target and skill_system.check_enemy(unit, target):
            action.do(action.AddSkill(target, self.value, unit))
            action.do(action.TriggerCharge(unit, self.skill))

class GiveStatusAfterAttack(SkillComponent):
    nid = 'give_status_after_attack'
    desc = "Gives a status to target after attacking the target"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        mark_playbacks = [p for p in playback if p[0] in ('mark_miss', 'mark_hit', 'mark_crit')]
        if target and any(p[3] == unit for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(target, self.value, unit))
            action.do(action.TriggerCharge(unit, self.skill))

class GainSkillAfterKill(SkillComponent):
    nid = 'gain_skill_after_kill'
    desc = "Gives a skill to user after a kill"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        if target and target.get_hp() <= 0:
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))

class GainSkillAfterAttacking(SkillComponent):
    nid = 'gain_skill_after_attack'
    desc = "Gives a skill to user after an attack"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        mark_playbacks = [p for p in playback if p[0] in ('mark_miss', 'mark_hit', 'mark_crit')]
        if any(p[3] == unit for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))

class GainSkillAfterActiveKill(SkillComponent):
    nid = 'gain_skill_after_active_kill'
    desc = "Gives a skill after a kill on personal phase"
    tag = 'combat2'

    expose = Type.Skill

    def end_combat(self, playback, unit, item, target, mode):
        mark_playbacks = [p for p in playback if p[0] in ('mark_miss', 'mark_hit', 'mark_crit')]
        if target and target.get_hp() <= 0 and any(p[3] == unit for p in mark_playbacks):  # Unit is overall attacker
            action.do(action.AddSkill(unit, self.value))
            action.do(action.TriggerCharge(unit, self.skill))

class Miracle(SkillComponent):
    nid = 'miracle'
    desc = "Unit cannot be reduced below 1 HP"
    tag = 'combat2'

    def cleanup_combat(self, playback, unit, item, target, mode):
        if unit.get_hp() <= 0:
            action.do(action.SetHP(unit, 1))
            game.death.miracle(unit)
            action.do(action.TriggerCharge(unit, self.skill))

class IgnoreDamage(SkillComponent):
    nid = 'ignore_damage'
    desc = "Unit will ignore all damage"
    tag = 'combat2'

    def after_hit(self, actions, playback, unit, item, target, mode):
        # Remove any acts that reduce my HP!
        did_something = False
        for act in reversed(actions):
            if isinstance(act, action.ChangeHP) and act.num < 0:
                actions.remove(act)
                did_something = True

        if did_something:
            actions.append(action.TriggerCharge(unit, self.skill))

class LiveToServe(SkillComponent):
    nid = 'live_to_serve'
    desc = "Unit will be healed X%% of amount healed"
    tag = 'combat2'

    expose = Type.Float
    value = 1.0

    def after_hit(self, actions, playback, unit, item, target, mode):
        total_amount_healed = 0
        playbacks = [p for p in playback if p[0] == 'heal_hit' and p[1] == self]
        for p in playbacks:
            total_amount_healed += p[4]

        amount = int(total_amount_healed * self.value)
        if amount > 0:
            actions.append(action.ChangeHP(unit, amount))
            actions.append(action.TriggerCharge(unit, self.skill))

class Lifelink(SkillComponent):
    nid = 'lifelink'
    desc = "Heals user %% of damage dealt"
    tag = 'combat2'

    expose = Type.Float
    value = 0.5

    def after_hit(self, actions, playback, unit, item, target, mode):
        total_damage_dealt = 0
        playbacks = [p for p in playback if p[0] in ('damage_hit', 'damage_crit') and p[1] == unit]
        for p in playbacks:
            total_damage_dealt += p[5]

        damage = utils.clamp(total_damage_dealt, 0, target.get_hp())
        true_damage = int(damage * self.value)
        actions.append(action.ChangeHP(unit, true_damage))

        playback.append(('heal_hit', unit, item, unit, true_damage, true_damage))

        actions.append(action.TriggerCharge(unit, self.skill))

class LimitMaximumRange(SkillComponent):
    nid = 'limit_maximum_range'
    desc = "limits unit's maximum allowed range"
    tag = 'combat2'

    expose = Type.Int
    value = 1

    def limit_maximum_range(self, unit, skill):
        return self.value

class ModifyMaximumRange(SkillComponent):
    nid = 'modify_maximum_range'
    desc = "modifies unit's maximum allowed range"
    tag = 'combat2'

    expose = Type.Int
    value = 1

    def modify_maximum_range(self, unit, skill):
        return self.value

class GuaranteedCrit(SkillComponent):
    nid = 'guaranteed_crit'
    desc = "Unit will have chance to crit even if crit constant is turned off"
    tag = 'combat2'

    def crit_anyway(self, unit):
        return True
