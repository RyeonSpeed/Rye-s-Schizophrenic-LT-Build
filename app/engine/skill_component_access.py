from functools import lru_cache

from app.data.database.components import ComponentType
from app.data.database.skill_components import SkillComponent, SkillTags
from app.utilities.class_utils import recursive_subclasses
from app.utilities.data import Data
import importlib, inspect

@lru_cache(1)
def get_cached_skill_components(proj_dir: str):
    from app.data.resources.resources import RESOURCES
    from app.engine import skill_components
    if RESOURCES.has_loaded_custom_components():
        # Necessary for get_skill_components to find the item component subclasses
        # defined here
        import custom_components

    #subclasses = recursive_subclasses(SkillComponent)
    subclasses = SkillComponent.__subclasses__()
    import os
    from glob import glob
    for file in glob(os.path.join(os.path.dirname(__file__), 'skill_components', "*.pyc")):
        name = 'app.engine.skill_components.'+os.path.splitext(os.path.basename(file))[0]

        # add package prefix to name, if required
        for name2, cls in inspect.getmembers(importlib.import_module(name)):
            if inspect.isclass(cls) and cls.__name__ not in 'ComponentType, SkillComponent, SkillTags' and hasattr(cls, 'tag'):
                subclasses.append(cls)
    # Sort by tag
    subclasses = sorted(subclasses, key=lambda x: list(SkillTags).index(x.tag) if x.tag in list(SkillTags) else 100)
    return Data(subclasses)

def get_skill_components():
    from app.data.database.database import DB
    return get_cached_skill_components(DB.current_proj_dir)

def get_skill_tags():
    return list(SkillTags)

def get_component(nid):
    _skill_components = get_skill_components()
    base_class = _skill_components.get(nid)
    if base_class:
        return base_class(base_class.value)
    return None

def restore_component(dat):
    nid, value = dat
    _skill_components = get_skill_components()
    base_class = _skill_components.get(nid)
    if base_class:
        if isinstance(base_class.expose, tuple):
            if base_class.expose[0] == ComponentType.List:
                # Need to make a copy
                # so we don't keep the reference around
                copy = base_class(value.copy())
            elif base_class.expose[0] in (ComponentType.Dict, ComponentType.FloatDict, ComponentType.StringDict):
                val = [v.copy() for v in value]
                copy = base_class(val)
            elif base_class.expose[0] == ComponentType.MultipleChoice:
                copy = base_class(value)
        else:
            copy = base_class(value)
        return copy
    return None

templates = {}

def get_templates():
    return templates.items()
