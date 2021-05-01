import random

class Defaults():
    @staticmethod
    def full_price(unit, item) -> int:
        return None

    @staticmethod
    def buy_price(unit, item) -> int:
        return None

    @staticmethod
    def sell_price(unit, item) -> int:
        return None

    @staticmethod
    def special_sort(unit, item):
        return None

    @staticmethod
    def num_targets(unit, item) -> int:
        return 1

    @staticmethod
    def minimum_range(unit, item) -> int:
        return 0

    @staticmethod
    def maximum_range(unit, item) -> int:
        return 0

    @staticmethod
    def weapon_type(unit, item):
        return None

    @staticmethod
    def weapon_rank(unit, item):
        return None

    @staticmethod
    def modify_weapon_triangle(unit, item) -> int:
        return 1

    @staticmethod
    def damage(unit, item) -> int:
        return None

    @staticmethod
    def hit(unit, item) -> int:
        return None

    @staticmethod
    def crit(unit, item) -> int:
        return None

    @staticmethod
    def exp(playback, unit, item, target) -> int:
        return 0

    @staticmethod
    def wexp(playback, unit, item, target) -> int:
        return 1

    @staticmethod
    def damage_formula(unit, item) -> str:
        return 'DAMAGE'

    @staticmethod
    def resist_formula(unit, item) -> str:
        return 'DEFENSE'

    @staticmethod
    def accuracy_formula(unit, item) -> str:
        return 'HIT'

    @staticmethod
    def avoid_formula(unit, item) -> str:
        return 'AVOID'

    @staticmethod
    def crit_accuracy_formula(unit, item) -> str:
        return 'CRIT_HIT'

    @staticmethod
    def crit_avoid_formula(unit, item) -> str:
        return 'CRIT_AVOID'

    @staticmethod
    def attack_speed_formula(unit, item) -> str:
        return 'ATTACK_SPEED'

    @staticmethod
    def defense_speed_formula(unit, item) -> str:
        return 'DEFENSE_SPEED'

# HOOK CATALOG
# All false hooks are exclusive
false_hooks = ('is_weapon', 'is_spell', 'is_accessory', 'equippable',
               'can_counter', 'can_be_countered', 'can_double',
               'can_use', 'can_use_in_base', 'locked', 'allow_same_target',
               'ignore_weapon_advantage', 'unrepairable', 'targets_items',
               'menu_after_combat')
# All default hooks are exclusive
formula = ('damage_formula', 'resist_formula', 'accuracy_formula', 'avoid_formula', 
           'crit_accuracy_formula', 'crit_avoid_formula', 'attack_speed_formula', 'defense_speed_formula')
default_hooks = ('full_price', 'buy_price', 'sell_price', 'special_sort', 'num_targets', 'minimum_range', 'maximum_range',
                 'weapon_type', 'weapon_rank', 'modify_weapon_triangle', 'damage', 'hit', 'crit')
default_hooks += formula

target_hooks = ('wexp', 'exp')
simple_target_hooks = ('warning', 'danger')

dynamic_hooks = ('dynamic_damage', 'dynamic_accuracy', 'dynamic_crit_accuracy', 
                 'dynamic_attack_speed', 'dynamic_multiattacks')
modify_hooks = ('modify_damage', 'modify_resist', 'modify_accuracy', 'modify_avoid', 
                'modify_crit_accuracy', 'modify_crit_avoid', 'modify_attack_speed', 
                'modify_defense_speed')

# None of these are exclusive
event_hooks = ('on_use', 'on_end_chapter', 'reverse_use',
               'on_equip_item', 'on_unequip_item', 'on_add_item', 'on_remove_item')

combat_event_hooks = ('start_combat', 'end_combat')

status_event_hooks = ('on_upkeep', 'on_endstep')

exclusive_hooks = false_hooks + default_hooks

for hook in false_hooks:
    func = """def %s(unit, item):
                  for component in item.components:
                      if component.defines('%s'):
                          return component.%s(unit, item)
                  return False""" \
        % (hook, hook, hook)
    exec(func)

for hook in default_hooks:
    func = """def %s(unit, item):
                  for component in item.components:
                      if component.defines('%s'):
                          return component.%s(unit, item)
                  return Defaults.%s(unit, item)""" \
        % (hook, hook, hook, hook)
    exec(func)

for hook in simple_target_hooks:
    func = """def %s(unit, item, target):
                  val = 0
                  for component in item.components:
                      if component.defines('%s'):
                          val += component.%s(unit, item, target)
                  return val""" \
        % (hook, hook, hook)
    exec(func)

for hook in target_hooks:
    func = """def %s(playback, unit, item, target):
                  val = 0
                  for component in item.components:
                      if component.defines('%s'):
                          val += component.%s(playback, unit, item, target)
                  return val""" \
        % (hook, hook, hook)
    exec(func)

for hook in modify_hooks:
    func = """def %s(unit, item):
                  val = 0
                  for component in item.components:
                      if component.defines('%s'):
                          val += component.%s(unit, item)
                  return val""" \
        % (hook, hook, hook)
    exec(func)

for hook in dynamic_hooks:
    func = """def %s(unit, item, target, mode):
                  val = 0
                  for component in item.components:
                      if component.defines('%s'):
                          val += component.%s(unit, item, target, mode)
                  return val""" \
        % (hook, hook, hook)
    exec(func)

for hook in event_hooks:
    func = """def %s(unit, item):
    for component in item.components:
        if component.defines('%s'):
            component.%s(unit, item)
    if item.parent_item:
        for component in item.parent_item.components:
            if component.defines('%s'):
                component.%s(unit, item.parent_item)""" \
        % (hook, hook, hook, hook, hook)
    exec(func)

for hook in combat_event_hooks:
    func = """def %s(playback, unit, item, target):
    for component in item.components:
        if component.defines('%s'):
            component.%s(playback, unit, item, target)
    if item.parent_item:
        for component in item.parent_item.components:
            if component.defines('%s'):
                component.%s(playback, unit, item.parent_item, target)""" \
        % (hook, hook, hook, hook, hook)
    exec(func)

for hook in status_event_hooks:
    func = """def %s(actions, playback, unit, item):
    for component in item.components:
        if component.defines('%s'):
            component.%s(actions, playback, unit, item)
    if item.parent_item:
        for component in item.parent_item.components:
            if component.defines('%s'):
                component.%s(actions, playback, unit, item.parent_item)""" \
        % (hook, hook, hook, hook, hook)
    exec(func)

def available(unit, item) -> bool:
    """
    If any hook reports false, then it is false
    """
    for component in item.components:
        if component.defines('available'):
            if not component.available(unit, item):
                return False
    if item.parent_item:
        for component in item.parent_item.components:
            if component.defines('available'):
                if not component.available(unit, item.parent_item):
                    return False
    return True

def is_broken(unit, item) -> bool:
    """
    If any hook reports true, then it is true
    """
    for component in item.components:
        if component.defines('is_broken'):
            if component.is_broken(unit, item):
                return True
    if item.parent_item:
        for component in item.parent_item.components:
            if component.defines('is_broken'):
                if component.is_broken(unit, item.parent_item):
                    return True
    return False

def on_broken(unit, item) -> bool:
    alert = False
    for component in item.components:
        if component.defines('on_broken'):
            if component.on_broken(unit, item):
                alert = True
    if item.parent_item:
        for component in item.parent_item.components:
            if component.defines('on_broken'):
                if component.on_broken(unit, item.parent_item):
                    alert = True
    return alert

def valid_targets(unit, item) -> set:
    targets = set()
    for component in item.components:
        if component.defines('valid_targets'):
            targets |= component.valid_targets(unit, item)
    return targets

def ai_targets(unit, item) -> set:
    targets = set()
    for component in item.components:
        if component.defines('ai_targets'):
            if targets:  # If we already have targets, just make them smaller
                targets &= component.ai_targets(unit, item)
            else:
                targets |= component.ai_targets(unit, item)
    return targets

def target_restrict(unit, item, def_pos, splash) -> bool:
    for component in item.components:
        if component.defines('target_restrict'):
            if not component.target_restrict(unit, item, def_pos, splash):
                return False
    return True

def item_restrict(unit, item, defender, def_item) -> bool:
    for component in item.components:
        if component.defines('item_restrict'):
            if not component.item_restrict(unit, item, defender, def_item):
                return False
    return True

def ai_priority(unit, item, target, move) -> float:
    custom_ai_flag: bool = False
    ai_priority = 0
    for component in item.components:
        if component.defines('ai_priority'):
            custom_ai_flag = True
            ai_priority += component.ai_priority(unit, item, target, move)
    if custom_ai_flag:
        return ai_priority
    else:
        # Returns None when no custom ai is available
        return None

def splash(unit, item, position) -> tuple:
    """
    Returns main target position and splash positions
    """
    main_target = []
    splash = []
    for component in item.components:
        if component.defines('splash'):
            new_target, new_splash = component.splash(unit, item, position)
            main_target.append(new_target)
            splash += new_splash
    # Handle having multiple main targets
    if len(main_target) > 1:
        splash += main_target
        main_target = None
    elif len(main_target) == 1:
        main_target = main_target[0]
    else:
        main_target = None

    # If not default
    if main_target or splash:
        return main_target, splash
    else: # DEFAULT
        from app.engine import skill_system
        alternate_splash_component = skill_system.alternate_splash(unit)
        if alternate_splash_component:
            main_target, splash = alternate_splash_component.splash(unit, item, position)
            return main_target, splash
        else:
            return position, []

def splash_positions(unit, item, position) -> set:
    positions = set()
    for component in item.components:
        if component.defines('splash_positions'):
            positions |= component.splash_positions(unit, item, position)
    # DEFAULT
    if not positions:
        from app.engine import skill_system
        alternate_splash_component = skill_system.alternate_splash(unit)
        if alternate_splash_component:
            positions = alternate_splash_component.splash_positions(unit, item, position)
            return positions
        else:
            return {position}
    return positions

def find_hp(actions, target):
    from app.engine import action
    starting_hp = target.get_hp()
    for subaction in actions:
        if isinstance(subaction, action.ChangeHP):
            starting_hp += subaction.num
    return starting_hp

def after_hit(actions, playback, unit, item, target, mode):
    for component in item.components:
        if component.defines('after_hit'):
            component.after_hit(actions, playback, unit, item, target, mode)
    if item.parent_item:
        for component in item.parent_item.components:
            if component.defines('after_hit'):
                component.after_hit(actions, playback, unit, item.parent_item, target, mode)

def on_hit(actions, playback, unit, item, target, target_pos, mode, first_item):
    for component in item.components:
        if component.defines('on_hit'):
            component.on_hit(actions, playback, unit, item, target, target_pos, mode)
    if item.parent_item and first_item:
        for component in item.parent_item.components:
            if component.defines('on_hit'):
                component.on_hit(actions, playback, unit, item.parent_item, target, target_pos, mode)

    # Default playback
    if target and find_hp(actions, target) <= 0:
        playback.append(('shake', 2))
        if not any(brush for brush in playback if brush[0] == 'hit_sound'):
            playback.append(('hit_sound', 'Final Hit'))
    else:
        playback.append(('shake', 1))
        if not any(brush[0] == 'hit_sound' for brush in playback):
            playback.append(('hit_sound', 'Attack Hit ' + str(random.randint(1, 5))))
    if target and not any(brush for brush in playback if brush[0] in ('unit_tint_add', 'unit_tint_sub')):
        playback.append(('unit_tint_add', target, (255, 255, 255)))

def on_crit(actions, playback, unit, item, target, target_pos, mode, first_item):
    for component in item.components:
        if component.defines('on_crit'):
            component.on_crit(actions, playback, unit, item, target, target_pos, mode)
        elif component.defines('on_hit'):
            component.on_hit(actions, playback, unit, item, target, target_pos, mode)
    if item.parent_item and first_item:
        for component in item.parent_item.components:
            if component.defines('on_crit'):
                component.on_crit(actions, playback, unit, item.parent_item, target, target_pos, mode)
            elif component.defines('on_hit'):
                component.on_hit(actions, playback, unit, item.parent_item, target, target_pos, mode)

    # Default playback
    playback.append(('shake', 3))
    if target:
        playback.append(('crit_vibrate', target))
        if not any(brush for brush in playback if brush[0] == 'hit_sound'):
            if find_hp(actions, target) <= 0:
                playback.append(('hit_sound', 'Final Hit'))
            else:
                playback.append(('hit_sound', 'Critical Hit ' + str(random.randint(1, 2))))
        if not any(brush for brush in playback if brush[0] == 'crit_tint'):
            playback.append(('crit_tint', target, (255, 255, 255)))

def on_miss(actions, playback, unit, item, target, target_pos, mode, first_item):
    for component in item.components:
        if component.defines('on_miss'):
            component.on_miss(actions, playback, unit, item, target, target_pos, mode)
    if item.parent_item and first_item:
        for component in item.parent_item.components:
            if component.defines('on_miss'):
                component.on_miss(actions, playback, unit, item.parent_item, target, target_pos, mode)

    # Default playback
    playback.append(('hit_sound', 'Attack Miss 2'))
    playback.append(('hit_anim', 'MapMiss', target))

def item_icon_mod(unit, item, target, sprite):
    for component in item.components:
        if component.defines('item_icon_mod'):
            sprite = component.item_icon_mod(unit, item, target, sprite)
    return sprite

def can_unlock(unit, item, region) -> bool:
    for component in item.components:
        if component.defines('can_unlock'):
            if component.can_unlock(unit, item, region):
                return True
    return False

def init(item):
    """
    Initializes any data on the parent item if necessary
    """
    for component in item.components:
        if component.defines('init'):
            component.init(item)
