from typing import Tuple

from app.resources.map_icons import MapIconCatalog
from app.utilities.data import Data, Prefab
from app.events.node_events import NodeEvent


class OverworldNodePrefab(Prefab):
    def __init__(self, nid: str, name: str, pos: str, icon: str = None):
        self.nid: str = nid
        self.name: str = name
        self.pos: Tuple[int, int] = pos             # tuple of location pair
        self.icon: str = icon or MapIconCatalog.DEFAULT()           # icon nid (see map_icons.json for a manifest)
        self.level: str = None          # level associated
        self.menu_options = Data()      #Events that can be activated in the node's menu

    def save_attr(self, name, value):
        # I cannot, for the life of me, get saving and loading stuff to play nice. Any help would be great.
        if name == 'menu_options':
            value = [menu_options.save() for menu_options in value]
        else:
            value = super().save_attr(name, value)
        return value

    def restore_attr(self, name, value):
        if name == 'menu_options':
            if value:
                value = Data([NodeEvent.restore(val) for val in value])
            else:
                value = Data()
        else:
            value = super().restore_attr(name, value)
        if(name == 'pos'):
            value = tuple(value)
        return value

    @classmethod
    def default(cls):
        return cls('0', 'Frelia Castle', (0, 0))

class OverworldNodeCatalog(Data[OverworldNodePrefab]):
    datatype = OverworldNodePrefab
