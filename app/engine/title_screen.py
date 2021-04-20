import sys, os

from app.constants import WINWIDTH, WINHEIGHT, TILEX, TILEY
from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.sound import SOUNDTHREAD
from app.engine.state import State
from app.engine.background import PanoramaBackground
from app.engine import engine, save, image_mods, banner, menus, particles, randomizer
from app.engine import config as cf
from app import autoupdate
from app.engine.fluid_scroll import FluidScroll
from app.engine.game_state import game
from app.engine.randomizer import Rando

from app.events.event import Event

import logging
logger = logging.getLogger(__name__)

class TitleStartState(State):
    name = "title_start"
    in_level = False
    show_map = False

    def start(self):
        self.logo = SPRITES.get('logo')
        imgs = RESOURCES.panoramas.get('title_background')
        self.bg = PanoramaBackground(imgs) if imgs else None
        game.memory['title_bg'] = self.bg
        
        self.particles = None
        if DB.constants.value('title_particles'):
            bounds = (-WINHEIGHT, WINWIDTH, WINHEIGHT, WINHEIGHT + 16)
            self.particles = particles.ParticleSystem('title', particles.Smoke, .075, bounds, (TILEX, TILEY))
            self.particles.prefill()
        game.memory['title_particles'] = self.particles
        game.memory['transition_speed'] = 0.5

        # Wait until saving thread has finished
        if save.SAVE_THREAD:
            save.SAVE_THREAD.join()

        SOUNDTHREAD.clear()
        if DB.constants.value('music_main'):
            SOUNDTHREAD.fade_in(DB.constants.value('music_main'), fade_in=50)
        
        game.state.refresh()
        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        if event:
            SOUNDTHREAD.play_sfx('Start')
            game.memory['next_state'] = 'title_main'
            game.state.change('transition_to')

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.particles:
            self.particles.update()
            self.particles.draw(surf)
        if self.logo:
            engine.blit_center(surf, self.logo)
        return surf

class TitleMainState(State):
    name = 'title_main'
    in_level = False
    show_map = False

    menu = None
    bg = None

    def start(self):
        save.check_save_slots()
        options = ['New Game', 'Extras']
        if any(ss.kind for ss in save.SAVE_SLOTS):
            options.insert(0, 'Restart Level')
            options.insert(0, 'Load Game')
        if os.path.exists(save.SUSPEND_LOC):
            options.insert(0, 'Continue')
        # Only check for updates in frozen version
        if hasattr(sys, 'frozen') and autoupdate.check_for_update():
            options.append('Update')

        self.fluid = FluidScroll(128)
        self.bg = game.memory['title_bg']
        self.particles = game.memory['title_particles']

        self.state = 'transition_in'
        self.position_x = -WINWIDTH//2

        # For fading out to load suspend
        self.background = SPRITES.get('bg_black')
        self.transition = 100

        self.banner_flag = False

        self.selection = None
        self.menu = menus.Main(options, "title_menu_dark")
        game.state.change('transition_in')
        return 'repeat'

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        if self.state == 'alert':
            self.state = 'transition_out'
        if self.state == 'normal':
            self.menu.handle_mouse()
            if 'DOWN' in directions:
                SOUNDTHREAD.play_sfx('Select 6')
                self.menu.move_down(first_push)
            elif 'UP' in directions:
                SOUNDTHREAD.play_sfx('Select 6')
                self.menu.move_up(first_push)

            if event == 'BACK':
                SOUNDTHREAD.play_sfx('Select 4')
                game.memory['next_state'] = 'title_start'
                game.state.change('transition_to')

            elif event == 'SELECT':
                SOUNDTHREAD.play_sfx('Select 1')
                self.selection = self.menu.get_current()
                if self.selection == 'Continue':
                    self.state = 'wait'
                elif os.path.exists(save.SUSPEND_LOC) and not self.banner_flag and \
                        self.selection in ('Load Game', 'Restart Level', 'New Game'):
                    if self.selection == 'New Game':
                        text = 'Starting a new game will remove suspend!'
                    elif self.selection == 'Load Game':
                        text = 'Loading a game will remove suspend!'
                    else:
                        text = 'Restarting a game will remove suspend!'
                    game.alerts.append(banner.Custom(text))
                    game.state.change('alert')
                    self.state = 'alert'
                    self.banner_flag = True
                elif self.selection == 'Update':
                    updating = autoupdate.update()
                    if updating:
                        engine.terminate()
                    else:
                        print("Failed to update?")
                else:
                    self.state = 'transition_out'

    def update(self):
        if self.menu:
            self.menu.update()

        if self.state == 'transition_in':
            self.position_x += 20
            if self.position_x >= WINWIDTH//2:
                self.position_x = WINWIDTH//2
                self.state = 'normal'

        elif self.state == 'transition_out':
            self.position_x -= 20
            if self.position_x <= -WINWIDTH//2:
                self.position_x = -WINWIDTH//2
                if self.selection == 'Load Game':
                    game.state.change('title_load')
                elif self.selection == 'Restart Level':
                    game.state.change('title_restart')
                elif self.selection == 'Extras':
                    game.state.change('title_extras')
                elif self.selection == 'New Game':
                    # game.state.change('title_mode')
                    #game.state.change('title_new')
                    game.state.change('title_rando')
                self.state = 'transition_in'
                return 'repeat'

        elif self.state == 'wait':
            self.transition -= 5
            if self.transition <= 0:
                self.continue_suspend()
                return 'repeat'

    def continue_suspend(self):
        self.menu = None
        suspend = save.SaveSlot(save.SUSPEND_LOC, None)
        logger.info("Loading suspend...")
        save.load_game(game, suspend)

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.particles:
            self.particles.update()
            self.particles.draw(surf)
        if self.menu:
            self.menu.draw(surf, center=(self.position_x, WINHEIGHT//2), show_cursor=(self.state == 'normal'))

        bb = image_mods.make_translucent(self.background, self.transition/100.)
        surf.blit(bb, (0, 0))

        return surf

class TitleLoadState(State):
    name = 'title_load'
    in_level = False
    show_map = False

    menu = None
    bg = None

    def start(self):
        self.fluid = FluidScroll(128)
        self.state = 'transition_in'
        self.position_x = int(WINWIDTH * 1.5)

        self.bg = game.memory['title_bg']
        self.particles = game.memory['title_particles']

        save.check_save_slots()
        self.save_slots = save.SAVE_SLOTS
        options, colors = save.get_save_title(self.save_slots)
        self.menu = menus.ChapterSelect(options, colors)
        most_recent = self.save_slots.index(max(self.save_slots, key=lambda x: x.realtime))
        self.menu.move_to(most_recent)

    def take_input(self, event):
        # Only take input in normal state
        if self.state != 'normal':
            return

        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        if event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            self.state = 'transition_out'

        elif event == 'SELECT':
            selection = self.menu.current_index
            save_slot = self.save_slots[selection]
            if save_slot.kind:
                SOUNDTHREAD.play_sfx('Save')
                logger.info("Loading save of kind %s...", save_slot.kind)
                game.state.clear()
                game.state.process_temp_state()
                game.build_new()
                save.load_game(game, save_slot)
                if save_slot.kind == 'start':  # Restart
                    # Restart level
                    next_level_nid = game.game_vars['_next_level_nid']
                    game.load_states(['turn_change'])
                    game.start_level(next_level_nid)
                game.memory['transition_from'] = 'Load Game'
                game.memory['title_menu'] = self.menu
                game.state.change('title_wait')
                game.state.process_temp_state()
                save.remove_suspend()
            else:
                SOUNDTHREAD.play_sfx('Error')

    def update(self):
        if self.menu:
            self.menu.update()

        if self.state == 'transition_in':
            self.position_x -= 20
            if self.position_x <= WINWIDTH//2:
                self.position_x = WINWIDTH//2
                self.state = 'normal'

        elif self.state == 'transition_out':
            self.position_x += 20
            if self.position_x >= int(WINWIDTH * 1.5):
                self.position_x = int(WINWIDTH * 1.5)
                game.state.back()
                self.state = 'transition_in'
                return 'repeat'

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.particles:
            self.particles.update()
            self.particles.draw(surf)
        if self.menu:
            self.menu.draw(surf, center=(self.position_x, WINHEIGHT//2))
        return surf

class TitleRestartState(TitleLoadState):
    name = 'title_restart'

    def take_input(self, event):
        # Only take input in normal state
        if self.state != 'normal':
            return

        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        if event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            self.state = 'transition_out'

        elif event == 'SELECT':
            selection = self.menu.current_index
            save_slot = save.RESTART_SLOTS[selection]
            if save_slot.kind:
                SOUNDTHREAD.play_sfx('Save')
                logger.info("Loading game...")
                game.build_new()
                save.load_game(game, save_slot)
                # Restart level
                next_level_nid = game.game_vars['_next_level_nid']
                game.start_level(next_level_nid)
                game.memory['transition_from'] = 'Restart Level'
                game.memory['title_menu'] = self.menu
                game.state.change('title_wait')
                game.state.process_temp_state()
                save.remove_suspend()
            else:
                SOUNDTHREAD.play_sfx('Error')

def build_new_game(slot):
    game.build_new()

    game.state.clear()
    if 'Rando' in globals():
        game.rando_settings = game.set_rando(Rando)
    game.state.change('turn_change')
    game.state.process_temp_state()

    first_level_nid = DB.levels[0].nid
    # Skip DEBUG if it's the first level
    if first_level_nid == 'DEBUG' and len(DB.levels) > 1:
        first_level_nid = DB.levels[1].nid
    game.start_level(first_level_nid)
    game.game_vars['_next_level_nid'] = first_level_nid

    save.suspend_game(game, 'start', slot)
    save.remove_suspend()

class TitleNewState(TitleLoadState):
    name = 'title_new'

    def take_input(self, event):
        # Only take input in normal state
        if self.state != 'normal':
            return

        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        if event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            self.state = 'transition_out'

        elif event == 'SELECT':
            selection = self.menu.current_index
            save_slot = self.save_slots[selection]
            if save_slot.kind:
                SOUNDTHREAD.play_sfx('Select 1')
                game.memory['option_owner'] = selection
                game.memory['option_menu'] = self.menu
                game.memory['transition_from'] = 'New Game'
                game.memory['title_menu'] = self.menu
                game.state.change('title_new_child')
            else:
                SOUNDTHREAD.play_sfx('Save')
                build_new_game(selection)
                options, color = save.get_save_title(self.save_slots)
                self.menu.set_colors(color)
                self.menu.update_options(options)
                game.memory['transition_from'] = 'New Game'
                game.memory['title_menu'] = self.menu
                game.state.change('title_wait')

class TitleNewChildState(State):
    name = 'title_new_child'
    transparent = True
    in_level = False
    show_map = False

    def start(self):
        selection = game.memory['option_owner']
        options = ['Overwrite', 'Back']
        self.menu = menus.Choice(selection, options, (8, WINHEIGHT - 24))
        self.menu.set_horizontal(True)

    def take_input(self, event):
        self.menu.handle_mouse()
        if event == 'RIGHT':
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down()
        elif event == 'LEFT':
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up()

        elif event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            game.state.back()

        elif event == 'SELECT':
            selection = self.menu.get_current()
            if selection == 'Overwrite':
                SOUNDTHREAD.play_sfx('Save')
                build_new_game(self.menu.owner)  # game.memory['option_owner']
                game.state.change('title_wait')
                game.state.process_temp_state()
            elif selection == 'Back':
                SOUNDTHREAD.play_sfx('Select 4')
                game.state.back()

    def update(self):
        self.menu.update()

    def draw(self, surf):
        surf = self.menu.draw(surf)
        return surf

class TitleExtrasState(TitleLoadState):
    name = 'title_extras'
    in_level = False
    show_map = False

    def start(self):
        self.fluid = FluidScroll(128)
        self.position_x = int(WINWIDTH * 1.5)
        self.state = 'transition_in'

        self.bg = game.memory['title_bg']
        self.particles = game.memory['title_particles']

        options = ['Options', 'Credits']
        if cf.SETTINGS['debug']:
            options.insert(0, 'All Saves')
        self.menu = menus.Main(options, 'title_menu_dark')

    def begin(self):
        # If we came back from the credits event, fade in
        if game.state.prev_state == 'event':
            game.state.change('transition_in')
            return 'repeat'

    def take_input(self, event):
        # Only take input in normal state
        if self.state != 'normal':
            return

        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        if event == 'BACK':
            SOUNDTHREAD.play_sfx('Select 4')
            self.state = 'transition_out'

        elif event == 'SELECT':
            SOUNDTHREAD.play_sfx('Select 1')
            selection = self.menu.get_current()
            if selection == 'Credits':
                game.sweep()  # Set up event manager
                event_prefab = DB.events.get_from_nid('Global Credits')
                if event_prefab:
                    event = Event(event_prefab.nid, event_prefab.commands)
                    game.events.append(event)
                    game.memory['next_state'] = 'event'
                    game.state.change('transition_to')
                else:
                    SOUNDTHREAD.play_sfx('Error')
            elif selection == 'Options':
                game.memory['next_state'] = 'settings_menu'
                game.state.change('transition_to')
            elif selection == 'All Saves':
                game.memory['next_state'] = 'title_all_saves'
                game.state.change('transition_to')

class TitleAllSavesState(TitleLoadState):
    name = 'title_all_saves'
    in_level = False
    show_map = False

    def start(self):
        self.fluid = FluidScroll(128)
        self.state = 'transition_in'
        self.position_x = int(WINWIDTH * 1.5)

        self.bg = game.memory['title_bg']
        self.particles = game.memory['title_particles']
    
        self.save_slots = save.get_all_saves()
        options, colors = save.get_save_title(self.save_slots)
        self.menu = menus.ChapterSelect(options, colors)

class TitleWaitState(State):
    name = 'title_wait'
    in_level = False
    show_map = False
    # NOT TRANSPARENT!!!

    def start(self):
        self.bg = game.memory['title_bg']
        self.particles = game.memory['title_particles']
        
        self.wait_flag = False
        self.wait_time = engine.get_time()
        self.menu = game.memory.get('title_menu')

    def update(self):
        if self.menu:
            self.menu.update()
        if not self.wait_flag and engine.get_time() - self.wait_time > 750:
            self.wait_flag = True
            game.state.change('transition_pop')

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.particles:
            self.particles.update()
            self.particles.draw(surf)
        if self.menu:
            if 100 < engine.get_time() - self.wait_time > 200:
                self.menu.draw(surf, flicker=True)
            else:
                self.menu.draw(surf)
        return surf

class TitleSaveState(State):
    name = 'title_save'
    in_level = False
    show_map = False

    def start(self):
        self.fluid = FluidScroll(128)
        imgs = RESOURCES.panoramas.get('title_background')
        self.bg = PanoramaBackground(imgs) if imgs else None
        game.memory['title_bg'] = self.bg

        self.particles = None
        if DB.constants.value('title_particles'):
            bounds = (-WINHEIGHT, WINWIDTH, WINHEIGHT, WINHEIGHT + 16)
            self.particles = particles.ParticleSystem('title', particles.Smoke, .075, bounds, (TILEX, TILEY))
            self.particles.prefill()
        game.memory['title_particles'] = self.particles

        game.memory['transition_speed'] = 0.5

        self.leave_flag = False
        self.wait_time = 0

        save.check_save_slots()
        options, colors = save.get_save_title(save.SAVE_SLOTS)
        self.menu = menus.ChapterSelect(options, colors)
        most_recent = save.SAVE_SLOTS.index(max(save.SAVE_SLOTS, key=lambda x: x.realtime))
        self.menu.move_to(most_recent)

        game.state.change('transition_in')
        return 'repeat'

    def go_to_next_level(self, make_save=True):
        current_state = game.state.state[-1]
        next_level_nid = game.game_vars['_next_level_nid']

        game.load_states(['turn_change'])
        if make_save:
            save.suspend_game(game, game.memory['save_kind'], slot=self.menu.current_index)

        game.start_level(next_level_nid)

        game.state.state.append(current_state)
        game.state.change('transition_pop')

    def take_input(self, event):
        if self.wait_time > 0:
            return

        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_down(first_push)
        elif 'UP' in directions:
            SOUNDTHREAD.play_sfx('Select 6')
            self.menu.move_up(first_push)

        if event == 'BACK':
            # Proceed to next level anyway
            SOUNDTHREAD.play_sfx('Select 4')
            if self.name == 'in_chapter_save':
                game.state.change('transition_pop')
            elif DB.constants.value('overworld'):
                pass  # TODO: Go to overworld
            else:
                self.go_to_next_level(make_save=False)

        elif event == 'SELECT':
            SOUNDTHREAD.play_sfx('Save')
            # Rename selection
            self.wait_time = engine.get_time()
            if self.name == 'in_chapter_save':
                name = game.level.name
                self.menu.set_text(self.menu.current_index, name)
            elif DB.constants.value('overworld'):
                name = 'overworld'
                self.menu.set_name(self.menu.current_index, name)
            else:
                next_level_nid = game.game_vars['_next_level_nid']
                name = DB.levels.get(next_level_nid).name
                self.menu.set_text(self.menu.current_index, name)
            self.menu.set_color(self.menu.current_index, 'green')
            
    def update(self):
        if self.menu:
            self.menu.update()

        if self.wait_time and engine.get_time() - self.wait_time > 1250 and not self.leave_flag:
            self.leave_flag = True

            if self.name == 'in_chapter_save':
                saved_state = game.state.state[:]
                game.state.state = game.state.state[:-1]  # All except this one
                save.suspend_game(game, game.memory['save_kind'], slot=self.menu.current_index)
                # Put states back
                game.state.state = saved_state
                game.state.change('transition_pop')
            elif DB.constants.value('overworld'):
                pass  # TODO: Go to overworld
            else:
                self.go_to_next_level(make_save=True)

    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)
        if self.particles:
            self.particles.update()
            self.particles.draw(surf)
        if self.menu:
            if 100 < engine.get_time() - self.wait_time < 200:
                self.menu.draw(surf, flicker=True)
            else:
                self.menu.draw(surf)
        return surf

class TitleRandomizerState(TitleLoadState):
    name = 'title_rando'
    in_level = False
    show_map = False

    def start(self):
        self.position_x = int(WINWIDTH * 1.5)
        self.state = 'transition_in'

        self.bg = game.memory['title_bg']

        # options = ['Options', 'Credits']
        options = ['Standard','Randomized']
        self.menu = menus.Main(options, 'title_menu_dark')

    def take_input(self, event):
        # Only take input in normal state
        if self.state != 'normal':
            return

        self.menu.handle_mouse()
        if event == 'DOWN':
            self.menu.move_down()
        elif event == 'UP':
            self.menu.move_up()

        elif event == 'BACK':
            self.state = 'transition_out'

        elif event == 'SELECT':
            selection = self.menu.get_current()
            if selection == 'Standard':
                Rando.rando_settings = randomizer.resetRando()
                game.memory['next_state'] = 'title_new' #Just do whatever new game does
                game.state.change('transition_to')
            elif selection == 'Randomized':
                Rando.rando_settings = randomizer.resetRando()
                game.memory['next_state'] = 'randomizer_menu' #Utilize a version of this for rando?
                game.state.change('transition_to')
