from app.utilities.data import Prefab

from app.engine.game_state import game

class PartyObject(Prefab):
    def __init__(self, nid, name, leader_nid, units=None, money=0, convoy=None, bexp=0):
        self.nid = nid
        self.name = name
        self.leader_nid = leader_nid
        self.party_prep_manage_sort_order = units or []  # Unit nids (The order is used for the prep and manage screen and NOTHING ELSE)
        self.money = money
        if convoy:
            # Actually the item, not just a uid reference
            self.convoy = [game.get_item(item_uid) for item_uid in convoy]
            self.convoy = [i for i in self.convoy if i]
        else:
            self.convoy = []
        self.bexp: int = bexp

    @property
    def items(self):
        return self.convoy

    def save(self):
        return {'nid': self.nid,
                'name': self.name,
                'leader_nid': self.leader_nid,
                'units': self.party_prep_manage_sort_order,
                'money': self.money,
                'convoy': [item.uid for item in self.convoy],
                'bexp': self.bexp}

    @classmethod
    def restore(cls, s_dict):
        party = cls(s_dict['nid'], s_dict['name'], s_dict['leader_nid'],
                    s_dict['party_prep_manage_sort_order'], s_dict['money'], s_dict['convoy'],
                    s_dict['bexp'])
        return party
