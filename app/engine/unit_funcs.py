from app.utilities import utils
from app.data.database import DB

from app.engine import static_random, item_funcs

import logging
logger = logging.getLogger(__name__)

def get_next_level_up(unit) -> dict:
    if unit.team == 'player':
        method = DB.constants.value('player_leveling')
    else:
        method = DB.constants.value('enemy_leveling')
        if method == 'Match':
            method = DB.constants.value('player_leveling')

    stat_changes = {nid: 0 for nid in DB.stats.keys()}
    klass = DB.classes.get(unit.klass)
    for nid in DB.stats.keys():
        growth = unit.growths[nid] + unit.growth_bonus(nid) + klass.growth_bonus.get(nid, 0)
        if method == 'Fixed':
            if growth > 0:
                stat_changes[nid] = (unit.growth_points[nid] + growth) // 100
                unit.growth_points[nid] = (unit.growth_points[nid] + growth) % 100
            elif growth < 0:
                stat_changes[nid] = (-unit.growth_points[nid] + growth) // 100
                unit.growth_points[nid] = (unit.growth_points[nid] - growth) % 100

        elif method == 'Random':
            stat_changes[nid] += _random_levelup(unit, unit.get_internal_level(), growth)
        elif method == 'Dynamic':
            _dynamic_levelup(unit, unit.get_internal_level(), stat_changes, unit.growth_points, nid, growth)
            
        stat_changes[nid] = utils.clamp(stat_changes[nid], -unit.stats[nid], klass.max_stats.get(nid, 30) - unit.stats[nid])

    return stat_changes

def _random_levelup(unit, level, growth_rate):
    rng = static_random.get_levelup(unit.nid, level)
    counter = 0
    if growth_rate > 0:
        while growth_rate > 0:
            counter += 1 if rng.randint(0, 99) < growth_rate else 0
            growth_rate -= 100
    elif growth_rate < 0:
        growth_rate = -growth_rate
        while growth_rate > 0:
            counter -= 1 if rng.randint(0, 99) < growth_rate else 0
            growth_rate -= 100
    return counter

def _dynamic_levelup(unit, level, stats, growth_points, growth_nid, growth_rate):
    rng = static_random.get_levelup(unit.nid, level)
    variance = 10
    if growth_rate > 0:
        start_growth = growth_rate + growth_points[growth_nid]
        if start_growth <= 0:
            growth_points[growth_nid] += growth_rate / 5.
        else:
            free_levels = growth_rate // 100
            stats[growth_nid] += free_levels
            new_growth = growth_rate % 100
            start_growth = new_growth + growth_points[growth_nid]
            if rng.randint(0, 99) < int(start_growth):
                stats[growth_nid] += 1
                growth_points[growth_nid] -= (100 - new_growth) / variance
            else:
                growth_points[growth_nid] += new_growth/variance
    elif growth_rate < 0:
        growth_rate = -growth_rate
        start_growth = growth_rate + growth_points[growth_nid]
        if start_growth <= 0:
            growth_points[growth_nid] += growth_rate / 5.
        else:
            free_levels = growth_rate // 100
            stats[growth_nid] -= free_levels
            new_growth = growth_rate % 100
            start_growth = new_growth + growth_points[growth_nid]
            if rng.randint(0, 99) < int(start_growth):
                stats[growth_nid] -= 1
                growth_points[growth_nid] -= (100 - new_growth) / variance
            else:
                growth_points[growth_nid] += new_growth/variance

def auto_level(unit, num_levels, starting_level=1):
    """
    Only for generics
    """

    # Get how to level
    if unit.team == 'player':
        method = DB.constants.value('player_leveling')
    else:
        method = DB.constants.value('enemy_leveling')
        if method == 'Match':
            method = DB.constants.value('player_leveling')

    if method == 'Fixed':
        for growth_nid, growth_value in unit.growths.items():
            growth_sum = (growth_value + unit.growth_bonus(growth_nid)) * num_levels
            if growth_value < 0:
                unit.stats[growth_nid] += (growth_sum - unit.growth_points[growth_nid]) // 100
                unit.growth_points[growth_nid] = -(growth_sum - unit.growth_points[growth_nid]) % 100
            else:
                unit.stats[growth_nid] += (growth_sum + unit.growth_points[growth_nid]) // 100
                unit.growth_points[growth_nid] = (growth_sum + unit.growth_points[growth_nid]) % 100

    elif method == 'Random':
        for growth_nid, growth_value in unit.growths.items():
            growth_rate = growth_value + unit.growth_bonus(growth_nid)
            for n in range(num_levels):    
                unit.stats[growth_nid] += _random_levelup(unit, starting_level + n, growth_rate)

    elif method == 'Dynamic':
        for growth_nid, growth_value in unit.growths.items():
            growth_rate = growth_value + unit.growth_bonus(growth_nid)
            for n in range(num_levels):
                _dynamic_levelup(unit, starting_level + n, unit.stats, unit.growth_points, growth_nid, growth_rate)
                
    # Make sure we don't exceed max
    klass = DB.classes.get(unit.klass)
    unit.stats = {k: utils.clamp(v, 0, klass.max_stats.get(k, 30)) for (k, v) in unit.stats.items()}
    unit.set_hp(1000)  # Go back to full hp

def apply_stat_changes(unit, stat_changes: dict, in_base: bool = False):
    """
    Assumes stat changes are valid!
    """
    logger.info("Applying stat changes %s to %s", stat_changes, unit.nid)
    
    for nid, value in stat_changes.items():
        unit.stats[nid] += value

    if in_base:
        unit.set_hp(1000)
        unit.set_mana(1000)

def get_starting_skills(unit, settings = None) -> list:
    # Class skills
    klass_obj = DB.classes.get(unit.klass)
    current_klass = klass_obj
    all_klasses = [klass_obj]
    counter = 5
    while current_klass and current_klass.tier > 1 and counter > 0:
        counter -= 1  # Prevent infinite loops
        if current_klass.promotes_from:
            current_klass = DB.classes.get(current_klass.promotes_from)
            all_klasses.append(current_klass)
        else:
            break
    all_klasses.reverse()
    
    skills_to_add = []
    feats = DB.skills.get_feats()
    current_skills = [skill.nid for skill in unit.skills]
    for idx, klass in enumerate(all_klasses):
        if settings:
            skill_set = settings.rando_settings['klassDictionary'][klass.nid].learned_skills
        else:
            skill_set = klass.learned_skills
        for learned_skill in skill_set:
            if (learned_skill[0] <= unit.level or klass != klass_obj) and \
                    learned_skill[1] not in current_skills and \
                    learned_skill[1] not in skills_to_add:
                if learned_skill[1] == 'Feat':
                    if DB.constants.value('generic_feats'):
                        my_feats = [feat for feat in feats if feat.nid not in current_skills and feat.nid not in skills_to_add]
                        random_number = static_random.get_growth() % len(my_feats)
                        new_skill = my_feats[random_number]
                        skills_to_add.append(new_skill.nid)
                else:
                    skills_to_add.append(learned_skill[1])

    klass_skills = item_funcs.create_skills(unit, skills_to_add)
    return klass_skills

def get_personal_skills(unit, prefab):
    skills_to_add = []
    current_skills = [skill.nid for skill in unit.skills]
    for learned_skill in prefab.learned_skills:
        if learned_skill[0] <= unit.level and learned_skill[1] not in current_skills:
            skills_to_add.append(learned_skill[1])

    personal_skills = item_funcs.create_skills(unit, skills_to_add)
    return personal_skills

def can_unlock(unit, region) -> bool:
    from app.engine import skill_system, item_system
    if skill_system.can_unlock(unit, region):
        return True
    for item in item_funcs.get_all_items(unit):
        if item_funcs.available(unit, item) and \
                item_system.can_unlock(unit, item, region):
            return True
    return False

def check_focus(unit, limit=3) -> int:
    from app.engine import skill_system
    from app.engine.game_state import game
    counter = 0
    if unit.position:
        for other in game.units:
            if other.position and \
                    unit is not other and \
                    skill_system.check_ally(unit, other) and \
                    utils.calculate_distance(unit.position, other.position) <= limit:
                counter += 1
    return counter
