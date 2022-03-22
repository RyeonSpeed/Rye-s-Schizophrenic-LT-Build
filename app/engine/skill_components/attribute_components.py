from app.data.skill_components import SkillComponent, SkillTags
from app.data.components import Type

class Hidden(SkillComponent):
    nid = 'hidden'
    desc = "Skill will not show up on screen"
    tag = SkillTags.ATTRIBUTE

class HiddenIfInactive(SkillComponent):
    nid = 'hidden_if_inactive'
    desc = 'Skill will not show up on info menu if condition is not fulfilled'
    tag = SkillTags.ATTRIBUTE

class TerrainSkill(SkillComponent):
    nid = 'is_terrain'
    desc = 'Skill is hidden and will not affect fliers'
    tag = SkillTags.ATTRIBUTE

    ignore_conditional = True

    def condition(self, unit):
        return not 'Flying' in unit.tags

class ClassSkill(SkillComponent):
    nid = 'class_skill'
    desc = "Skill will show up on first page of info menu"
    tag = SkillTags.ATTRIBUTE

class Stack(SkillComponent):
    nid = 'stack'
    desc = "Skill can be applied to a unit multiple times"
    tag = SkillTags.ATTRIBUTE

class Feat(SkillComponent):
    nid = 'feat'
    desc = "Skill can be selected as a feat"
    tag = SkillTags.ATTRIBUTE

class Negative(SkillComponent):
    nid = 'negative'
    desc = "Skill is considered detrimental"
    tag = SkillTags.ATTRIBUTE

class Global(SkillComponent):
    nid = 'global'
    desc = "All units will possess this skill"
    tag = SkillTags.ATTRIBUTE

class Negate(SkillComponent):
    nid = 'negate'
    desc = "Skill negates Effective component"
    tag = SkillTags.ATTRIBUTE

class NegateTags(SkillComponent):
    nid = 'negate_tags'
    desc = "Skill negates Effective component on specific Tags"
    tag = SkillTags.ATTRIBUTE

    expose = (Type.List, Type.Tag)

class HasTags(SkillComponent):
    nid = 'has_tags'
    desc = 'Skill grants the following tags to the unit'
    tag = SkillTags.ATTRIBUTE

    expose = (Type.List, Type.Tag)