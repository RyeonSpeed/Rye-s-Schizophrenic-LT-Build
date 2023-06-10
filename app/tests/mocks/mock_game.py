from unittest.mock import MagicMock, Mock

from app.engine.game_state import GameState
from app.engine.overworld.overworld_manager import OverworldManager, OverworldManagerInterface

def mock_overworld_manager() -> OverworldManager:
    om = MagicMock(spec=OverworldManagerInterface)
    return om

def get_mock_game() -> GameState:
    game = Mock(wraps=GameState)

    game.movement = MagicMock()
    game.speak_styles = {}
    game.overworld_controller = mock_overworld_manager()
    
    game.get_item = MagicMock()

    # Need to mock a function that returns it's own MagicMock with stack set to None
    get_skill = MagicMock()
    m = MagicMock()
    m.stack = None
    get_skill.return_value = m
    
    game.get_skill = get_skill
    game.get_unit = lambda x: None
    return game
