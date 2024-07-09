from typing import List, Tuple
from utils.typing import NID

import os

from PyQt5.QtGui import QPixmap, QPainter

from app.constants import COLORKEY
from app.data.resources import combat_commands
from app.editor.combat_animation_editor.combat_animation_model import palette_swap

import logging

def export_to_legacy(current: WeaponAnimation, combat_anim: CombatAnimation, location: str):
    """
    Exports weapon animations to a Legacy formatted combat animation script file.
    The combat script used will not be correct for the actual Legacy engine and should
    be treated solely as a reference.

    Args:
        current (WeaponAnimation): Combat animation to export as a legacy LT file
    """

    palettes: List[Tuple[str, NID]] = combat_anim.palettes
    palette_nids = [palette[1] for palette in palettes]
    logging.info("Export from weapon animation %s-%s with palettes %s", combat_anim.nid, current.nid, palette_nids)

    # Generate script
    script_lines: List[str] = []
    for pose in current.poses:
        script_lines.append(f"pose;{pose.nid}")
        for combat_command in pose.timeline:
            command: str = combat_commands.generate_text(combat_command)
            script_lines.append(command)
        # Add newline
        script_lines.append("")

    script_loc = os.path.join(location, f"{combat_anim.nid}-{current.nid}-Script.txt")
    with open(script_loc, 'w') as fp:
        fp.writelines(script_lines)

    # Generate Index file
    index_lines: List[str] = []
    for frame in current.frames:
        x, y, width, height = frame.rect
        frame_line = f"{frame.nid};{x},{y};{width},{height};{frame.offset[0]},{frame.offset[1]}"
        index_lines.append(frame_line)

    index_loc = os.path.join(location, f"{combat_anim.nid}-{current.nid}-Index.txt")
    with open(index_loc, 'w') as fp:
        fp.writelines(index_lines)

    # Generate images
    # Find size of main pixmap
    max_width = max([frame.x + frame.width for frame in current.frames])
    max_height = max([frame.y + frame.height for frame in current.frames])

    for palette_name, palette_nid in palettes:
        image_loc = os.path.join(location, f"{combat_anim.nid}-{current.nid}-{palette_name}.png")
        main_pixmap = QPixmap(max_width, max_height)
        main_pixmap.fill(QColor(*COLORKEY))
        painter = QPainter()
        painter.begin(main_pixmap)
        for frame in current.frames:
            x, y, width, height = frame.rect
            frame_pixmap = palette_swap(frame.pixmap, palette_nid, with_colorkey=False)
            painter.drawPixmap(x, y, frame_pixmap)
        painter.end()
        # Save image
        main_pixmap.save(image_loc)

    logging.info("Completed export from weapon animation %s-%s with palettes %s", combat_anim.nid, current.nid, palette_nids)
        