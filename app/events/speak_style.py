from __future__ import annotations

from typing import Set, Tuple, Dict
from app.utilities.enums import Alignments
from app.utilities.typing import NID

from app.constants import WINWIDTH

from app.utilities.data import Prefab

class SpeakStyle(Prefab):
    def __init__(self, nid: NID = None, speaker: NID = None, text_position: Alignments | Tuple[int, int] = None,
                 width: int = None, text_speed: float = None, font_color: str = None,
                 font_type: str = None, dialog_box: str = None, num_lines: int = None,
                 draw_cursor: bool = None, message_tail: str = None, name_tag_bg: str = None, flags: Set[str] = None):
        self.nid: NID = nid
        self.speaker: NID = speaker
        self.text_position: Alignments | Tuple[int, int] = text_position
        self.width: int = width
        self.text_speed: float = text_speed
        self.font_color: str = font_color
        self.font_type: str = font_type
        self.dialog_box: str = dialog_box
        self.num_lines: int = num_lines
        self.draw_cursor: bool = draw_cursor
        self.message_tail: str = message_tail
        self.name_tag_bg: str = name_tag_bg
        self.flags: Set[str] = flags

class SpeakStyleLibrary(Dict[NID, SpeakStyle]):
    def __init__(self, user_styles=None):
        # Built in speak styles for backwards compatibility
        self.update(
            {'__default': SpeakStyle(text_speed=1, font_type='convo', dialog_box='message_bg_base', num_lines=2, draw_cursor=True,
                                     message_tail='message_bg_tail', name_tag_bg='name_tag'),
             '__default_text': SpeakStyle(text_speed=0.5, font_type='text', dialog_box='menu_bg_base', num_lines=0, name_tag_bg='menu_bg_base'),
             'noir': SpeakStyle(dialog_box='menu_bg_dark', font_color='white', message_tail='None'),
             'hint': SpeakStyle(dialog_box='menu_bg_parchment', text_position=Alignments.CENTER, width=WINWIDTH//2 + 8, num_lines=4, message_tail='None'),
             'cinematic': SpeakStyle(dialog_box='None', text_position=Alignments.CENTER, font_color='grey', num_lines=5,
                                     font_type='chapter', draw_cursor=False, message_tail='None'),
             'narration': SpeakStyle(dialog_box='menu_bg_base', text_position=(4, 110), width=WINWIDTH - 8,
                                     font_color='white', message_tail='None'),
             'narration_top': SpeakStyle(dialog_box='menu_bg_base', text_position=(4, 2), width=WINWIDTH - 8,
                                         font_color='white', message_tail='None'),
             'clear': SpeakStyle(dialog_box='None', font_color='white', draw_cursor=False, message_tail='None'),
             'thought_bubble': SpeakStyle(message_tail='message_bg_thought_tail')
             }
        )

        if user_styles:
            self.update(user_styles)

    def save(self) -> dict:
        return {nid: style.save() for nid, style in self.items()}

    @classmethod
    def restore(cls, save_dict) -> SpeakStyleLibrary:
        self = cls()
        for nid, ser_dict in save_dict.items():
            style = SpeakStyle.restore(ser_dict)
            self[nid] = style
        return self
