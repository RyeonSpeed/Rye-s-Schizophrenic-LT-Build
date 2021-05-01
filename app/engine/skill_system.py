class Defaults():
    @staticmethod
    def can_select(unit) -> bool:
        return unit.team == 'player'

    @staticmethod
    def check_ally(unit1, unit2) -> bool:
        if unit1 is unit2:
            return True
        elif unit1.team == 'player' or unit1.team == 'other':
            return unit2.team == 'player' or unit2.team == 'other'
        else:
            return unit2.team == unit1.team
        return False

    @staticmethod
    def check_enemy(unit1, unit2) -> bool:
        if unit1.team == 'player' or unit1.team == 'other':
            return not (unit2.team == 'player' or unit2.team == 'other')
        else:
            return not unit2.team == unit1.team
        return True

    @staticmethod
    def can_trade(unit1, unit2) -> bool:
        return unit2.position and unit1.team == unit2.team and check_ally(unit1, unit2)

    @staticmethod
    def exp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def enemy_exp_multiplier(unit1, unit2) -> float:
        return 1.0

    @staticmethod
    def steal_icon(unit1, unit2) -> bool:
        return False

    @staticmethod
    def has_canto(unit1, unit2) -> bool:
        return False

    @staticmethod
    def limit_maximum_range(unit, item) -> int:
        return 1000

    @staticmethod
    def modify_maximum_range(unit, item) -> int:
        return 0

    @staticmethod
    def movement_type(unit):
        return None

    @staticmethod
    def sight_range(unit):
        return 0

    @staticmethod
    def empower_splash(unit):
        return 0

    @staticmethod
    def modify_buy_price(unit, item) -> float:
        return 1.0

    @staticmethod
    def modify_sell_price(unit, item) -> float:
        return 1.0

    @staticmethod
    def damage_formula(unit) -> str:
        return 'DAMAGE'

    @staticmethod
    def resist_formula(unit) -> str:
        return 'DEFENSE'

    @staticmethod
    def accuracy_formula(unit) -> str:
        return 'HIT'

    @staticmethod
    def avoid_formula(unit) -> str:
        return 'AVOID'

    @staticmethod
    def crit_accuracy_formula(unit) -> str:
        return 'CRIT_HIT'

    @staticmethod
    def crit_avoid_formula(unit) -> str:
        return 'CRIT_AVOID'

    @staticmethod
    def attack_speed_formula(unit) -> str:
        return 'ATTACK_SPEED'

    @staticmethod
    def defense_speed_formula(unit) -> str:
        return 'DEFENSE_SPEED'

# Takes in unit, returns False if not present
# All default hooks are exclusive
formula = ('damage_formula', 'resist_formula', 'accuracy_formula', 'avoid_formula', 
           'crit_accuracy_formula', 'crit_avoid_formula', 'attack_speed_formula', 'defense_speed_formula')
default_behaviours = (
    'pass_through', 'vantage', 'ignore_terrain', 'crit_anyway',
    'ignore_region_status', 'no_double', 'def_double', 'alternate_splash',
    'ignore_rescue_penalty', 'ignore_forced_movement', 'distant_counter')
# Takes in unit, returns default value
exclusive_behaviours = ('can_select', 'movement_type', 'sight_range', 'empower_splash')
exclusive_behaviours += formula
# Takes in unit and item, returns default value
item_behaviours = ('modify_buy_price', 'modify_sell_price', 'limit_maximum_range', 'modify_maximum_range')
# Takes in unit and target, returns default value
targeted_behaviours = ('check_ally', 'check_enemy', 'can_trade', 'exp_multiplier', 'enemy_exp_multiplier', 'steal_icon', 'has_canto')
# Takes in unit, item returns bonus
modify_hooks = (
    'modify_damage', 'modify_resist', 'modify_accuracy', 'modify_avoid', 
    'modify_crit_accuracy', 'modify_crit_avoid', 'modify_attack_speed', 
    'modify_defense_speed')
# Takes in unit, item, target, mode, returns bonus
dynamic_hooks = ('dynamic_damage', 'dynamic_resist', 'dynamic_accuracy', 'dynamic_avoid', 
                 'dynamic_crit_accuracy', 'dynamic_crit_avoid', 'dynamic_attack_speed', 'dynamic_defense_speed',
                 'dynamic_multiattacks')
# Takes in unit, item, target, mode returns bonus
multiply_hooks = ('damage_multiplier', 'resist_multiplier')

# Takes in unit
simple_event_hooks = ('on_death',)
# Takes in playback, unit, item, target
combat_event_hooks = ('start_combat', 'cleanup_combat', 'end_combat', 'pre_combat', 'post_combat', 'test_on', 'test_off')
# Takes in actions, playback, unit, item, target, mode
subcombat_event_hooks = ('after_hit', 'after_take_hit')
# Takes in unit, item
item_event_hooks = ('on_add_item', 'on_remove_item', 'on_equip_item', 'on_unequip_item')

def condition(skill, unit) -> bool:
    for component in skill.components:
        if component.defines('condition'):
            if not component.condition(unit):
                return False
    return True

for behaviour in default_behaviours:
    func = """def %s(unit):
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit):
                                  return component.%s(unit)
                  return False""" \
        % (behaviour, behaviour, behaviour)
    exec(func)

for behaviour in exclusive_behaviours:
    func = """def %s(unit):
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit):
                                  return component.%s(unit)
                  return Defaults.%s(unit)""" \
        % (behaviour, behaviour, behaviour, behaviour)
    exec(func)

for behaviour in targeted_behaviours:
    func = """def %s(unit1, unit2):
                  for skill in unit1.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit1):
                                  return component.%s(unit1, unit2)
                  return Defaults.%s(unit1, unit2)""" \
        % (behaviour, behaviour, behaviour, behaviour)
    exec(func)

for behaviour in item_behaviours:
    func = """def %s(unit, item):
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit):
                                  return component.%s(unit, item)
                  return Defaults.%s(unit, item)""" \
        % (behaviour, behaviour, behaviour, behaviour)
    exec(func)

for hook in modify_hooks:
    func = """def %s(unit, item):
                  val = 0
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit):
                                  val += component.%s(unit, item)
                  return val""" \
        % (hook, hook, hook)
    exec(func)

for hook in dynamic_hooks:
    func = """def %s(unit, item, target, mode):
                  val = 0
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit):
                                  val += component.%s(unit, item, target, mode)
                  return val""" \
        % (hook, hook, hook)
    exec(func)

for hook in multiply_hooks:
    func = """def %s(unit, item, target, mode):
                  val = 1
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit):
                                  val *= component.%s(unit, item, target, mode)
                  return val""" \
        % (hook, hook, hook)
    exec(func)

for hook in simple_event_hooks:
    func = """def %s(unit):
                  for skill in unit.skills: 
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit):
                                  component.%s(unit)""" \
        % (hook, hook, hook)
    exec(func)

for hook in combat_event_hooks:
    func = """def %s(playback, unit, item, target, mode):
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              if component.ignore_conditional or condition(skill, unit):
                                  component.%s(playback, unit, item, target, mode)""" \
        % (hook, hook, hook)
    exec(func)

for hook in subcombat_event_hooks:
    func = """def %s(actions, playback, unit, item, target, mode):
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              component.%s(actions, playback, unit, item, target, mode)""" \
        % (hook, hook, hook)
    exec(func)

for hook in item_event_hooks:
    func = """def %s(unit, item):
                  for skill in unit.skills:
                      for component in skill.components:
                          if component.defines('%s'):
                              component.%s(unit, item)""" \
        % (hook, hook, hook)
    exec(func)

def available(unit, item) -> bool:
    """
    If any hook reports false, then it is false
    """
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('available'):
                if component.ignore_conditional or condition(skill, unit):
                    if not component.available(unit, item):
                        return False
    return True

def stat_change(unit, stat) -> int:
    bonus = 0
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('stat_change'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.stat_change(unit)
                    bonus += d.get(stat, 0)
    return bonus

def growth_change(unit, stat) -> int:
    bonus = 0
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('growth_change'):
                if component.ignore_conditional or condition(skill, unit):
                    d = component.growth_change(unit)
                    bonus += d.get(stat, 0)
    return bonus

def can_unlock(unit, region) -> bool:
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('can_unlock'):
                if component.ignore_conditional or condition(skill, unit):
                    if component.can_unlock(unit, region):
                        return True
    return False

def on_upkeep(actions, playback, unit) -> tuple:  # actions, playback
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('on_upkeep'):
                if component.ignore_conditional or condition(skill, unit):
                    component.on_upkeep(actions, playback, unit)
    return actions, playback

def on_endstep(actions, playback, unit) -> tuple:  # actions, playback
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('on_endstep'):
                if component.ignore_conditional or condition(skill, unit):
                    component.on_endstep(actions, playback, unit)
    return actions, playback

def on_end_chapter(unit, skill):
    for component in skill.components:
        if component.defines('on_end_chapter'):
            if component.ignore_conditional or condition(skill, unit):
                component.on_end_chapter(unit, skill)

def init(skill):
    """
    Initializes any data on the parent skill if necessary
    """
    for component in skill.components:
        if component.defines('init'):
            component.init(skill)

def on_add(unit, skill):
    for component in skill.components:
        if component.defines('on_add'):
            component.on_add(unit, skill)
    for other_skill in unit.skills:
        for component in other_skill.components:
            if component.defines('on_other_skill'):
                component.on_gain_skill(unit, skill)

def on_remove(unit, skill):
    for component in skill.components:
        if component.defines('on_remove'):
            component.on_remove(unit, skill)

def re_add(unit, skill):
    for component in skill.components:
        if component.defines('re_add'):
            component.re_add(unit, skill)

def get_text(skill) -> str:
    for component in skill.components:
        if component.defines('text'):
            return component.text()
    return None

def get_cooldown(skill) -> float:
    for component in skill.components:
        if component.defines('cooldown'):
            return component.cooldown()
    return None

def trigger_charge(unit, skill):
    for component in skill.components:
        if component.defines('trigger_charge'):
            component.trigger_charge(unit, skill)
    return None

def get_extra_abilities(unit):
    abilities = {}
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('extra_ability'):
                if component.ignore_conditional or condition(skill, unit):
                    new_item = component.extra_ability(unit)
                    ability_name = new_item.name
                    abilities[ability_name] = new_item
    return abilities

def get_combat_arts(unit):
    from app.engine import item_funcs, target_system
    combat_arts = {}
    for skill in unit.skills:
        if not condition(skill, unit):
            continue
        combat_art = None
        combat_art_weapons = item_funcs.get_all_items(unit)
        combat_art_set_max_range = None
        combat_art_modify_max_range = None
        for component in skill.components:
            if component.defines('combat_art'):
                combat_art = component.combat_art(unit)
            if component.defines('combat_art_weapon_filter'):
                combat_art_weapons = component.combat_art_weapon_filter(unit)
            if component.defines('combat_art_set_max_range'):
                combat_art_set_max_range = component.combat_art_set_max_range(unit)
            if component.defines('combat_art_modify_max_range'):
                combat_art_modify_max_range = component.combat_art_modify_max_range(unit)

        if combat_art and combat_art_weapons:
            good_weapons = []
            # Check which of the good weapons meet the range requirements
            for weapon in combat_art_weapons:
                # Just for testing range
                if combat_art_set_max_range:
                    weapon._force_max_range = max(0, combat_art_set_max_range)
                elif combat_art_modify_max_range:
                    max_range = max(item_funcs.get_range(unit, weapon))
                    weapon._force_max_range = max(0, max_range + combat_art_modify_max_range)
                targets = target_system.get_valid_targets(unit, weapon)
                weapon._force_max_range = None
                if targets:
                    good_weapons.append(weapon)

            if good_weapons:
                combat_arts[skill.name] = (skill, good_weapons)

    return combat_arts

def activate_combat_art(unit, skill):
    for component in skill.components:
        if component.defines('on_activation'):
            component.on_activation(unit)

def deactivate_all_combat_arts(unit):
    for skill in unit.skills:
        for component in skill.components:
            if component.defines('on_deactivation'):
                component.on_deactivation(unit)
