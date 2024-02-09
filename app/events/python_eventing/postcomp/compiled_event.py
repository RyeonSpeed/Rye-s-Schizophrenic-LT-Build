from dataclasses import dataclass
import sys
import traceback
from typing import Generator
from app.engine.evaluate import get_context
from app.engine.game_state import GameState
from app.events.python_eventing.errors import InvalidPythonError
from app.events.python_eventing.utils import EVENT_GEN_NAME
from app.utilities.typing import NID

@dataclass
class CompiledEvent():
    event: NID          # event nid
    source: str         # original source code of event
    compiled: str       # pythonic source code of event

    def get_runnable(self, game: GameState) -> Generator:
        exec_context = get_context(game=game)
        exec(self.compiled, exec_context)
        # possibility that there are some errors in python script
        try:
            gen = exec_context[EVENT_GEN_NAME]()
        except Exception as e:
            _, _, exc_tb = sys.exc_info()
            exception_lineno = traceback.extract_tb(exc_tb)[-1][1]
            diff_lines = self._num_diff_lines()
            source_as_lines = self.source.split('\n')
            true_lineno = exception_lineno - diff_lines
            failing_line = source_as_lines[true_lineno - 1]
            exc = InvalidPythonError(self.event, true_lineno, failing_line)
            exc.what = str(e)
            raise exc from e
        return gen

    def _num_diff_lines(self):
        generator_idx = self.compiled.index(EVENT_GEN_NAME)
        return self.compiled[:generator_idx].count('\n') + 1