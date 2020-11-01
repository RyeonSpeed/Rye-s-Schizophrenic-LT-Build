from dataclasses import dataclass

from app.utilities.data import Data, Prefab
from app.data import stats, weapons
from app.data.skills import LearnedSkill

@dataclass
class Klass(Prefab):
    nid: str = None
    name: str = None

    desc: str = ""
    tier: int = 1
    movement_group: str = None

    promotes_from: str = None
    turns_into: list = None
    tags: list = None
    max_level: int = 20

    bases: stats.StatList = None
    growths: stats.StatList = None
    growth_bonus: stats.StatList = None
    promotion: stats.StatList = None
    max_stats: stats.StatList = None

    learned_skills: list = None
    wexp_gain: weapons.WexpGainList = None

    icon_nid: str = None
    icon_index: tuple = (0, 0)
    map_sprite_nid: str = None
    combat_anim_nid: str = None

    def get_stat_titles(self):
        return ['Generic Bases', 'Generic Growths', 'Promotion Gains', 'Growth Bonuses', 'Stat Maximums']

    def get_stat_lists(self):
        return [self.bases, self.growths, self.promotion, self.growth_bonus, self.max_stats]

    def get_skills(self):
        return [skill[1] for skill in self.learned_skills]

    def replace_skill_nid(self, old_nid, new_nid):
        for item in self.learned_skills:
            if item[1] == old_nid:
                item[1] = new_nid

    def save_attr(self, name, value):
        if name == 'learned_skills':
            value = [skill.save() for skill in value]
        else:
            value = super().save_attr(name, value)
        return value

    def restore_attr(self, name, value):
        if name in ('bases', 'growths', 'growth_bonus', 'promotion', 'max_stats'):
            value = stats.StatList().restore(value)
        elif name == 'learned_skills':
            value = [LearnedSkill.restore(skill) for skill in value]
        elif name == 'wexp_gain':
            value = weapons.WexpGainList().restore(value)
        else:
            value = super().restore_attr(name, value)
        return value

class ClassCatalog(Data):
    datatype = Klass
