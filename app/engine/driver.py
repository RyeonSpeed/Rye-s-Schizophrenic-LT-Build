import os
from datetime import datetime

from app.constants import WINWIDTH, WINHEIGHT, VERSION
from app.engine import engine

import app.engine.config as cf

def start(title, from_editor=False):
    if from_editor:
        engine.constants['standalone'] = False
    engine.init()
    icon = engine.image_load('favicon.ico')
    engine.set_icon(icon)
    # Hack to get icon to show up in windows
    try:
        import ctypes
        myappid = u'rainlash.lextalionis.ltmaker.current' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        print("Maybe not Windows?")
    engine.DISPLAYSURF = engine.build_display(engine.SCREENSIZE)
    engine.set_title(title + ' - v' + VERSION)
    print("Version: %s" % VERSION)

def run(game):
    from app.engine.sound import SOUNDTHREAD
    from app.engine.input_manager import INPUT
    
    SOUNDTHREAD.reset()
    SOUNDTHREAD.set_music_volume(cf.SETTINGS['music_volume'])
    SOUNDTHREAD.set_sfx_volume(cf.SETTINGS['sound_volume'])
    
    surf = engine.create_surface((WINWIDTH, WINHEIGHT))
    screenshot = False
    # import time
    while True:
        # start = time.time_ns()
        engine.update_time()
        # print(engine.get_delta())

        raw_events = engine.get_events()
        if raw_events == engine.QUIT:
            break
        event = INPUT.process_input(raw_events)

        surf, repeat = game.state.update(event, surf)
        while repeat:  # Let's the game traverse through state chains
            surf, repeat = game.state.update([], surf)

        SOUNDTHREAD.update(raw_events)

        engine.push_display(surf, engine.SCREENSIZE, engine.DISPLAYSURF)
        # Save screenshot
        for e in raw_events:
            if e.type == engine.KEYDOWN and e.key == engine.key_map['`']:
                screenshot = True
                if not os.path.isdir('screenshots'):
                    os.mkdir('screenshots')
            elif e.type == engine.KEYUP and e.key == engine.key_map['`']:
                screenshot = False
        if screenshot:
            current_time = str(datetime.now()).replace(' ', '_').replace(':', '.')
            engine.save_surface(surf, 'screenshots/LT_%s.bmp' % current_time)

        engine.update_display()
        # milliseconds_elapsed = (end - start)/1e6
        # if milliseconds_elapsed > 10:
        #     print("Engine took too long: %f" % milliseconds_elapsed)

        game.playtime += engine.tick()
