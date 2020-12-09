import random

class Defaults():
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
    def defense_formula(unit, item) -> str:
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
               'can_use', 'can_use_in_base', 'locked', 'allow_same_target')
# All true hooks are not exclusive
true_hooks = ('can_counter', 'can_be_countered', 'can_double')
# All default hooks are exclusive
formula = ('damage_formula', 'defense_formula', 'accuracy_formula', 'avoid_formula', 
           'crit_accuracy_formula', 'crit_avoid_formula', 'attack_speed_formula', 'defense_speed_formula')
default_hooks = ('buy_price', 'sell_price', 'special_sort', 'num_targets', 'minimum_range', 'maximum_range',
                 'weapon_type', 'weapon_rank', 'modify_weapon_triangle', 'damage', 'hit', 'crit')
default_hooks += formula

target_hooks = ('wexp', 'exp')

dynamic_hooks = ('dynamic_damage', 'dynamic_accuracy', 'dynamic_crit_accuracy', 
                 'dynamic_attack_speed', 'dynamic_multiattacks')
modify_hooks = ('modify_damage', 'modify_resist', 'modify_accuracy', 'modify_avoid', 
                'modify_crit_accuracy', 'modify_crit_avoid', 'modify_attack_speed', 
                'modify_defense_speed')

# None of these are exclusive
event_hooks = ('on_use', 'on_not_usable', 'on_end_chapter', 'on_upkeep', 'on_endstep',
               'on_equip', 'on_unequip', 'on_hold', 'on_drop')

exclusive_hooks = false_hooks + default_hooks

for hook in false_hooks:
    func = """def %s(unit, item):
                  for component in item.components:
                      if component.defines('%s'):
                          return component.%s(unit, item)
                  return False""" \
        % (hook, hook, hook)
    exec(func)

for hook in true_hooks:
    func = """def %s(unit, item):
                  for component in item.components:
                      if component.defines('%s') and not component.%s(unit, item):
                          return False
                  return True""" \
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
            component.%s(unit, item)""" \
        % (hook, hook, hook)
    exec(func)

def available(unit, item) -> bool:
    """
    If any hook reports false, then it is false
    """
    for component in item.components:
        if component.defines('available'):
            if not component.available(unit, item):
                return False
    return True

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
            targets |= component.ai_targets(unit, item)
    return targets

def target_restrict(unit, item, defender, splash) -> bool:
    for component in item.components:
        if component.defines('target_restrict'):
            if not component.target_restrict(unit, item, defender, splash):
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

def get_range(unit, item) -> set:
    min_range, max_range = 0, 0
    for component in item.components:
        if component.defines('minimum_range'):
            min_range = component.minimum_range(unit, item)
            break
    for component in item.components:
        if component.defines('maximum_range'):
            max_range = component.maximum_range(unit, item)
            break
    return set(range(min_range, max_range + 1))

def splash(unit, item, position) -> tuple:
    """
    Returns main target and splash
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
    else:
        from app.engine.game_state import game
        return game.board.get_unit(position), []

def splash_positions(unit, item, position) -> set:
    positions = set()
    for component in item.components:
        if component.defines('splash_positions'):
            positions |= component.splash_positions(unit, item)
    if not positions:
        return {position}
    return positions

def find_hp(actions, target):
    from app.engine import action
    starting_hp = target.get_hp()
    for subaction in actions:
        if isinstance(subaction, action.ChangeHP):
            starting_hp += subaction.num
    return starting_hp

def on_hit(actions, playback, unit, item, target, mode=None):
    for component in item.components:
        if component.defines('on_hit'):
            component.on_hit(actions, playback, unit, item, target, mode)

    # Default playback
    if find_hp(actions, target) <= 0:
        playback.append(('shake', 2))
        if not any(action for action in playback if action[0] == 'hit_sound'):
            playback.append(('hit_sound', 'Final Hit'))
    else:
        playback.append(('shake', 1))
        if not any(action[0] == 'hit_sound' for action in playback):
            playback.append(('hit_sound', 'Attack Hit ' + str(random.randint(1, 5))))
    if not any(action for action in playback if action[0] == 'unit_tint'):
        playback.append(('unit_tint', target, (255, 255, 255, 255)))

def on_crit(actions, playback, unit, item, target, mode=None):
    for component in item.components:
        if component.defines('on_crit'):
            component.on_crit(actions, playback, unit, item, target, mode)
        elif component.defines('on_hit'):
            component.on_hit(actions, playback, unit, item, target, mode)

    # Default playback
    playback.append(('shake', 3))
    playback.append(('crit_vibrate', target))
    if not any(action for action in playback if action[0] == 'hit_sound'):
        if find_hp(actions, target) <= 0:
            playback.append(('hit_sound', 'Final Hit'))
        else:
            playback.append(('hit_sound', 'Critical Hit ' + str(random.randint(1, 2))))
    if not any(action for action in playback if action[0] == 'crit_tint'):
        playback.append(('crit_tint', target, (255, 255, 255, 255)))

def on_miss(actions, playback, unit, item, target, mode=None):
    for component in item.components:
        if component.defines('on_miss'):
            component.on_miss(actions, playback, unit, item, target, mode)

    # Default playback
    playback.append(('hit_sound', 'Attack Miss 2'))
    playback.append(('hit_anim', 'MapMiss', target))

def item_icon_mods(unit, item, target, sprite):
    for component in item.components:
        if component.defines('item_icon_mods'):
            sprite = component.item_icon_mods(unit, item, target, sprite)
    return sprite

def init(item):
    for component in item.components:
        if component.defines('init'):
            component.init(item)
