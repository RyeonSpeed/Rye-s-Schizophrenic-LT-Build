from app.events.speak_style import SpeakStyle, SpeakStyleLibrary
from app.events.triggers import GenericTrigger
from typing import List
import unittest
from unittest.mock import MagicMock, patch, call

from app.tests.mocks.mock_game import get_mock_game
from app.events.event_commands import parse_text_to_command
from app.utilities.enums import Alignments

class EventUnitTests(unittest.TestCase):
    def setUp(self):
        from app.data.database.database import DB
        DB.load('testing_proj.ltproj')
        self.patchers = self.initialize_patchers()
        for patcher in self.patchers:
            patcher.start()
        self.game = get_mock_game()
        self.game.speak_styles = SpeakStyleLibrary()

    def initialize_patchers(self):
        patchers = [
            patch('app.engine.action.do'),
            patch('app.engine.dialog.Dialog'),
        ]
        return patchers

    def tearDown(self) -> None:
        for patcher in self.patchers:
            patcher.stop()

    def create_event(self, test_commands):
        from app.events.event import Event
        parsed_test_commands = [parse_text_to_command(command)[0] for command in test_commands]
        event = Event('test_nid', parsed_test_commands, GenericTrigger(), game=self.game)
        return event

    def run_all_commands(self, event):
        while event.state != 'complete':
            event.update()

    def MACRO_test_event_commands(self, test_commands):
        from app.events.function_catalog import get_catalog, reset_catalog
        command_names = set([command.split(';')[0] for command in test_commands])
        event = self.create_event(test_commands)
        mocked_commands: List[MagicMock] = []
        catalog = get_catalog()
        for name in command_names:
            mocked_command = MagicMock()
            catalog[name] = mocked_command
            mocked_commands.append(mocked_command)

        self.run_all_commands(event)
        for mocked_command in mocked_commands:
            mocked_command.assert_called_once()
        reset_catalog()

    def test_event_terminates_eventually(self):
        test_commands = [
            "speak;Eirika;SPEAK_TEXT",
            "speak;Eirika;SPEAK_TEXT",
            "speak;Eirika;SPEAK_TEXT",
        ]
        event = self.create_event(test_commands)
        self.run_all_commands(event)
        self.assertEqual(event.state, 'complete')

    def test_break(self):
        from app.events.function_catalog import get_catalog, reset_catalog
        test_commands = [
            "speak;Eirika;SPEAK_TEXT",
            "break",
            "speak;Eirika;SPEAK_TEXT"
        ]
        event = self.create_event(test_commands)
        catalog = get_catalog()
        catalog['speak'] = MagicMock()
        self.run_all_commands(event)

        catalog['speak'].assert_called_once()
        self.assertEqual(event.state, 'complete')
        reset_catalog()

    def test_speak_command(self):
        from app.events import event_functions
        # test that event correctly parses speak commands
        self.MACRO_test_event_commands(['speak;Eirika;SPEAK_TEXT'])

        # replaces the imported class so we can intercept calls
        dialog_patch = patch('app.engine.dialog.Dialog')
        mock_dialog = dialog_patch.start()

        # Test #1:
        #   - event replaces text correctly
        #   - event parses no_block correctly
        #   - Dialog object is correctly initialized
        #   - Dialog object is added to event text boxes
        #   - Dialog object does not increment priority with no portrait
        #   - Dialog object uses correct default arguments
        # initialize testing command(s)
        # we test event command parsing in another test, so just use a dummy event
        event = self.create_event([])
        event_functions.speak(event, None, '\u2028SPEAK_TEXT\u2028SPEAK_TEXT', flags={'no_block'})
        mock_dialog.assert_called_with('SPEAK_TEXT{sub_break}SPEAK_TEXT{no_wait}', None, 'message_bg_base',
                                       None, None, speaker=None, style_nid=None,
                                       autosize=False, speed=1, font_color=None,
                                       font_type='convo', num_lines=2, draw_cursor=True,
                                       message_tail='message_bg_tail', transparency=0.05, 
                                       name_tag_bg='name_tag', flags={'no_block'})
        self.assertEqual(len(event.text_boxes), 1)
        self.assertEqual(event.priority_counter, 1)

        # Test #2:
        #   - Test with portrait
        #   - Test correctly increments priority
        #   - Test dialog object correctly parses position, width, and text_speed
        mock_portrait = MagicMock()
        event = self.create_event([])
        event.portraits['Eirika'] = mock_portrait
        event_functions.speak(event, 'Eirika', 'SPEAK_TEXT', text_position='1,2', width='3', text_speed='5.0')
        mock_dialog.assert_called_with('SPEAK_TEXT', mock_portrait, 'message_bg_base',
                                       (1, 2), 3, speaker='Eirika', style_nid=None,
                                       autosize=False, speed=5.0, font_color=None,
                                       font_type='convo', num_lines=2, draw_cursor=True,
                                       message_tail='message_bg_tail', transparency=0.05, 
                                       name_tag_bg='name_tag', flags=set())
        self.assertEqual(mock_portrait.priority, 1)

        # Test #2a:
        #   - Test with portrait, low priority
        #   - Test with 'fit' flag
        #   - Test does not increment priority
        event_functions.speak(event, 'Eirika', 'SPEAK_TEXT', flags={'low_priority', 'fit'})
        mock_dialog.assert_called_with('SPEAK_TEXT', mock_portrait, 'message_bg_base',
                                       None, None, speaker='Eirika', style_nid=None,
                                       autosize=True, speed=1, font_color=None,
                                       font_type='convo', num_lines=2, draw_cursor=True,
                                       message_tail='message_bg_tail', transparency=0.05, 
                                       name_tag_bg='name_tag', flags={'low_priority', 'fit'})
        self.assertEqual(mock_portrait.priority, 1)

        # test #3: dialog with speak style
        from app.events.speak_style import SpeakStyle
        event = self.create_event([])
        self.game.speak_styles['test_style'] = SpeakStyle('test_style', 'Eirika', (1, 2), 3,
                                                          4.5, 'some_color', 'some_font', 'some_box_type',
                                                          6, True, 'message_bg_thought_tail', 0.2)
        event_functions.speak(event, None, 'SPEAK_TEXT', style_nid='test_style')
        mock_dialog.assert_called_with('SPEAK_TEXT', None, 'some_box_type', (1, 2), 3,
                                       speaker='Eirika', style_nid='test_style',
                                       autosize=False, speed=4.5, font_color='some_color',
                                       font_type='some_font', num_lines=6, draw_cursor=True,
                                       message_tail='message_bg_thought_tail', transparency=0.2,
                                       name_tag_bg='name_tag', flags=set())

        # test #4: special center text position
        event_functions.speak(event, None, 'SPEAK_TEXT', text_position='center')
        mock_dialog.assert_called_with('SPEAK_TEXT', None, 'message_bg_base',
                                       Alignments.CENTER, None, speaker=None, style_nid=None,
                                       autosize=False, speed=1, font_color=None,
                                       font_type='convo', num_lines=2, draw_cursor=True,
                                       message_tail='message_bg_tail', transparency=0.05,
                                       name_tag_bg='name_tag', flags=set())

        # disable intercepting calls at the end of the test
        dialog_patch.stop()


if __name__ == '__main__':
    unittest.main()
