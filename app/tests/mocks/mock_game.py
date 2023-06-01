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
    game.get_skill = MagicMock()
    game.get_unit = lambda x: None
    return game
