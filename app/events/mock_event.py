from enum import Enum

from app.events.event import Event

class IfStatementStrategy(Enum):
    ALWAYS_TRUE = 1
    ALWAYS_FALSE = 2

class MockGame():
    """
    Mock game object that stores the speak styles, so they work even though the rest of the game isn't present
    """
    def __init__(self):
        self.speak_styles = speak_style.SpeakStyleLibrary()

class MockEvent(Event):
    # These are the only commands that will be processed by this event
    available = {"finish", "wait", "end_skip", "music", "music_clear", "sound", "add_portrait", "multi_add_portrait", "remove_portrat" "multi_remove_portrait", "move_portrait", "mirror_portrait", "bop_portrait", "expression", "speak_style", "speak", "unhold", "transition", "change_background", "table", "remove_table", "draw_overlay_sprite", "remove_overlay_sprite", "location_card", "credits", "ending", "pop_dialog"}

    loop_commands = {'for', 'endf'}

    def __init__(self, nid, commands, command_idx=0, if_statement_strategy=IfStatementStrategy.ALWAYS_TRUE):
        self.nid = nid
        self.commands: List[event_commands.EventCommand] = commands.copy()
        self.command_idx = command_idx
        self.if_statement_strategy = if_statement_strategy

        self.background = None
        self.game = MockGame()

        self._generic_setup()

    def update(self):
        current_time = engine.get_time()
        # update all internal updates, remove the ones that are finished
        self.should_update = {name: to_update for name, to_update in self.should_update.items() if not to_update(self.do_skip)}

        self._update_state(dialog_log=False)
        self._update_transition()

    def handle_loop(self, command: event_commands.EventCommand) -> bool:
        if command.nid == 'for':
            internal_fors = 0

            curr_idx = self.command_idx + 1
            curr_command = self.commands[curr_idx]
            looped_commands: List[event_commands.EventCommand] = []
            while curr_command.nid != 'endf' or internal_fors > 0:
                if curr_command.nid == 'for':
                    internal_fors += 1
                if curr_command.nid == 'endf':
                    internal_fors -= 1
                looped_commands.append(curr_command)
                curr_idx += 1
                if curr_idx > len(self.commands):
                    self.logger.error("%s: could not find end command for loop %s" % ('handle_loop', cond))
                    return True
                curr_command = self.commands[curr_idx]

            # skip the stuff inthe middle
            self.command_idx = curr_idx
            return True
        # Skip endf command here
        elif command.nid == 'endf':
            return True
        return False

    def _get_truth(self, command):
        if self.if_statement_strategy == IfStatementStrategy.ALWAYS_TRUE:
            truth = True
        else:
            truth = False
        self.logger.info("Result: %s" % truth)
        return truth

    def run_command(self, command: event_commands.EventCommand):
        # Only certain commands will be processed
        if command.nid in self.available:
            super().run_command(command)
