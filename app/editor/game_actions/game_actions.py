import glob

from app.editor.data_editor import DB
from app.engine import engine, driver, game_state

import logging

def handle_exception(e: Exception):
    logging.error("Engine crashed with a fatal error!")
    logging.exception(e)
    # Required to close window (reason: Unknown)
    engine.terminate(True)

def test_play():
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        game = game_state.start_game()
        driver.run(game)
    except Exception as e:
        handle_exception(e)

def test_play_current(level_nid):
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        game = game_state.start_level(level_nid)
        driver.run(game)
    except Exception as e:
        handle_exception(e)

def get_saved_games():
    GAME_NID = str(DB.constants.value('game_nid'))
    return glob.glob('saves/' + GAME_NID + '-preload-*-*.p')

def test_play_load(level_nid, save_loc=None):
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        if save_loc:
            game = game_state.load_level(level_nid, save_loc)
        else:
            game = game_state.start_level(level_nid)
        driver.run(game)
    except Exception as e:
        handle_exception(e)

def test_combat(left_combat_anim, left_weapon_anim, left_palette_name, left_palette, left_item_nid: str, 
                right_combat_anim, right_weapon_anim, right_palette_name, right_palette, right_item_nid: str,
                pose_nid: str):
    try:
        driver.start("Combat Test", from_editor=True)
        from app.engine import battle_animation
        from app.engine.combat.mock_combat import MockCombat
        right = battle_animation.BattleAnimation.get_anim(right_combat_anim, right_weapon_anim, right_palette_name, right_palette, None, right_item_nid)
        left = battle_animation.BattleAnimation.get_anim(right_weapon_anim, left_weapon_anim, left_palette_name, left_palette, None, left_item_nid)
        at_range = 1 if 'Ranged' in right_weapon_anim.nid else 0
        mock_combat = MockCombat(left, right, at_range, pose_nid)
        left.pair(mock_combat, right, False, at_range)
        right.pair(mock_combat, left, True, at_range)
        driver.run_combat(mock_combat)
    except Exception as e:
        handle_exception(e)
