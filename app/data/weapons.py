from dataclasses import dataclass

from app.utilities.data import Data, Prefab

# === Can get bonuses to combat statistics based on weapon_type and weapon_rank
class CombatBonus(Prefab):
    def __init__(self, weapon_type, weapon_rank, effects):
        self.weapon_type = weapon_type
        self.weapon_rank = weapon_rank

        self.damage = effects[0]
        self.resist = effects[1]
        self.accuracy = effects[2]
        self.avoid = effects[3]
        self.crit = effects[4]
        self.dodge = effects[5]
        self.attack_speed = effects[6]
        self.defense_speed = effects[7]

    @property
    def effects(self):
        return (self.damage, self.resist, self.accuracy, self.avoid, self.crit, self.dodge, self.attack_speed, self.defense_speed)

    @classmethod
    def default(cls):
        return cls(None, None, [0]*8)

class CombatBonusList(list):
    def contains(self, weapon_type: str):
        return any(bonus.weapon_type == weapon_type for bonus in self)

    def swap_type(self, old_weapon_type: str, new_weapon_type: str):
        for bonus in self:
            if bonus.weapon_type == old_weapon_type:
                bonus.weapon_type = new_weapon_type

    def swap_rank(self, old_rank: str, new_rank: str):
        for bonus in self:
            if bonus.weapon_rank == old_rank:
                bonus.weapon_rank = new_rank

    def add_new_default(self, db):
        new_combat_bonus = CombatBonus.default()
        new_combat_bonus.weapon_type = db.weapons[0].nid
        new_combat_bonus.weapon_rank = "All"
        self.append(new_combat_bonus)
        return new_combat_bonus

    def move_index(self, old_index, new_index):
        if old_index == new_index:
            return
        obj = self.pop(old_index)
        self.insert(new_index, obj)

# === WEAPON RANK ===
@dataclass
class WeaponRank(Prefab):
    rank: str = None
    requirement: int = 1

    @property
    def nid(self):
        return self.rank

    @nid.setter
    def nid(self, value):
        self.rank = value

    def __repr__(self):
        return "WeaponRank %s: %d" % \
            (self.rank, self.requirement)

class RankCatalog(Data):
    datatype = WeaponRank

    def get_rank_from_wexp(self, wexp) -> WeaponRank:
        ranks = sorted(self._list, key=lambda x: x.requirement)
        correct_rank = None
        for rank in ranks:
            if wexp >= rank.requirement:
                correct_rank = rank
        return correct_rank

    def get_next_rank_from_wexp(self, wexp) -> WeaponRank:
        ranks = sorted(self._list, key=lambda x: x.requirement)
        correct_rank = None
        for rank in ranks:
            if wexp < rank.requirement:
                correct_rank = rank
        return correct_rank

# === WEAPON TYPE ===
@dataclass(eq=False)
class WeaponType(Prefab):
    nid: str = None
    name: str = None
    magic: bool = False
    rank_bonus: CombatBonusList = None
    advantage: CombatBonusList = None
    disadvantage: CombatBonusList = None

    icon_nid: str = None
    icon_index: tuple = (0, 0)

    def __repr__(self):
        return ("WeaponType %s" % self.nid)

    def save_attr(self, name, value):
        if name in ('rank_bonus', 'advantage', 'disadvantage'):
            value = [adv.save() for adv in value]
        else:
            value = super().save_attr(name, value)
        return value

    def restore_attr(self, name, value):
        if name in ('rank_bonus', 'advantage', 'disadvantage'):
            if value:
                value = CombatBonusList([CombatBonus.restore(adv) for adv in value])
            else:
                value = CombatBonusList()
        else:
            value = super().restore_attr(name, value)
        return value

class WeaponCatalog(Data):
    datatype = WeaponType

# === WEAPON EXPERIENCE GAINED ===
class WexpGain(Prefab):
    def __init__(self, usable: bool, weapon_type: str, wexp_gain: int):
        self.usable = usable
        self.nid = weapon_type
        self.wexp_gain = wexp_gain

    @property
    def weapon_type(self):
        return self.nid

    def absorb(self, wexp_gain):
        self.usable = wexp_gain.usable
        self.wexp_gain = wexp_gain.wexp_gain

    def save(self):
        return (self.usable, self.nid, self.wexp_gain)
    
    @classmethod
    def restore(cls, s_tuple):
        return cls(*s_tuple)

class WexpGainList(Data):
    datatype = WexpGain

    def new(self, idx, db_weapons):
        new_weapon_type = db_weapons[idx]
        self.insert(idx, WexpGain(False, new_weapon_type.nid, 0))

    @classmethod
    def default(cls, db):
        return cls([WexpGain(False, nid, 0) for nid in db.weapons.keys()])
