from __future__ import annotations
from functools import lru_cache

import sys
import traceback

from typing import Optional
from app.engine.game_state import GameState

from app.events import event_commands
from app.events.python_eventing.compilation import Compiler
from app.events.python_eventing.errors import InvalidPythonError
from app.events.python_eventing.utils import DO_NOT_EXECUTE_SENTINEL
from app.utilities.typing import NID

class PythonEventParser():
    def __init__(self, nid: NID, source: str, game: GameState):
        self.nid = nid
        self.source = source
        self.curr_cmd_idx = 0
        self.is_finished = False
        self._script = Compiler.compile(nid, source, game, 0)

    @lru_cache()
    def get_source_line(self, line: int) -> str:
        as_lines = self.source.split('\n')
        return as_lines[line]

    def get_current_line(self) -> int:
        return self.curr_cmd_idx

    def fetch_next_command(self) -> Optional[event_commands.EventCommand]:
        try:
            command_idx, next_command = next(self._script)
            while command_idx is DO_NOT_EXECUTE_SENTINEL:
                command_idx, next_command = next(self._script)
            self.curr_cmd_idx = command_idx
            return next_command
        except StopIteration:
            self.is_finished = True
            return None
        except Exception as e:
            # exception occured in python script
            _, _, exc_tb = sys.exc_info()
            tbs = traceback.extract_tb(exc_tb)
            # Proceed backwards through the stack trace until we find a "<string>"
            for tb in reversed(tbs):
                exception_fname, exception_lineno = tb[:2]
                if exception_fname == "<string>":
                    # This means that we failed in the python script itself and 
                    # can therefore figure out exactly what line in the python script is wrong
                    diff_lines = Compiler.num_diff_lines()
                    true_lineno = exception_lineno - diff_lines
                    failing_line = self.get_source_line(true_lineno - 1)
                    exc = InvalidPythonError(self.nid, true_lineno, failing_line)
                    exc.what = str(e)
                    exc.original_exception = e
                    raise exc from e
                    break
            else:
                # Unable to handle the error correctly, so just raise it up
                raise e

    def finished(self):
        return self.is_finished

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['source'] = self.source
        s_dict['is_finished'] = self.is_finished
        s_dict['curr_cmd_idx'] = self.curr_cmd_idx
        return s_dict

    @classmethod
    def restore(cls, s_dict, game: GameState) -> PythonEventParser:
        source = s_dict['source']
        nid = s_dict['nid']
        self = cls(nid, source, game)
        self.curr_cmd_idx = s_dict['curr_cmd_idx']
        self._script = Compiler.compile(nid, source, game, self.curr_cmd_idx)
        return self
