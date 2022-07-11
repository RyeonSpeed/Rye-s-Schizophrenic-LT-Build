import logging
import random, re
from typing import Dict
from app.engine.query_engine import GameQueryEngine

from app.utilities import utils
from app.data.database import DB

import app.engine.config as cf
from app.engine import engine, item_funcs, item_system, skill_system, combat_calcs, unit_funcs, target_system
from app.engine import static_random

"""
Essentially just a repository that imports a lot of different things so that many different eval calls
will be accepted
"""

def evaluate(string: str, unit1=None, unit2=None, position=None,
             local_args: Dict = None, game=None) -> bool:
    if not game:
        from app.engine.game_state import game
    query_engine = GameQueryEngine(logging.Logger(""), game)
    query_funcs = [funcname for funcname in dir(query_engine) if not funcname.startswith('_')]
    query_func_dict = {funcname: getattr(query_engine, funcname) for funcname in query_funcs}

    def check_pair(s1: str, s2: str) -> bool:
        """
        Determines whether two units are in combat with one another
        """
        if not unit1 or not unit2:
            return False
        return (unit1.nid == s1 and unit2.nid == s2) or (unit1.nid == s2 and unit2.nid == s1)

    def check_default(s1: str, t1: tuple = ()) -> bool:
        """
        Determines whether the default fight quote should be used
        t1 contains the nids of units that have unique fight quotes
        """
        if not unit1 or not unit2:
            return False
        elif unit1.nid == s1 and unit2.team == 'player':
            return unit2.nid not in t1
        elif unit2.nid == s1 and unit1.team == 'player':
            return unit1.nid not in t1
        else:
            return False

    temp_globals = globals().copy()
    temp_globals.update({
        'unit1': unit1,
        'unit': unit1,
        'unit2': unit2,
        'target': unit2,
        'position': position,
        'check_pair': check_pair,
        'check_default': check_default,
        'game': game
    })
    temp_globals.update(query_func_dict)
    if local_args:
        temp_globals.update(local_args)
    return eval(string, temp_globals)
