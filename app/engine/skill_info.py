from app.engine.objects.skill import SkillObject
from typing import Union

# Tracking origin of skills for removal policies
class UnitSkill():
    skill_obj: SkillObject
    source: Union[str, tuple, int]
    displaceable: bool
    removable: bool
    
    def __init__(self, skill_obj: SkillObject, source: Union[str, tuple, int]):
        self.skill_obj = skill_obj
        self.source = source

    def displaceable(self):
        return self._displaceable

    def removable(self):
        return self._removable
        
class GlobalSkill(UnitSkill):
    displaceable = False
    removable = False
        
class TerrainSkill(UnitSkill):
    displaceable = False
    removable = False
    
class AuraSkill(UnitSkill):
    displaceable = False
    removable = False
    
class ItemSkill(UnitSkill):
    displaceable = False
    removable = False
    
class RegionSkill(UnitSkill):
    displaceable = False
    removable = False
    
class TravelerSkill(UnitSkill):
    displaceable = False
    removable = False
    
class KlassSkill(UnitSkill):
    displaceable = False
    removable = True
    
class PersonalSkill(UnitSkill):
    displaceable = False
    removable = True

class FatigueSkill(UnitSkill):
    displaceable = False
    removable = True
    
class DefaultSkill(UnitSkill):
    displaceable = True
    removable = True