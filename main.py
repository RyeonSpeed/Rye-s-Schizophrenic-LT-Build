import os, sys

from app.constants import VERSION
from app.data.resources.resources import RESOURCES
from app.data.database.database import DB
from app.engine import engine
from app.engine import config as cf
from app.engine import driver
from app.engine import game_state
from app.engine.codegen import source_generator

def main(name: str = 'threequel'):
    # Translation currently unused within engine proper
    # If you need to use translation, remember to copy the locale folder to your build.
    # from app.editor.editor_locale import init_locale
    # init_locale()
    if not os.path.exists(name + '.ltproj'):
        raise ValueError("Could not locate LT project %s" % (name + '.ltproj'))
    proj_path = os.path.dirname(os.path.realpath(__file__)) + name + '.ltproj'
    RESOURCES.load(proj_path)
    DB.load(proj_path)
    title = DB.constants.value('title')
    driver.start(title)
    game = game_state.start_game()
    driver.run(game)

def test_play(name: str = 'threequel'):
    if not os.path.exists(name + '.ltproj'):
        raise ValueError("Could not locate LT project %s" % (name + '.ltproj'))
    RESOURCES.load(name + '.ltproj')
    DB.load(name + '.ltproj')
    title = DB.constants.value('title')
    driver.start(title, from_editor=True)
    if 'DEBUG' in DB.levels:
        game = game_state.start_level('DEBUG')
    else:
        first_level_nid = DB.levels[0].nid
        game = game_state.start_level(first_level_nid)
    driver.run(game)

def inform_error():
    print("=== === === === === ===")
    print("A bug has been encountered.")
    print("Please copy this error log and send it to rainlash!")
    print('Or send the file "saves/debug.log.1" to rainlash!')
    print("Thank you!")
    print("=== === === === === ===")

if __name__ == '__main__':
    import logging, traceback
    from app import lt_log
    success = lt_log.create_logger()
    if not success:
        engine.terminate()

    # compile necessary files
    if not hasattr(sys, 'frozen'):
        def list_files(startpath):
            for root, dirs, files in os.walk(startpath):
                level = root.replace(startpath, '').count(os.sep)
                if level == 1:
                    first_level = os.path.basename(root)
                if level == 0 or (first_level and 'app' in first_level):
                    indent = ' ' * 4 * (level)
                    print('Python: {}{}/'.format(indent, os.path.basename(root)))
                    subindent = ' ' * 4 * (level + 1)
                    for f in files:
                        print('Python: {}{}'.format(subindent, f))
        list_files(os.getcwd())
        source_generator.generate_all()

    try:
        main()
    except Exception as e:
        logging.exception(e)
        inform_error()
        print('*** Lex Talionis Engine Version %s ***' % VERSION)
        print('Main Crash {0}'.format(str(e)))

        # Now print exception to screen
        import time
        time.sleep(0.5)
        traceback.print_exc()
        time.sleep(0.5)
        inform_error()
        engine.terminate(crash=True)
        if cf.SETTINGS['debug']:
            time.sleep(5)
        else:
            time.sleep(20)
